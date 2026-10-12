"""Read original human input. No source database is opened for writing.

Captured prompts are input, not automatically beliefs. Quoted/code/template
material is retained as context but is not accepted as Adam-authored text.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import urlopen


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def instant(value) -> str:
    dt = (datetime.fromtimestamp(value, timezone.utc) if isinstance(value, (float, int))
          else datetime.fromisoformat(str(value).replace("Z", "+00:00")))
    if dt.tzinfo is None:
        raise ValueError("A source timestamp has no timezone")
    return dt.astimezone(timezone.utc).isoformat()


GENERATED = (
    "# AGENTS.md instructions", "<environment_context>", "<system-reminder>",
    "<task-notification>", "<command-name>", "<local-command-stdout>",
    "This session is being continued from a previous conversation", "You are Codex",
    "You are an AI assistant", "This is an app-generated request", "<user_instructions>",
)
FIXTURE = re.compile(r"(?:SAVY SYNC PROBE|SAVY sync check — remove after verification|"
                     r"^SYNC TEST|^TEST FIXTURE|^SYNTHETIC TEST|^SMOKE TEST)", re.I)
APP_METADATA = re.compile(r"^\s*</?(?:external_codex_apps_[\w-]+|image|send_user_message_question_reply)\b", re.I)


def app_generated(text: str) -> bool:
    """Codex's Page/image/reply envelopes are transport, not typed prose."""
    return bool(APP_METADATA.match(text))


def attribution_excluded(text: str) -> bool:
    """Retain attributed/copied answers as context, not Adam-authored assertions.

    The exact cloud-agent source was identified in Adam's correction on Oct 11.
    Transport client_authored flags are deliberately not authorship evidence.
    """
    return (app_generated(text)
            or digest(text) == "05f18bb21c8c5167b52539a1b5f1bff12448db1198eaafc068fd62ea185bba93"
            or (text.lstrip().startswith("I asked Cowboy AI ")
                and "and verified its saved response. It replied:" in text))


def question_replies(text: str) -> list[dict] | None:
    opening, closing = '<send_user_message_question_reply>', '</send_user_message_question_reply>'
    wrapper = text.strip()
    if not wrapper.startswith(opening):
        return None
    if not wrapper.endswith(closing):
        raise ValueError("Structured human reply has no closing envelope")
    replies = json.loads(wrapper[len(opening):-len(closing)])
    if not isinstance(replies, list) or any(not isinstance(r, dict) or not isinstance(r.get('answer'), str)
                                           or not isinstance(r.get('questionItemId'), str) for r in replies):
        raise ValueError("Structured human reply does not identify its original answer")
    return replies


def browser_request_start(text: str) -> int | None:
    """Locate Codex's human request after its documented ambient browser wrapper.

    The caller has already verified a root human session and user role. Keep
    the entire envelope as source provenance; offsets address the original.
    """
    match = re.match(
        r"\A\s*<in-app-browser-context source=\"ambient-ui-state\">\n"
        r"This block is automatically supplied ambient UI state, not part of the user's request\."
        r"[\s\S]*?</in-app-browser-context>\n\n## My request:\n", text)
    return match.end() if match else None


def owned_belief_quotes(text: str) -> list[tuple[int, int]]:
    """An explicit first-person ownership statement identifies this quotation.

    This admits the named belief's exact content, not arbitrary pasted quotes,
    classifications, or inferred relationships. Outer quote marks are syntax;
    returned offsets address the unchanged source content inside them.
    """
    if FIXTURE.search(text) or attribution_excluded(text) or any(marker in text for marker in GENERATED):
        return []
    match = re.match(r'^\s*I have a belief called,\s*(?:"(?P<straight>[^"\n]+)"|“(?P<curly>[^”\n]+)”)', text)
    if not match:
        return []
    group = "straight" if match.group("straight") is not None else "curly"
    return [match.span(group)]


def own_spans(text: str) -> tuple[list[tuple[int, int]], list[str]]:
    """Only unquoted prose. Offsets always address the untouched original.

This is a collection policy, not a language/meaning definition. We cannot
identify the author of pasted prose without metadata; document wrappers are
therefore collection exceptions, never requests for Adam to approve his words.
"""
    if not text.strip():
        return [], ["empty"]
    if FIXTURE.search(text):
        return [], ["test-fixture"]
    if attribution_excluded(text) or any(marker in text for marker in GENERATED):
        return [], ["generated-wrapper"]
    if re.match(r"^\s*</?[A-Za-z][\w:-]*(?=[\s/>])", text):
        return [], ["pasted-document-authorship-unresolved"]
    if text.lstrip().startswith(("# ", "## ", "{\"", "<?xml", "<!DOCTYPE", "<INSTRUCTIONS>")):
        return [], ["pasted-document-authorship-unresolved"]
    excluded: list[tuple[int, int]] = []
    reasons = []
    # Attribution for quotations is retained in the full source, not inferred.
    for pattern, reason in [
        (r"(?ms)^\s*```.*?^\s*```[^\n]*(?:\n|$)", "code-block"),
        (r"(?m)^[ \t]*>[^\n]*(?:\n|$)", "quoted-material"),
        (r'“[^”]*”|"[^"\n]*"|`[^`\n]+`', "inline-quotation"),
    ]:
        hits = [(m.start(), m.end()) for m in re.finditer(pattern, text)]
        if hits:
            excluded.extend(hits)
            reasons.append(reason)
    merged: list[list[int]] = []
    for start, end in sorted(excluded):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])
    result = []
    start = 0
    for left, right in merged + [[len(text), len(text)]]:
        if text[start:left].strip():
            result.append((start, left))
        start = right
    return result, reasons


class Collector:
    def __init__(self, config: dict, cursors: dict):
        self.config = config
        self.cursors = json.loads(json.dumps(cursors))
        self.since = instant(config["since"])
        self.entries: list[dict] = []
        self.coverage: dict = {}
        self.exceptions: list[dict] = []

    def emit(self, adapter, ident, field, text, created, modified=None, *, role="input", context=None):
        if not isinstance(text, str):
            raise ValueError(f"{adapter}:{ident}:{field} is not text")
        created_raw, modified_raw = created, modified
        created = instant(created)
        modified = instant(modified or created)
        if modified < self.since:
            return
        if role == "input" and (text.rstrip().endswith("?") or re.match(r"\s*(?:why|how|what|can|could|would|is|are|does|do\s+(?:I|we|you|they))\b", text, re.I)):
            role = "question"
        body_start = browser_request_start(text) if adapter == "codex" else None
        body = text[body_start:] if body_start is not None else text
        body_spans, reasons = own_spans(body)
        offset = body_start or 0
        spans = [(offset + a, offset + b) for a, b in body_spans]
        identity = f"{adapter}:{ident}:{field}"
        if reasons:
            self.exceptions.append({"source_identity": identity, "reasons": reasons,
                                    "source_sha256": digest(text), "context": context,
                                    "source_text": text, "created_at": created})
        # Keep existing unquoted identities stable when admitting owned quotes.
        identified = [(f"span:{i}", a, b) for i, (a, b) in enumerate(spans)]
        identified += [(f"owned-belief:{offset+a}:{offset+b}", offset+a, offset+b) for a, b in owned_belief_quotes(body)]
        for span_identity, start, end in identified:
            quote = text[start:end]
            self.entries.append({"identity": identity + ":" + span_identity,
                                 "adapter": adapter, "source_id": str(ident), "field": field,
                                 "role": role, "text": quote, "text_sha256": digest(quote),
                                 "source_text": text, "source_sha256": digest(text),
                                 "char_start": start, "char_end": end,
                                 "created_at": created, "modified_at": modified,
                                 "source_created_raw": created_raw, "source_modified_raw": modified_raw,
                                 "context": context or {}})

    @staticmethod
    def db(path):
        p = Path(path)
        c = sqlite3.connect(p.as_uri() + "?mode=ro", uri=True, timeout=15)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA query_only=ON")
        return c

    def all_entries(self, path):
        with self.db(path) as c:
            rows = list(c.execute("SELECT rowid AS source_rowid,* FROM entries WHERE rowid > ? ORDER BY rowid",
                                  (self.cursors.get("all_entries", 0),)))
            for row in rows:
                r = dict(row)
                self.cursors["all_entries"] = r.pop("source_rowid")
                if r["entry_kind"] != "user_prompt" or r["source_app"] not in ("codex", "claude", "grok", "cursor", "gemini"):
                    continue
                if digest(r["raw_text"]) != r["content_sha256"]:
                    raise ValueError("All Entries source hash mismatch: " + r["entry_id"])
                record = Path(r["record_path"]).read_text(encoding="utf-8")
                marker = "<!-- exact-entry-start -->\n"
                if marker not in record or record.split(marker, 1)[1] != r["raw_text"]:
                    raise ValueError("All Entries Markdown/index disagree: " + r["entry_id"])
                self.emit("all_entries", r["entry_id"], "user_prompt", r["raw_text"], r["captured_at"],
                          context={k: v for k, v in r.items() if k != "raw_text"})
        return {"records_read": len(rows), "cursor": self.cursors.get("all_entries", 0)}

    def cowboy(self, path):
        count = 0
        with self.db(path) as c:
            # These are small tables. Re-reading catches form revisions, with text hashes doing deduplication.
            for row in c.execute("SELECT * FROM questions ORDER BY asked_at,id"):
                r = dict(row)
                if r["surface"] not in ("web", "cowboyai-iphone"):
                    continue
                count += 1
                theme = json.loads(r["theme_json"]) if r.get("theme_json") else None
                text = theme["question"] if theme else r["question"]
                self.emit("cowboyai", r["id"], "question", text, r["asked_at"], role="question",
                          context={"path": str(path), "surface": r["surface"], "theme_id": (theme or {}).get("id")})
                if theme:
                    for index, f in enumerate(theme.get("fields", [])):
                        # 'night' is AI output; 'prompt' is a template. Only the original answer is read.
                        self.emit("cowboyai", r["id"], f"fields:{index}:answer", f.get("answer", ""), r["asked_at"],
                                  role="reflection", context={"path": str(path), "prompt": f.get("prompt"), "theme_id": theme.get("id")})
            for row in c.execute("SELECT m.*,q.surface FROM more_information m JOIN questions q ON q.id=m.question_id"):
                r = dict(row)
                if r["surface"] in ("web", "cowboyai-iphone"):
                    self.emit("cowboyai", r["id"], "more_information", r["text"], r["created"],
                              role="reflection", context={"path": str(path), "question_id": r["question_id"]})
        return {"original_question_records_read": count, "excluded_surfaces": ["grade", "cli", "cli-twopass"]}

    def savy(self, path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("SAVY reminders are not a list")
        for r in data:
            if FIXTURE.search(r.get("title", "")):
                continue
            for field in ("title", "notes", "outcome", "whenIAm", "whenIAmText", "doneLooksLike", "want", "contextText"):
                text = r.get(field, "")
                if text in ("New Post", "New Reminder"):
                    continue
                if isinstance(text, str):
                    self.emit("savy", r["id"], field, text, r["createdAt"], r.get("updatedAt"),
                              role="reflection", context={"path": str(path), "kind": r.get("kind"), "theme_id": r.get("postThemeID")})
            for index, text in enumerate(r.get("postAnswers", [])):
                if r.get("postAnswersContainQuestions"):
                    # SAVY persists its prompt as line one. Preserve the answer substring exactly.
                    if "\n" not in text:
                        self.exceptions.append({"source_identity": f"savy:{r['id']}:postAnswers:{index}",
                                                "reasons": ["template-boundary-unresolved"], "source_text": text})
                        continue
                    prompt, answer = text.split("\n", 1)
                    if prompt.strip() not in self.config.get("savy_prompts", []):
                        suffixes = [q for q in self.config.get("savy_prompts", []) if prompt.endswith(q)]
                        if not suffixes:
                            self.exceptions.append({"source_identity": f"savy:{r['id']}:postAnswers:{index}",
                                                    "reasons": ["template-boundary-unresolved"], "source_text": text})
                            continue
                        original_prompt = max(suffixes, key=len)
                        prefix = prompt[:-len(original_prompt)]
                        self.emit("savy", r["id"], f"postAnswers:{index}:prompt_prefix", prefix, r["createdAt"], r.get("updatedAt"),
                                  role="reflection", context={"path": str(path), "prompt": original_prompt,
                                                               "complete_field": text, "theme_id": r.get("postThemeID")})
                        prompt = original_prompt
                else:
                    prompt, answer = None, text
                self.emit("savy", r["id"], f"postAnswers:{index}", answer, r["createdAt"], r.get("updatedAt"),
                          role="reflection", context={"path": str(path), "prompt": prompt, "complete_field": text,
                                                       "theme_id": r.get("postThemeID")})
        return {"reminders_read": len(data), "AI_fields_imported": 0}

    def savy_bootstrap(self, path):
        """A verified initial copy; future saves arrive through SAVY's native intake transport."""
        if self.cursors.get("savy_bootstrap_imported"):
            return {"snapshot_imported_previously": True, "future_updates": "native SAVY gateway intakes"}
        raw = Path(path).read_text(encoding="utf-8")
        if digest(raw) != self.config["savy_bootstrap_sha256"]:
            raise ValueError("SAVY bootstrap snapshot changed independently")
        result = self.savy(path)
        self.cursors["savy_bootstrap_imported"] = True
        return result | {"one_time_snapshot": True, "future_updates": "native SAVY gateway intakes"}

    def gateway(self, url):
        with urlopen(url, timeout=15) as response:
            data = json.load(response)
        intakes = data["intakes"]
        seen = set(self.cursors.get("gateway_requests", []))
        new_count = 0
        for item in sorted(intakes, key=lambda x: x["payload"]["created_at"]):
            p = item["payload"]
            if p.get("source_app_surface") != "savy_ios":
                continue
            if p["request_id"] in seen:
                continue
            seen.add(p["request_id"])
            new_count += 1
            context = {"reminder_id": p.get("reminder_id"), "capture_id": p.get("capture_id"),
                       "request_id": p["request_id"], "receipt": item.get("receipt"),
                       "source_app_surface": p["source_app_surface"], "complete_native_payload": p,
                       "timestamp_kind": "native save/capture event"}
            for field, text in p["exact_words"].items():
                self.emit("savy_intake", p["reminder_id"], field, text, p["created_at"], role="reflection", context=context)
            metadata = p.get("metadata", {})
            for field in ("notes", "waitingOn", "location", "url"):
                self.emit("savy_intake", p["reminder_id"], field, metadata.get(field, ""), p["created_at"],
                          role="reflection" if field == "notes" else "input", context=context)
            for index, step in enumerate(metadata.get("steps", [])):
                self.emit("savy_intake", p["reminder_id"], f"steps:{index}", step, p["created_at"], role="input", context=context)
            for index, field in enumerate(metadata.get("postAnswers", []) or []):
                if metadata.get("postAnswersContainQuestions"):
                    if "\n" not in field:
                        raise ValueError("SAVY intake has no template boundary: " + p["request_id"])
                    prompt, answer = field.split("\n", 1)
                    matches = [q for q in self.config.get("savy_prompts", []) if prompt.endswith(q)]
                    if prompt.strip() not in self.config.get("savy_prompts", []) and not matches:
                        self.exceptions.append({"source_identity": f"savy_intake:{p['request_id']}:postAnswers:{index}",
                                                "reasons": ["template-boundary-unresolved"], "source_text": field,
                                                "context": context})
                        continue
                    canonical = prompt.strip() if prompt.strip() in self.config.get("savy_prompts", []) else max(matches, key=len)
                    if prompt.endswith(canonical) and prompt != canonical:
                        self.emit("savy_intake", p["reminder_id"], f"postAnswers:{index}:prompt_prefix", prompt[:-len(canonical)],
                                  p["created_at"], role="reflection", context=context | {"complete_field": field})
                else:
                    prompt, answer = None, field
                self.emit("savy_intake", p["reminder_id"], f"postAnswers:{index}", answer, p["created_at"],
                          role="reflection", context=context | {"prompt": prompt, "complete_field": field})
        self.cursors["gateway_requests"] = sorted(seen)
        return {"intakes_read": len(intakes), "new_intakes_read": new_count, "transport_receipts_changed": False,
                "original_form_answers_and_notes_included": True}

    def transcript(self, path, kind):
        key = str(path)
        files = self.cursors.setdefault("files", {})
        old = files.get(key, {"offset": 0, "line": 0})
        if path.stat().st_size < old["offset"]:
            raise ValueError("Source transcript truncated: " + key)
        new = dict(old)
        count = 0
        with path.open("rb") as f:
            f.seek(old["offset"])
            while True:
                line = f.readline()
                if not line or not line.endswith(b"\n"):
                    break                 # an actively written final line is read next run
                item = json.loads(line)
                new["line"] += 1
                new["offset"] = f.tell()
                if kind == "codex":
                    p = item.get("payload", {})
                    if item.get("type") == "session_meta":
                        new["session_id"] = p["id"]
                        new["human_session"] = p.get("source") in ("vscode", "cli", "app_server", "appServer")
                    if item.get("type") == "turn_context":
                        new["turn_context_seen"] = True
                    if (item.get("type") != "response_item" or p.get("type") != "message"
                            or p.get("role") != "user" or not new.get("human_session")
                            or not new.get("turn_context_seen")):
                        continue
                    for index, block in enumerate(p.get("content", [])):
                        if block.get("type") != "input_text":
                            continue
                        replies = question_replies(block["text"])
                        if replies is not None:
                            for reply_index, reply in enumerate(replies):
                                self.emit(kind, f"{new['session_id']}:{new['line']}:{index}:reply:{reply_index}",
                                          "answer", reply["answer"], item["timestamp"], context={
                                              "path": key, "line": new["line"], "block": index,
                                              "session_id": new["session_id"], "message_id": p.get("id"),
                                              "question_item_id": reply["questionItemId"], "reply_index": reply_index,
                                              "complete_reply_envelope": block["text"],
                                              "reply_envelope_sha256": digest(block["text"]),
                                              "origin": "original human answer field; envelope and question are metadata"})
                            count += len(replies)
                            continue
                        self.emit(kind, f"{new['session_id']}:{new['line']}:{index}", "user_prompt", block["text"], item["timestamp"],
                                  context={"path": key, "line": new["line"], "block": index, "session_id": new["session_id"],
                                           "message_id": p.get("id"), "origin": "root human submission; exec/subagent sessions excluded"})
                        count += 1
                    continue
                else:
                    if item.get("type") != "user" or item.get("isMeta") or item.get("isCompactSummary") or item.get("isSidechain"):
                        continue
                    message = item.get("message", {})
                    if message.get("role") != "user":
                        continue
                    content = message.get("content", "")
                    text = content if isinstance(content, str) else "\n".join(b["text"] for b in content if b.get("type") == "text")
                ident = item.get("uuid") or f"{new.get('session_id', path.stem)}:{new['line']}"
                self.emit(kind, ident, "user_prompt", text, item["timestamp"],
                          context={"path": key, "line": new["line"], "session_id": new.get("session_id", item.get("sessionId")),
                                   "origin": "root human submission; assistant and tool turns excluded"})
                count += 1
        files[key] = new
        return count

    def codex(self, root):
        root = Path(root)
        if not root.is_dir():
            raise FileNotFoundError(root)
        if self.cursors.get("codex_reply_schema") != 1:
            # One source-schema backfill admits historical human reply fields,
            # preserving old identities and versions without a new approval.
            files = self.cursors.get("files", {})
            for path in list(files):
                if Path(path).is_relative_to(root):
                    files[path] = {"offset": 0, "line": 0}
            self.cursors["codex_reply_schema"] = 1
        if self.cursors.get("codex_browser_request_schema") != 1:
            # Re-read root user messages once, retaining existing identities and
            # admitting only the human body of the known browser envelope.
            for path in list(self.cursors.get("files", {})):
                if Path(path).is_relative_to(root):
                    self.cursors["files"][path] = {"offset": 0, "line": 0}
            self.cursors["codex_browser_request_schema"] = 1
        # Date directories discover new sessions; known files include still-active older sessions.
        since = datetime.fromisoformat(self.cursors.get("codex_scan_day", self.since)).date()
        today = datetime.now(timezone.utc).date()
        paths = {Path(p) for p in self.cursors.get("files", {}) if Path(p).is_relative_to(root)}
        day = since - timedelta(days=1)
        while day <= today:
            paths.update((root / day.strftime("%Y/%m/%d")).glob("*.jsonl"))
            day += timedelta(days=1)
        count = sum(self.transcript(p, "codex") for p in sorted(paths))
        self.cursors["codex_scan_day"] = today.isoformat() + "T00:00:00+00:00"
        return {"files_checked": len(paths), "human_messages_read": count}

    def claude(self, root):
        root = Path(root)
        if not root.is_dir():
            raise FileNotFoundError(root)
        cutoff = datetime.fromisoformat(self.since).timestamp()
        paths = [p for p in root.glob("*/*.jsonl") if not p.name.startswith("agent-") and p.stat().st_mtime >= cutoff]
        return {"files_checked": len(paths), "human_messages_read": sum(self.transcript(p, "claude") for p in paths)}

    def owned_belief_backfill(self):
        """Replay only previously excluded, explicitly self-owned quotations.

        Original snapshots and source identities survive; no source database or
        cursor is reset. Publication checkpoints this schema after validation.
        """
        if self.cursors.get("owned_belief_quote_schema") == 1:
            return {"sources_replayed": 0}
        root = self.config.get("archive_root")
        replayed = set()
        for path in sorted(Path(root).glob("*/sources.json")) if root else []:
            for e in json.loads(path.read_text())["exceptions"]:
                text = e.get("source_text", "")
                if not owned_belief_quotes(text):
                    continue
                if digest(text) != e["source_sha256"]:
                    raise ValueError("Owned belief backfill source hash mismatch: " + str(path))
                identity = e["source_identity"]
                if identity in replayed:
                    continue
                adapter, remainder = identity.split(":", 1)
                ident, field = remainder.rsplit(":", 1)
                if adapter not in ("codex", "claude", "all_entries") or field != "user_prompt":
                    continue
                self.emit(adapter, ident, field, text, e["created_at"], context=e.get("context"))
                replayed.add(identity)
        self.cursors["owned_belief_quote_schema"] = 1
        return {"sources_replayed": len(replayed)}

    def collect(self):
        for adapter, path in self.config["sources"].items():
            try:
                self.coverage[adapter] = {"status": "read", **getattr(self, adapter)(path)}
            except Exception as e:
                self.coverage[adapter] = {"status": "failed", "error": f"{type(e).__name__}: {e}"}
        try:
            self.coverage["owned_belief_backfill"] = {"status": "read", **self.owned_belief_backfill()}
        except Exception as e:
            self.coverage["owned_belief_backfill"] = {"status": "failed", "error": f"{type(e).__name__}: {e}"}
        return self.entries, self.cursors, self.coverage, self.exceptions
