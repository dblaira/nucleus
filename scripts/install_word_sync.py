#!/usr/bin/env python3
"""Install Adam's explicitly requested 900-second local sync; no agent per run."""
import hashlib
import json
import os
import plistlib
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADAM = Path("/Users/adamblair")
LABEL = "com.adamblair.cowboyai-word-sync"
SHARE = ADAM / ".local/share/cowboyai-word-sync"
STATE = ADAM / ".local/state/cowboyai-word-sync"
PYTHON = ADAM / "Documents/nucleus/.venv/bin/python"
DOCKER = ADAM / ".local/bin/docker"
IMAGE = "cowboyai-exact-words-validation:20261010"


def call(args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


def main():
    commit = call(["/usr/bin/git", "-C", str(ROOT), "rev-parse", "HEAD"])
    names = ("__init__.py", "graph.py", "word_sources.py", "word_sync.py", "word_sync_validator.py")
    for name in names:
        tracked = subprocess.run(["/usr/bin/git", "-C", str(ROOT), "show", f"{commit}:nucleus/{name}"],
                                 check=True, capture_output=True).stdout
        if tracked != (ROOT / "nucleus" / name).read_bytes():
            raise ValueError("Install only the committed sync code: " + name)
    image_id = call([str(DOCKER), "image", "inspect", IMAGE, "--format", "{{.Id}}"])
    release = SHARE / "releases" / commit
    (release / "nucleus").mkdir(parents=True, exist_ok=True)
    STATE.mkdir(parents=True, exist_ok=True)
    STATE.chmod(0o700)
    hashes = {}
    for name in names:
        src, dest = ROOT / "nucleus" / name, release / "nucleus" / name
        if dest.exists() and dest.read_bytes() != src.read_bytes():
            raise ValueError("Installed release was independently changed: " + str(dest))
        shutil.copy2(src, dest)
        hashes[name] = hashlib.sha256(dest.read_bytes()).hexdigest()
    manifest = {"commit": commit, "modules": hashes, "validator_image_id": image_id}
    (release / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    ontology = ADAM / "Documents/Main/Ontology"
    config = {"since": "2026-10-10T00:00:00-07:00", "state_dir": str(STATE),
              "graph": str(ontology / "accepted/accepted-graph.ttl"),
              "ledger": str(ontology / "accepted/decision-ledger.json"),
              "shape": str(ontology / "shapes/connection-shape.ttl"),
              "archive_root": str(ontology / "sources/automatic-exact-words"),
              "vault_lock": str(ADAM / ".local/state/obsidian-backup/runner.lock"),
              "docker": str(DOCKER), "validator_image": image_id,
              "backup_command": ["/usr/bin/python3", str(ADAM / ".local/share/obsidian-backup/backup.py")],
              "backup_status": str(ADAM / ".local/state/obsidian-backup/status.json"),
              "sources": {"all_entries": str(ADAM / "Library/Application Support/All Entries/index.sqlite3"),
                          "cowboy": str(ADAM / "Library/Application Support/nucleus/nucleus.sqlite3"),
                          "savy": str(ADAM / "Library/Containers/com.adamblair.savy/Data/Library/Application Support/reminders.json"),
                          "gateway": "http://127.0.0.1:8765/v1/hub/candidates",
                          "codex": str(ADAM / ".codex/sessions"), "claude": str(ADAM / ".claude/projects")}}
    prompt_file = ADAM / "Developer/GitHub/SAVY-iOS/SAVY/PostTheme.swift"
    prompts = re.findall(r'PostThemeQuestion\(prompt: ("(?:[^"\\]|\\.)*")', prompt_file.read_text())
    config["savy_prompts"] = [json.loads(p) for p in prompts]
    config_path = SHARE / "config.json"
    if config_path.exists():
        existing = json.loads(config_path.read_text())
        # Preserve user changes, but refuse a mismatched safety boundary.
        for key in ("graph", "ledger", "vault_lock", "state_dir"):
            if existing[key] != config[key]:
                raise ValueError("Existing sync configuration conflicts: " + key)
        config = existing | {"validator_image": image_id}
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n")
    config_path.chmod(0o600)
    manifest["config_sha256"] = hashlib.sha256(config_path.read_bytes()).hexdigest()
    (SHARE / "installed.json").write_text(json.dumps(manifest, indent=2) + "\n")
    logs = ADAM / "Library/Logs"
    agent = {"Label": LABEL,
             "ProgramArguments": [str(PYTHON), "-m", "nucleus.word_sync", "--config", str(config_path)],
             "WorkingDirectory": str(release), "StartInterval": 900, "RunAtLoad": True,
             "ProcessType": "Background", "StandardOutPath": str(logs / "cowboyai-word-sync.log"),
             "StandardErrorPath": str(logs / "cowboyai-word-sync-error.log"),
             "EnvironmentVariables": {"PATH": "/Users/adamblair/.local/bin:/usr/bin:/bin"}}
    plist = ADAM / "Library/LaunchAgents" / (LABEL + ".plist")
    if plist.exists() and plistlib.loads(plist.read_bytes()) != agent:
        raise ValueError("Existing launch agent differs; preserve it before updating")
    plist.write_bytes(plistlib.dumps(agent))
    domain = "gui/" + str(os.getuid())
    found = subprocess.run(["/bin/launchctl", "print", domain + "/" + LABEL], capture_output=True).returncode == 0
    if not found:
        call(["/bin/launchctl", "bootstrap", domain, str(plist)])
    else:
        call(["/bin/launchctl", "kickstart", domain + "/" + LABEL])
    print(json.dumps({"label": LABEL, "interval_seconds": 900, "commit": commit,
                      "release": str(release), "config": str(config_path), "validator_image": image_id}))


if __name__ == "__main__":
    main()
