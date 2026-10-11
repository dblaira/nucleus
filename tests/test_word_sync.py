import json
from pathlib import Path

import pytest

from nucleus.graph import load_graph, unescape
from nucleus.narrative import Narrator, Told, records_told
from nucleus.word_sources import Collector, digest, own_spans
from nucleus import word_sync as sync

AT = "2026-10-11T12:00:00+00:00"
TTL = '@prefix understood: <https://understood.app/ontology#> .\n@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n'


@pytest.fixture
def config(tmp_path):
    (tmp_path / "graph.ttl").write_text(TTL)
    (tmp_path / "ledger.json").write_text("[]\n")
    (tmp_path / "shape.ttl").write_text(TTL)
    (tmp_path / "savy.json").write_text("[]")
    return {"since": "2026-10-10T00:00:00+00:00", "state_dir": str(tmp_path / "state"),
            "graph": str(tmp_path / "graph.ttl"), "ledger": str(tmp_path / "ledger.json"),
            "shape": str(tmp_path / "shape.ttl"), "archive_root": str(tmp_path / "archive"),
            "vault_lock": str(tmp_path / "vault.lock"), "sources": {"savy": str(tmp_path / "savy.json")},
            "savy_prompts": ["What happened?"], "backup_command": None}


def savy(config, text, at=AT):
    Path(config["sources"]["savy"]).write_text(json.dumps([
        {"id": "isolated-fixture-1", "createdAt": AT, "updatedAt": at, "title": text}], ensure_ascii=False))


def validator(config, batch):
    # Unit tests check transaction behavior. The actual Docker validator is run separately on an isolated batch and live dry run.
    result = {"status": "passed", "unit_transaction_fixture": True}
    sync.atomic(batch / "validation.json", sync.dumps(result))
    return result


def snapshot(config):
    return [Path(config[k]).read_bytes() for k in ("graph", "ledger")]


def test_new_source_is_exact_and_repeat_does_not_rewrite_graph_or_ledger(config):
    words = "I feel lighter.\n\nMore awake and aware.  😀"
    savy(config, words)
    code, status = sync.run(config, validator=validator)
    assert code == 0 and status["new_entries"] == 1 and status["LLM_calls"] == 0
    graph = load_graph(Path(config["graph"]), Path(config["ledger"]))
    assert graph.source_entries()[0]["text"] == words
    assert graph.source_entries()[0]["source_created_at"] == AT
    before = snapshot(config)
    mtimes = [Path(config[k]).stat().st_mtime_ns for k in ("graph", "ledger")]
    code, status = sync.run(config, validator=validator)
    assert code == 0 and status["new_entries"] == 0 and status["duplicates_skipped"] == 1
    assert snapshot(config) == before
    assert [Path(config[k]).stat().st_mtime_ns for k in ("graph", "ledger")] == mtimes


def test_edit_and_revert_preserve_all_revisions(config):
    for index, words in enumerate(["I feel lighter.", "I feel awake.", "I feel lighter."]):
        savy(config, words, AT.replace("12:00", f"12:0{index}"))
        code, status = sync.run(config, validator=validator)
        assert code == 0 and status["revisions"] == int(index > 0)
    graph = load_graph(Path(config["graph"]), Path(config["ledger"]))
    assert len(graph.records) == 3 and len(graph.ledger) == 3
    assert len(graph.source_entries()) == 1
    assert graph.source_entries()[0]["text"] == "I feel lighter."


def test_template_and_ai_output_are_not_original_answers(config):
    data = [{"id": "1", "createdAt": AT, "updatedAt": AT, "title": "New Post",
             "postAnswersContainQuestions": True,
             "postAnswers": ["What happened?\nI feel lighter.  ", "What happened?\n"],
             "night": "AI-authored material"}]
    Path(config["sources"]["savy"]).write_text(json.dumps(data))
    code, status = sync.run(config, validator=validator)
    assert code == 0 and status["new_entries"] == 1
    graph = load_graph(Path(config["graph"]), Path(config["ledger"]))
    assert graph.source_entries()[0]["text"] == "I feel lighter.  "
    assert "AI-authored material" not in graph.raw_graph
    assert "What happened?" not in graph.raw_graph


def test_missing_source_is_failure_not_no_new_words_and_does_not_advance(config):
    savy(config, "I feel lighter.")
    assert sync.run(config, validator=validator)[0] == 0
    before, checkpoint = snapshot(config), (Path(config["state_dir"]) / "state.json").read_bytes()
    Path(config["sources"]["savy"]).unlink()
    code, status = sync.run(config, validator=validator)
    assert code == 1 and status["coverage"]["savy"]["status"] == "failed"
    assert snapshot(config) == before
    assert (Path(config["state_dir"]) / "state.json").read_bytes() == checkpoint


def test_validator_failure_keeps_sources_retryable(config):
    savy(config, "I feel lighter.")
    before = snapshot(config)
    def fail(*args):
        raise ValueError("Invalid RDF")
    code, status = sync.run(config, validator=fail)
    assert code == 1 and "Invalid RDF" in status["error"]
    assert snapshot(config) == before
    assert not (Path(config["state_dir"]) / "state.json").exists()
    assert sync.run(config, validator=validator)[1]["new_entries"] == 1


def test_interruption_after_ledger_write_recovers_without_loss_or_duplicate(config):
    savy(config, "I feel lighter.")
    entries, cursors, coverage, exceptions = Collector(config, {}).collect()
    state_dir = Path(config["state_dir"])
    batch = state_dir / "batches/crash-fixture"
    summary, _ = sync.prepare(config, {}, entries, cursors, coverage, exceptions, batch)
    validator(config, batch)
    original_graph = Path(config["graph"]).read_bytes()
    def crash(index):
        if index == 0:
            raise InterruptedError("process stopped after ledger")
    with pytest.raises(InterruptedError):
        sync.publish(config, state_dir, batch, summary, after_write=crash)
    assert Path(config["graph"]).read_bytes() == original_graph
    assert (state_dir / "pending.json").exists() and not (state_dir / "state.json").exists()
    recovered = sync.recover(config, state_dir)
    assert recovered["recovered"] and not (state_dir / "pending.json").exists()
    code, status = sync.run(config, validator=validator)
    assert code == 0 and status["new_entries"] == 0
    assert len(load_graph(Path(config["graph"]), Path(config["ledger"])).ledger) == 1


def test_independent_edit_during_pending_recovery_is_preserved(config):
    savy(config, "I feel lighter.")
    es, cs, cov, ex = Collector(config, {}).collect()
    state_dir = Path(config["state_dir"])
    batch = state_dir / "batches/conflict-fixture"
    summary, _ = sync.prepare(config, {}, es, cs, cov, ex, batch)
    validator(config, batch)
    def crash(index):
        raise InterruptedError()
    with pytest.raises(InterruptedError):
        sync.publish(config, state_dir, batch, summary, after_write=crash)
    Path(config["graph"]).write_text(TTL + "# independently edited\n")
    before = snapshot(config)
    with pytest.raises(ValueError, match="independent edit"):
        sync.recover(config, state_dir)
    assert snapshot(config) == before and (state_dir / "pending.json").exists()


def test_vault_writer_lock_keeps_batch_retryable(config):
    savy(config, "I feel lighter.")
    before = snapshot(config)
    with sync.lock(config["vault_lock"]):
        code, status = sync.run(config, validator=validator)
    assert code == 1 and status["status"] == "retry" and snapshot(config) == before
    assert not (Path(config["state_dir"]) / "state.json").exists()
    assert sync.run(config, validator=validator)[0] == 0


def test_dry_run_does_not_publish_or_advance(config):
    savy(config, "I feel lighter.")
    before = snapshot(config)
    code, status = sync.run(config, dry_run=True, validator=validator)
    assert code == 0 and status["status"] == "dry-run" and snapshot(config) == before
    assert not (Path(config["state_dir"]) / "state.json").exists()


@pytest.mark.parametrize("text", ["# AGENTS.md instructions\ngenerated", "<system-reminder>AI</system-reminder>",
                                 "SAVY SYNC PROBE from Mac facf", "# Pasted document\nunknown author"])
def test_wrappers_fixtures_and_unattributed_documents_not_accepted(text):
    assert own_spans(text)[0] == []


def test_quoted_third_party_and_code_remain_context_not_adams_words():
    text = 'I feel lighter.\n> Assistant said something.\n“Third party”\n```\nAI code\n```\nI feel awake.'
    spans, reasons = own_spans(text)
    originals = [text[a:b] for a, b in spans]
    assert "I feel lighter." in originals[0] and "I feel awake." in originals[-1]
    assert not any("Assistant" in t or "Third party" in t or "AI code" in t for t in originals)
    assert set(reasons) == {"quoted-material", "inline-quotation", "code-block"}


def test_turtle_escape_decoder_preserves_literal_backslash_and_unicode():
    assert unescape(r'Unicode 😀\nline\tand \\"quote\\"') == 'Unicode 😀\nline\tand \\"quote\\"'
    assert unescape(r'Literal \\n stays a backslash') == r'Literal \n stays a backslash'


def test_original_entry_is_retrievable_without_inventing_a_domain(config, tmp_path):
    savy(config, "I feel lighter after escaping malaise.")
    assert sync.run(config, validator=validator)[0] == 0
    graph = load_graph(Path(config["graph"]), Path(config["ledger"]))
    assert "inLifeDomain" not in graph.raw_graph and "strength" not in graph.raw_graph
    narrator = Narrator([], graph, pattern_file=tmp_path / "missing", ontology_root=tmp_path / "missing")
    told = Told()
    lines = narrator.source_road("lighter escaping malaise", told)
    assert lines and "I feel lighter after escaping malaise." in lines[0]
    rows = records_told(told, graph)
    assert rows[0]["quote"] == "I feel lighter after escaping malaise."
    assert rows[0]["source_created_at"] == AT and rows[0]["accepted_at"] == AT


def test_codex_reads_root_human_submissions_but_not_assistant_or_exec(config, tmp_path):
    p = tmp_path / "interactive.jsonl"
    def record(kind, payload):
        return json.dumps({"type": kind, "timestamp": AT, "payload": payload}) + "\n"
    p.write_text(record("session_meta", {"id": "root", "source": "vscode"}) +
                 record("turn_context", {}) +
                 record("response_item", {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "AI opinion"}]}) +
                 record("response_item", {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "I feel lighter."}]}))
    collector = Collector(config, {})
    assert collector.transcript(p, "codex") == 1
    assert [e["text"] for e in collector.entries] == ["I feel lighter."]
    later = Collector(config, collector.cursors)
    assert later.transcript(p, "codex") == 0
    p.write_text(p.read_text().replace('"vscode"', '"exec"'))
    automated = Collector(config, {})
    assert automated.transcript(p, "codex") == 0 and automated.entries == []


def test_codex_page_and_image_envelopes_are_context_even_in_a_user_turn(config, tmp_path):
    p = tmp_path / "interactive-attachments.jsonl"
    def record(kind, payload):
        return json.dumps({"type": kind, "timestamp": AT, "payload": payload}) + "\n"
    envelopes = ['<external_codex_apps_open_page>{"page":null}</external_codex_apps_open_page>',
                 '<image name=[Image #1] path="/fixture/screenshot.png">', '</image>',
                 '<future_attachment kind="generated">metadata</future_attachment>']
    p.write_text(record("session_meta", {"id": "root", "source": "vscode"}) +
                 record("turn_context", {}) + record("response_item", {
                     "type": "message", "role": "user", "content":
                     [{"type": "input_text", "text": text} for text in envelopes] +
                     [{"type": "input_image", "image_url": "isolated-fixture"},
                      {"type": "input_text", "text": "I feel lighter.  "}]}))
    collector = Collector(config, {})
    collector.transcript(p, "codex")
    assert [e["text"] for e in collector.entries] == ["I feel lighter.  "]
    assert [e["source_text"] for e in collector.exceptions] == envelopes


def test_previously_admitted_app_metadata_is_quarantined_without_erasing_history(config):
    savy(config, "I feel lighter.")
    c = Collector(config, {})
    entries, cursors, coverage, exceptions = c.collect()
    # Reproduce an old collector's false admission, only in an isolated vault.
    raw = '<external_codex_apps_open_page>{"page":null}</external_codex_apps_open_page>'
    fragment = '<external_codex_apps_open_page>{'
    old = dict(entries[0], identity="codex:isolated-envelope:user_prompt:span:0", adapter="codex",
               text=fragment, text_sha256=digest(fragment), source_text=raw, source_sha256=digest(raw),
               char_start=0, char_end=len(fragment))
    state_dir = Path(config["state_dir"])
    batch = state_dir / "batches/old-wrapper-fixture"
    summary, _ = sync.prepare(config, {}, entries + [old], cursors, coverage, exceptions, batch)
    validator(config, batch)
    sync.publish(config, state_dir, batch, summary)
    before = load_graph(Path(config["graph"]), Path(config["ledger"]))
    assert len(before.source_entries()) == 2
    code, status = sync.run(config, validator=validator)
    assert code == 0 and status["quarantined_generated_entries"] == 1
    graph = load_graph(Path(config["graph"]), Path(config["ledger"]))
    assert [e["text"] for e in graph.source_entries()] == ["I feel lighter."]
    assert graph.ledger[:len(before.ledger)] == before.ledger
    assert graph.raw_graph.startswith(before.raw_graph)
    assert len(graph.records) == len(before.records) == 2
    assert graph.ledger[-1]["actor"] == "cowboyai-word-sync"
    assert status["readback"]["generated_entries_no_longer_accepted"] == 1
    unchanged = snapshot(config)
    mtimes = [Path(config[k]).stat().st_mtime_ns for k in ("graph", "ledger")]
    assert sync.run(config, validator=validator)[1]["quarantined_generated_entries"] == 0
    assert snapshot(config) == unchanged
    assert [Path(config[k]).stat().st_mtime_ns for k in ("graph", "ledger")] == mtimes


def test_partial_transcript_line_is_read_on_next_run(config, tmp_path):
    p = tmp_path / "claude.jsonl"
    raw = json.dumps({"type": "user", "timestamp": AT, "uuid": "1",
                      "message": {"role": "user", "content": "I feel lighter. 😀"}}, ensure_ascii=False).encode()
    p.write_bytes(raw[:-5])
    collector = Collector(config, {})
    assert collector.transcript(p, "claude") == 0 and collector.cursors["files"][str(p)]["offset"] == 0
    with p.open("ab") as f:
        f.write(raw[-5:] + b"\n")
    later = Collector(config, collector.cursors)
    assert later.transcript(p, "claude") == 1 and later.entries[0]["text"] == "I feel lighter. 😀"


def test_questions_remain_questions_and_instruction_remains_input(config):
    c = Collector(config, {})
    c.emit("codex", "1", "user_prompt", "why I cannot feel happy", AT)
    c.emit("codex", "2", "user_prompt", "Do it. Verify it works.", AT)
    assert [e["role"] for e in c.entries] == ["question", "input"]


def test_claude_sidechain_and_model_fills_are_not_collected(config, tmp_path):
    p = tmp_path / "claude.jsonl"
    p.write_text(json.dumps({"type": "user", "timestamp": AT, "isSidechain": True,
                            "message": {"role": "user", "content": "Subagent instruction"}}) + "\n")
    c = Collector(config, {})
    assert c.transcript(p, "claude") == 0 and c.entries == []


def test_changed_published_word_is_a_conflict_not_silently_overwritten(config):
    savy(config, "I feel lighter.")
    assert sync.run(config, validator=validator)[0] == 0
    path = Path(config["graph"])
    path.write_text(path.read_text().replace('understood:exactWords "I feel lighter."', 'understood:exactWords "Changed independently."'))
    before = snapshot(config)
    code, status = sync.run(config, validator=validator)
    assert code == 1 and "changed independently" in status["error"]
    assert snapshot(config) == before


def test_user_text_before_a_template_is_preserved_as_its_own_exact_span(config):
    Path(config["sources"]["savy"]).write_text(json.dumps([
        {"id": "1", "createdAt": AT, "updatedAt": AT, "title": "New Post",
         "postAnswersContainQuestions": True, "postAnswers": ["My observation..What happened?\n\nI feel lighter."]}]))
    code, status = sync.run(config, validator=validator)
    assert code == 0 and status["new_entries"] == 2
    texts = {r["text"] for r in load_graph(Path(config["graph"]), Path(config["ledger"])).source_entries()}
    assert texts == {"My observation..", "\nI feel lighter."}


def test_late_earlier_revision_keeps_latest_text_and_does_not_duplicate(config):
    savy(config, "I feel awake.", AT.replace("12:00", "12:02"))
    assert sync.run(config, validator=validator)[0] == 0
    savy(config, "I feel lighter.", AT)
    assert sync.run(config, validator=validator)[1]["revisions"] == 1
    graph = load_graph(Path(config["graph"]), Path(config["ledger"]))
    assert len(graph.records) == 2 and graph.source_entries()[0]["text"] == "I feel awake."
    assert sync.run(config, validator=validator)[1]["new_entries"] == 0
    assert len(load_graph(Path(config["graph"]), Path(config["ledger"])).records) == 2


def test_savy_gateway_preserves_form_answers_notes_and_only_new_receipts(config, monkeypatch):
    import io
    import nucleus.word_sources as sources
    item = {"receipt": {"received_at": AT}, "payload": {"source_app_surface": "savy_ios", "request_id": "request-1",
            "capture_id": "capture-1", "reminder_id": "reminder-1", "created_at": AT,
            "exact_words": {"want": "I feel lighter.", "when_i_am": "", "done_looks_like": ""},
            "metadata": {"notes": "I feel awake.", "postAnswersContainQuestions": True,
                         "postAnswers": ["What happened?\n\nI feel aware.  "], "night": "AI fill"}}}
    monkeypatch.setattr(sources, "urlopen", lambda *a, **kw: io.StringIO(json.dumps({"intakes": [item]})))
    collector = Collector(config, {})
    status = collector.gateway("http://127.0.0.1/fixture")
    assert status["new_intakes_read"] == 1 and status["original_form_answers_and_notes_included"]
    assert {e["text"] for e in collector.entries} == {"I feel lighter.", "I feel awake.", "\nI feel aware.  "}
    assert all("AI fill" not in e["text"] for e in collector.entries)
    repeated = Collector(config, collector.cursors)
    assert repeated.gateway("http://127.0.0.1/fixture")["new_intakes_read"] == 0 and repeated.entries == []
