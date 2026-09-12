"""One model call. Anthropic when a key is on this Mac, then OpenAI, otherwise the Codex lane.
The Z.ai door (Adam's prepaid GLM credits) opens with NUCLEUS_DOOR=zai.

Both doors take the same prompt and return the raw reply text. The gate judges it.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import threading
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from . import STORE_PATH
from .prompt import SCHEMA_PATH

ANTHROPIC_MODEL = "claude-fable-5-1"
CODEX_MODEL = "gpt-5.6-sol"
TIMEOUT_SECONDS = 90.0


@dataclass
class ModelReply:
    provider: str
    model: str
    text: str


def anthropic_key() -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    try:
        completed = subprocess.run(
            ["security", "find-generic-password", "-s", "nucleus", "-a", "anthropic", "-w"],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    key = completed.stdout.strip()
    return key or None


def call_anthropic(prompt: str, key: str, timeout: float = TIMEOUT_SECONDS) -> ModelReply:
    """The nucleus block is identical every call, so it is marked for caching."""
    marker = "\n===== the dictionary's reading of the question ====="
    head, sep, tail = prompt.partition(marker)
    system = [{"type": "text", "text": head, "cache_control": {"type": "ephemeral"}}] if sep else []
    user = (sep + tail) if sep else prompt
    body = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 12000,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode("utf-8"),
        headers={"content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    text = "".join(block.get("text", "") for block in payload.get("content", []) if block.get("type") == "text")
    return ModelReply(provider="anthropic", model=ANTHROPIC_MODEL, text=text)


NUCLEUS_MARKER = "\n===== the dictionary's reading of the question ====="
CONVERSATION_PATH = STORE_PATH.parent / "conversation.json"
ROOM = STORE_PATH.parent / "codex-room"   # an empty folder the conversation lives in
ONCE = """

===== hold these =====
Everything above is Adam Blair's nucleus: his records, his ontology, his dictionary, his routes. Hold all of it.
Each message after this one is one question with its own contract. Every reply is exactly one JSON object
and nothing else: no prose, no fences. For this message reply with the single word: ready
"""
_conversation_lock = threading.Lock()
_SESSION_ID = re.compile(r"session id: ([0-9a-f-]{36})")
_CODEX_BASE = ["codex", "exec", "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check",
               "-m", CODEX_MODEL, "-c", "model_reasoning_effort=\"low\""]


def nucleus_hash(head: str) -> str:
    return hashlib.sha256(head.encode("utf-8")).hexdigest()


def split_prompt(prompt: str) -> tuple[str, str]:
    """The part that is the same every question (his files) and the part that is this question."""
    head, sep, tail = prompt.partition(NUCLEUS_MARKER)
    return (head, sep + tail) if sep else ("", prompt)


def _read_conversation() -> dict:
    try:
        return json.loads(CONVERSATION_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _open_conversation(head: str, timeout: float) -> str:
    """Send the nucleus once. The Codex lane keeps the conversation; its id is saved next to the store."""
    ROOM.mkdir(parents=True, exist_ok=True)
    command = _CODEX_BASE + ["-s", "read-only", "-C", str(ROOM), "--color", "never", "-"]
    completed = subprocess.run(command, input=head + ONCE, capture_output=True, text=True, timeout=timeout, check=False)
    found = _SESSION_ID.search(completed.stderr)
    if not found:
        raise RuntimeError(f"Could not open the conversation. exit {completed.returncode}. stderr: {completed.stderr.strip()[-600:]}")
    session_id = found.group(1)
    CONVERSATION_PATH.write_text(json.dumps({"session_id": session_id, "nucleus_hash": nucleus_hash(head)}), encoding="utf-8")
    return session_id


def _extract_json(text: str) -> str:
    start, end = text.find("{"), text.rfind("}")
    return text[start:end + 1] if start != -1 and end > start else text.strip()


def call_codex_conversation(head: str, turn: str, timeout: float = TIMEOUT_SECONDS) -> ModelReply:
    """One short turn in the open conversation that already holds the nucleus.

    Measured 2026-09-11: 16.6 s against 26 to 45 s for a fresh conversation each question.
    The conversation is reopened when his files change (the hash) or when the lane has lost it.
    """
    with _conversation_lock:
        saved = _read_conversation()
        session_id = saved.get("session_id") if saved.get("nucleus_hash") == nucleus_hash(head) else None
        if not session_id:
            session_id = _open_conversation(head, timeout)
        command = _CODEX_BASE + ["resume", session_id, "-"]
        completed = subprocess.run(command, input=turn, capture_output=True, text=True, timeout=timeout, check=False)
        text = _extract_json(completed.stdout)
        if completed.returncode != 0 or not text.startswith("{"):
            session_id = _open_conversation(head, timeout)
            completed = subprocess.run(_CODEX_BASE + ["resume", session_id, "-"], input=turn, capture_output=True, text=True, timeout=timeout, check=False)
            text = _extract_json(completed.stdout)
        if not text.startswith("{"):
            raise RuntimeError(f"The conversation returned nothing usable. exit {completed.returncode}. stderr: {completed.stderr.strip()[-600:]}")
        return ModelReply(provider="codex", model=CODEX_MODEL, text=text)


def call_codex(prompt: str, timeout: float = TIMEOUT_SECONDS, schema: Path = SCHEMA_PATH) -> ModelReply:
    """The Codex lane. With the nucleus in the prompt: one open conversation, short turns. Otherwise one fresh call."""
    head, turn = split_prompt(prompt)
    if head:
        return call_codex_conversation(head, turn, timeout=timeout)
    return call_codex_fresh(prompt, timeout=timeout, schema=schema)


def call_codex_fresh(prompt: str, timeout: float = TIMEOUT_SECONDS, schema: Path = SCHEMA_PATH) -> ModelReply:
    """A fresh Codex conversation for one prompt, read-only, in an empty folder, answer shaped by the schema."""
    with tempfile.TemporaryDirectory(prefix="nucleus-codex-") as folder:
        out = Path(folder) / "reply.json"
        # --ignore-user-config and --ignore-rules: without them the Codex CLI loads Adam's
        # ~/.codex/config.toml (reasoning effort "ultra"), his 9.9 KB AGENTS.md and his hooks,
        # runs shell commands to read his skills, and rewrites the answer into chapters.
        # Measured 2026-09-10 on a one-line prompt: 58 s with them loaded, 9 s without.
        command = [
            "codex", "exec", "-m", CODEX_MODEL, "-s", "read-only", "--ephemeral", "--skip-git-repo-check",
            "--ignore-user-config", "--ignore-rules", "-c", "model_reasoning_effort=\"low\"",
            "-C", folder, "--color", "never", "--output-schema", str(schema), "-o", str(out), "-",
        ]
        completed = subprocess.run(command, input=prompt, capture_output=True, text=True, timeout=timeout, check=False)
        if out.exists():
            text = out.read_text(encoding="utf-8").strip()
        else:
            text = completed.stdout.strip()
        if not text:
            raise RuntimeError(f"Codex returned nothing. exit {completed.returncode}. stderr: {completed.stderr.strip()[-600:]}")
        return ModelReply(provider="codex", model=CODEX_MODEL, text=text)


OPENAI_MODEL = os.environ.get("NUCLEUS_OPENAI_MODEL", "gpt-5.6-sol")


def openai_key() -> str | None:
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    try:
        completed = subprocess.run(
            ["security", "find-generic-password", "-s", "nucleus", "-a", "openai", "-w"],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    key = completed.stdout.strip()
    return key or None


def call_openai(prompt: str, key: str, timeout: float = TIMEOUT_SECONDS) -> ModelReply:
    """The OpenAI API door. Same prompt, plain call, JSON reply. Untested until a key is on this Mac."""
    body = {
        "model": OPENAI_MODEL,
        "input": [{"role": "user", "content": prompt}],
        "text": {"format": {"type": "json_object"}},
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={"content-type": "application/json", "authorization": f"Bearer {key}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    text = payload.get("output_text") or ""
    if not text:
        for item in payload.get("output", []):
            for part in item.get("content", []) if isinstance(item, dict) else []:
                if part.get("type") in ("output_text", "text"):
                    text += part.get("text", "")
    return ModelReply(provider="openai", model=OPENAI_MODEL, text=text)


ZAI_MODEL = os.environ.get("NUCLEUS_ZAI_MODEL", "glm-5.3-flash")  # glm-5.3 thinks past 12,000 tokens and never answers (measured 2026-09-11)


def zai_key() -> str | None:
    """Adam's Z.ai key. He puts it in the Mac keychain himself; the code never sees it in a file."""
    key = os.environ.get("ZAI_API_KEY")
    if key:
        return key
    try:
        completed = subprocess.run(
            ["security", "find-generic-password", "-s", "nucleus", "-a", "zai", "-w"],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    key = completed.stdout.strip()
    return key or None


def call_zai(prompt: str, key: str, timeout: float = TIMEOUT_SECONDS) -> ModelReply:
    """The Z.ai door (GLM). OpenAI-shaped chat call, thinking low (this model cannot turn it off), JSON reply. Adam's prepaid credits."""
    body = {
        "model": ZAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "thinking": {"type": "enabled", "effort": "low"},
        "response_format": {"type": "json_object"},
        "max_tokens": 12000,
    }
    request = urllib.request.Request(
        "https://api.z.ai/api/paas/v4/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"content-type": "application/json", "authorization": f"Bearer {key}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    text = ""
    for choice in payload.get("choices", []):
        message = choice.get("message") or {}
        text += message.get("content") or ""
    if not text:
        raise RuntimeError(f"Z.ai returned no text: {json.dumps(payload)[:600]}")
    return ModelReply(provider="zai", model=payload.get("model") or ZAI_MODEL, text=text.strip())


def door() -> str:
    """Which door a call goes through. NUCLEUS_DOOR=zai|anthropic|openai|codex overrides the order.

    Measured 2026-09-11 on "What is FLOW?": codex 28 s; zai glm-5.3-flash 64 s (compact nucleus) and
    83 s (full files); zai glm-5.3 never finished thinking. So the Z.ai door waits until Adam asks for it.
    """
    chosen = os.environ.get("NUCLEUS_DOOR")
    if chosen:
        return chosen
    if anthropic_key():
        return "anthropic"
    if openai_key():
        return "openai"
    return "codex"


def call(prompt: str, timeout: float = TIMEOUT_SECONDS, schema: Path = SCHEMA_PATH) -> ModelReply:
    """schema shapes the reply on the Codex lane; the other doors take the shape from the prompt."""
    which = door()
    if which == "zai":
        key = zai_key()
        if not key:
            raise RuntimeError("NUCLEUS_DOOR is zai but no Z.ai key is in the keychain (service nucleus, account zai).")
        return call_zai(prompt, key, timeout=timeout)
    if which == "anthropic":
        return call_anthropic(prompt, anthropic_key(), timeout=timeout)
    if which == "openai":
        return call_openai(prompt, openai_key(), timeout=timeout)
    return call_codex(prompt, timeout=timeout, schema=schema)
