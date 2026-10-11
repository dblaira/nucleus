"""Publish source-exact RDF entries under Adam's standing approval. No LLM calls."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .graph import CONNECTION_PREFIX, load_graph, unescape
from .word_sources import Collector, digest

AUTHORITY = "My words do not need approval.  They are my words which means they went though an approval process before they were spoken.  Approve all candidates that use only my words."
U = "https://understood.app/ontology#"


def now():
    return datetime.now(timezone.utc).isoformat()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dumps(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name("." + path.name + "." + uuid.uuid4().hex)
    try:
        with temp.open("xb") as f:
            os.chmod(temp, 0o600)
            f.write(data.encode("utf-8") if isinstance(data, str) else data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        temp.unlink(missing_ok=True)


@contextmanager
def lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def literal(value):
    return json.dumps(value, ensure_ascii=False)


def entry_block(entry, at):
    uri = CONNECTION_PREFIX + entry["record_id"]
    source_uri = "urn:cowboyai:source:" + digest(entry["identity"])
    props = [
        ("understood:label", literal(entry["label"])),
        ("understood:connectionType", '"stated_source_entry"'),
        ("understood:exactWords", literal(entry["text"])),
        ("understood:sourceRole", literal(entry["role"])),
        ("understood:sourceIdentity", literal(entry["identity"])),
        ("understood:sourceRevision", literal(str(entry["revision"]))),
        ("understood:textSha256", literal(entry["text_sha256"])),
        ("understood:acceptedAt", literal(at) + "^^xsd:dateTime"),
        ("<http://purl.org/dc/terms/created>", literal(entry["created_at"]) + "^^xsd:dateTime"),
        ("<http://purl.org/dc/terms/modified>", literal(entry["modified_at"]) + "^^xsd:dateTime"),
        ("<http://www.w3.org/ns/prov#wasDerivedFrom>", "<" + source_uri + ">"),
        ("understood:sourceSnapshot", literal(entry["source_snapshot"])),
    ]
    if entry.get("previous_record"):
        props.append(("<http://www.w3.org/ns/prov#wasRevisionOf>", "<" + CONNECTION_PREFIX + entry["previous_record"] + ">"))
    return "\n<" + uri + "> a understood:SourceEntry ;\n" + "".join("  " + p + " " + v + " ;\n" for p, v in props) + "  .\n"


def prepare(config, state, entries, cursors, coverage, exceptions, batch):
    graph_path, ledger_path = Path(config["graph"]), Path(config["ledger"])
    old_graph = graph_path.read_text(encoding="utf-8")
    old_ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    if not isinstance(old_ledger, list):
        raise ValueError("Decision ledger is not a list")
    graph = load_graph(graph_path, ledger_path)
    updated = json.loads(json.dumps(state))
    seen = updated.setdefault("seen", {})
    selected = []
    repeats, revisions = 0, 0
    at = now()
    batch_id = batch.name
    archive = Path(config["archive_root"]) / batch_id
    new_ledger = list(old_ledger)
    new_graph = old_graph
    for original in entries:
        e = dict(original)
        if e["source_text"][e["char_start"]:e["char_end"]] != e["text"] or digest(e["text"]) != e["text_sha256"]:
            raise ValueError("Exact-source check failed: " + e["identity"])
        prior = seen.get(e["identity"])
        if prior and prior["text_sha256"] == e["text_sha256"]:
            record = graph.find(prior["record_id"])
            # A repeated identity inside this collection may refer to a just-staged record.
            if record is None and not any(x["record_id"] == prior["record_id"] for x in selected):
                raise ValueError("Previously published source entry is missing: " + prior["record_id"])
            if record and (not graph.is_accepted(record) or unescape(record.exact_words) != e["text"]):
                raise ValueError("Published source entry changed independently: " + prior["record_id"])
            repeats += 1
            continue
        revision = prior["revision"] + 1 if prior else 1
        e["revision"] = revision
        e["record_id"] = "source-" + digest(e["identity"] + ":" + str(revision) + ":" + e["text_sha256"])[:32]
        e["previous_record"] = prior["record_id"] if prior else None
        if graph.find(e["record_id"]):
            raise ValueError("Uncheckpointed source ID already exists; recover the pending journal first")
        e["label"] = "“" + e["text"] + "” — his words · " + e["record_id"]
        e["source_snapshot"] = str(archive / "sources.json")
        new_graph += entry_block(e, at)
        new_ledger.append({"ledger_id": "SYNC-" + e["record_id"], "claim_id": e["record_id"],
                           "claim": e["label"], "decision": "accepted", "at": at,
                           "actor": "Adam Blair", "approval_basis": "standing-exact-words-2026-10-10",
                           "authority": AUTHORITY, "source_identity": e["identity"],
                           "source_created_at": e["created_at"], "source_modified_at": e["modified_at"],
                           "source_snapshot": e["source_snapshot"], "text_sha256": e["text_sha256"]})
        seen[e["identity"]] = {"text_sha256": e["text_sha256"], "revision": revision, "record_id": e["record_id"]}
        revisions += int(prior is not None)
        selected.append(e)
    updated["cursors"] = cursors
    updated["last_success"] = at
    updated["backup_pending"] = bool(selected) or state.get("backup_pending", False)
    summary = {"batch_id": batch_id, "at": at, "new_entries": len(selected) - revisions,
               "revisions": revisions, "duplicates_skipped": repeats, "coverage": coverage,
               "collection_exceptions": len([e for e in exceptions if e["reasons"] != ["empty"]]),
               "entries": selected, "exceptions": exceptions, "authority": AUTHORITY,
               "LLM_calls": 0, "full_sources_kept": True}
    batch.mkdir(parents=True, exist_ok=False)
    os.chmod(batch, 0o700)
    if selected:
        atomic(batch / "before-graph.ttl", old_graph)
        atomic(batch / "before-ledger.json", ledger_path.read_bytes())
        atomic(batch / "graph.ttl", new_graph)
        atomic(batch / "ledger.json", dumps(new_ledger))
        atomic(batch / "shape.ttl", Path(config["shape"]).read_bytes())
    atomic(batch / "state.json", dumps(updated))
    atomic(batch / "sources.json", dumps(summary))
    return summary, updated


def docker_validate(config, batch):
    validator = Path(__file__).with_name("word_sync_validator.py").resolve()
    if config.get("start_docker_when_needed", True):
        probe = subprocess.run([config["docker"], "info", "--format", "{{.ServerVersion}}"],
                               capture_output=True, text=True, timeout=10)
        if probe.returncode:
            subprocess.run(["/usr/bin/open", "-gj", "/Applications/Docker.app"], check=True,
                           capture_output=True, timeout=10)
            deadline = time.monotonic() + 45
            while probe.returncode and time.monotonic() < deadline:
                time.sleep(1)
                probe = subprocess.run([config["docker"], "info", "--format", "{{.ServerVersion}}"],
                                       capture_output=True, text=True, timeout=5)
            if probe.returncode:
                raise ValueError("Docker could not start; this validated batch will retry on the next run")
    # Docker's non-root validator UID differs from the host UID. Only this
    # mounted directory is readable; its state_dir parent remains owner-only.
    batch.chmod(0o755)
    for path in batch.iterdir():
        path.chmod(0o644)
    command = [config["docker"], "run", "--rm", "--network", "none", "--read-only",
               "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--memory", "512m",
               "--cpus", "1",
               "-v", str(batch.resolve()) + ":/batch:ro", "-v", str(validator) + ":/validator.py:ro",
               config["validator_image"], "/validator.py"]
    p = subprocess.run(command, capture_output=True, text=True, timeout=90)
    if p.returncode:
        raise ValueError("Docker validation failed: " + (p.stderr or p.stdout)[-2500:])
    result = json.loads(p.stdout)
    if result.get("status") != "passed":
        raise ValueError("Docker did not confirm validation")
    atomic(batch / "validation.json", dumps(result))
    return result


def verify(config, batch):
    source = json.loads((batch / "sources.json").read_text(encoding="utf-8"))
    graph = load_graph(Path(config["graph"]), Path(config["ledger"]))
    for e in source["entries"]:
        record = graph.find(e["record_id"])
        if not record or not graph.is_accepted(record) or unescape(record.exact_words) != e["text"]:
            raise ValueError("Live reader exact-word verification failed: " + e["record_id"])
        if record.source_created_at != e["created_at"]:
            raise ValueError("Original source date changed: " + e["record_id"])
    return {"accepted_exact_entries_read_back": len(source["entries"]), "graph_sha256": file_hash(config["graph"]),
            "ledger_sha256": file_hash(config["ledger"])}


def recover(config, state_dir):
    pending_path = state_dir / "pending.json"
    if not pending_path.exists():
        return None
    pending = json.loads(pending_path.read_text(encoding="utf-8"))
    batch = Path(pending["batch"])
    for entry in pending["files"]:
        dest = Path(entry["destination"])
        current = file_hash(dest) if dest.exists() else None
        if current not in (entry["old_sha256"], entry["new_sha256"]):
            raise ValueError("Pending publication conflicts with an independent edit: " + str(dest))
        if file_hash(entry["staged"]) != entry["new_sha256"]:
            raise ValueError("Pending staged file failed integrity check")
    for entry in pending["files"]:
        atomic(entry["destination"], Path(entry["staged"]).read_bytes())
    proof = verify(config, batch)
    atomic(batch / "readback.json", dumps(proof))
    atomic(state_dir / "state.json", (batch / "state.json").read_bytes())
    atomic(batch / "completed.json", dumps({"at": now(), **proof}))
    pending_path.unlink()
    return pending["summary"] | {"recovered": True, "readback": proof}


def publish(config, state_dir, batch, summary, after_write=None):
    archive = Path(config["archive_root"]) / batch.name
    archive.mkdir(parents=True, exist_ok=False)
    # Provenance is visible before either accepted file. It is never replaced.
    for name in ("sources.json", "validation.json"):
        atomic(archive / name, (batch / name).read_bytes())
    pairs = [("ledger.json", config["ledger"], "before-ledger.json"),
             ("graph.ttl", config["graph"], "before-graph.ttl")]
    files = [{"staged": str(batch / staged), "destination": str(dest),
              "old_sha256": file_hash(batch / old), "new_sha256": file_hash(batch / staged)}
             for staged, dest, old in pairs]
    for item in files:
        if file_hash(item["destination"]) != item["old_sha256"]:
            raise ValueError("Live files changed after staging; preserved the staged and live versions")
    journal = {"batch": str(batch), "files": files,
               "summary": {k: v for k, v in summary.items() if k not in ("entries", "exceptions", "authority")}}
    atomic(state_dir / "pending.json", dumps(journal))
    for index, item in enumerate(files):
        atomic(item["destination"], Path(item["staged"]).read_bytes())
        if after_write:
            after_write(index)             # tests exercise real interruption between these writes
    return recover(config, state_dir)


def backup(config, state_dir):
    command = config.get("backup_command")
    if not command:
        return {"status": "not-configured"}
    p = subprocess.run(command, capture_output=True, text=True, timeout=120)
    saved = json.loads(Path(config["backup_status"]).read_text(encoding="utf-8"))
    verified = saved.get("status") == "success" and saved.get("working_tree_clean") and saved.get("remote_verified") == saved.get("local_after")
    result = {"status": "verified" if p.returncode == 0 and verified else "failed",
              "at": saved.get("finished_at"), "commit": saved.get("remote_verified"),
              "reason": saved.get("reason")}
    state = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
    state["backup_pending"] = result["status"] != "verified"
    atomic(state_dir / "state.json", dumps(state))
    return result


def run(config, dry_run=False, validator=docker_validate):
    state_dir = Path(config["state_dir"])
    state_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(state_dir, 0o700)
    result = {"started_at": now(), "status": "running", "LLM_calls": 0}
    code = 0
    try:
        with lock(state_dir / "run.lock"):
            with lock(config["vault_lock"]):
                recovered = recover(config, state_dir) if not dry_run else None
                state_path = state_dir / "state.json"
                state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
                entries, cursors, coverage, exceptions = Collector(config, state.get("cursors", {})).collect()
                result["coverage"] = coverage
                if any(c["status"] != "read" for c in coverage.values()):
                    raise ValueError("Source collection failed; source cursors have not advanced")
                batch = state_dir / "batches" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8])
                summary, updated = prepare(config, state, entries, cursors, coverage, exceptions, batch)
                result.update({k: v for k, v in summary.items() if k not in ("entries", "exceptions", "authority")})
                changed = bool(summary["entries"])
                if changed:
                    result["validation"] = validator(config, batch)
                    if not dry_run:
                        proof = publish(config, state_dir, batch, summary)
                        result["readback"] = proof["readback"]
                elif not dry_run:
                    atomic(state_path, dumps(updated))
                result["recovered_batch"] = recovered
                result["batch_path"] = str(batch)
                result["status"] = "dry-run" if dry_run else "success"
                result["last_success"] = state.get("last_success") if dry_run else updated["last_success"]
                result["graph_changed"] = changed and not dry_run
            # The existing backup owner acquires its own vault lock. Never run it while holding that lock.
            if not dry_run and updated.get("backup_pending"):
                result["backup"] = backup(config, state_dir)
                if result["backup"]["status"] == "failed":
                    result["status"] = "backup-failed"
                    code = 1
            elif Path(config.get("backup_status", "")).is_file():
                prior_backup = json.loads(Path(config["backup_status"]).read_text(encoding="utf-8"))
                result["backup"] = {"status": prior_backup.get("status"), "at": prior_backup.get("finished_at"),
                                    "commit": prior_backup.get("remote_verified")}
    except Exception as e:
        result["status"] = "retry" if isinstance(e, BlockingIOError) else "failed"
        result["error"] = f"{type(e).__name__}: {e}"
        code = 1
        state_path = state_dir / "state.json"
        result["last_success"] = json.loads(state_path.read_text()).get("last_success") if state_path.exists() else None
    result["finished_at"] = now()
    atomic(state_dir / "runs" / (uuid.uuid4().hex + ".json"), dumps(result))
    if not dry_run:
        atomic(state_dir / "status.json", dumps(result))
    return code, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if args.status:
        print((Path(config["state_dir"]) / "status.json").read_text(encoding="utf-8"))
        return 0
    code, result = run(config, args.dry_run)
    print(dumps(result))
    return code


if __name__ == "__main__":
    sys.exit(main())
