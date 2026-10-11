# Adam's exact words, every 15 minutes

Implementation authorization, Adam, October 11, 2026:

> Do it. Set up the 15-minute sync so my knowledge graph and RDF triples stay current using my exact words, without asking for approval again. Verify it works.

Standing approval, October 10, 2026:

> My words do not need approval.  They are my words which means they went though an approval process before they were spoken.  Approve all candidates that use only my words.

## Ownership and scope

One writer owns `word_sources.py`, `word_sync.py`, `word_sync_validator.py`, the narrowly extended graph reader, original-entry retrieval, installer and tests. Base commit: `f9e326dcfcf996c959f9ec65d169d0c246690696`. Its only data writes are new source snapshots, appended RDF source entries, appended acceptance decisions, external recovery backups, checkpoints and status. The existing Obsidian backup program remains the only vault Git writer.

Forbidden writes: source application databases, original saved answers, existing RDF/decisions, dictionary meanings/routes, Notion, iOS files and unrelated work. No model inference, invented relationship, strength or life-domain classification is part of ingestion.

## Sources and authorship

The first run catches up from October 10, 2026, midnight Pacific, overlapping the accepted October refresh. Thereafter source cursors and original-text hashes make repeated reads idempotent. An edited field adds a numbered revision and preserves the previous entry. Deletion at a source never deletes its recorded versions.

- All Entries: original `user_prompt` records from known apps; index hash and canonical Markdown must agree. Screen captures and saved mixed-author documents are excluded.
- Cowboy AI: original questions, original theme answers, and original more-information entries. Grading/CLI lanes, template prompts and `night` model output are excluded.
- SAVY: a dated, hash-verified initial snapshot of original stored fields, captured during authorized setup. A LaunchAgent cannot open its private app container. The app already enqueues a complete native capture on each save (`ReminderStore.swift:176`), including notes and original form answers; future updates are collected through that existing intake stream. No new OS permission is required. Placeholder titles and known test probes are excluded; template boundaries and any user text before a template are preserved separately.
- SAVY gateway intakes: immutable native `exact_words`, notes, form answers and original typed metadata; transport receipts remain unchanged. Request IDs form an incremental cursor. Capture event dates are distinguished from the initial stored-record dates. Late-delivered earlier versions are preserved without replacing the newest version.
- Codex: root interactive session submissions after turn context; assistant/tool turns and exec/subagent sessions are excluded. An incremental tail reader handles active older sessions and missed date directories after sleep.
- Codex Page/image attachment envelopes remain transport context even when delivered in a user-role message. Structured question replies provide an explicitly identified human `answer` field: its decoded exact text is captured, while the complete envelope and original field identity remain provenance. A one-time source-schema backfill restores prior reply fields without duplicating prior inputs. Other markup blocks remain unresolved document context. An authorship audit checks accepted source entries against their retained source snapshots. If a previously admitted entry is verified transport metadata, it appends a program correction and provenance annotation; it preserves the original record and decision while removing acceptance. It never edits Adam's text or requests another approval.
- Claude: root human prompts; sidechains, compacted summaries, meta/tool turns and subagent files are excluded.

Quoted third-party text, code and document wrappers remain in the full source context/collection exceptions. They are not asserted as Adam-authored words. Unmarked pasted material has no universally observable authorship marker; source entries retain the fact that they were input, rather than asserting that their contents are personal beliefs or causal facts. Collection issues are reported in status, without another approval request.

## RDF and retrieval

New records use `understood:SourceEntry`, distinct from relationship `Connection` records. Each has exact text, original role, source identity, source revision, original creation/modification dates, acceptance time, hash, source-snapshot location and `prov:wasDerivedFrom`. Edits also have `prov:wasRevisionOf`. No life domain is manufactured to satisfy the relationship shape.

The shared graph reader admits these entries under their specific acceptance decisions. `GET /exact-words?query=...` retrieves original text, role and source date without a model. The existing narrative can quote relevant originals when no dictionary/relationship answer was found; original questions are excluded from that answer fallback. Literal overlap is not causation. Existing answers and established answer routes remain preserved. The graph's existing mtime reload applies to new queries.

## Publication and recovery

The sync and backup share `~/.local/state/obsidian-backup/runner.lock`. Staging and recovery copies live outside the vault under owner-only `~/.local/state/cowboyai-word-sync`. Docker runs the pinned validator image offline, read-only and without capabilities. It parses RDF, checks source offsets/hashes, requires the old RDF/ledger to remain intact, and rejects any newly introduced SHACL violation. The existing legacy `domain/focus` violation is reported, not hidden. A separate source-entry shape checks original-entry metadata.

Publication saves provenance first, then the appended ledger, then the graph, using atomic file replacements. A durable journal precedes accepted-file writes. The cursor moves only after exact text, acceptance and original dates are read back through the shared reader. A process interruption completes from that journal; independently edited files stop recovery with both versions retained. A source/validation/lock failure advances no source cursor. Backups are read back from the sole vault backup owner's status and retried if needed.

`scripts/install_word_sync.py` requires committed code, copies a content-hashed release outside Documents, pins the Docker image ID, and installs `com.adamblair.cowboyai-word-sync`: `StartInterval=900`, `RunAtLoad=true`. Docker starts in the background if validation needs it. Successful runs are quiet and use zero LLM calls/tokens. The Mac must be awake; the next run catches up after sleep/login.

Status: `~/.local/state/cowboyai-word-sync/status.json`. Original-source exceptions, per-source read failures, last success, new entries/revisions, duplicates, validation and remote backup are separate fields. A failed source is never reported as no new words.

## Acceptance evidence

See Cowboyai `claude/reports/2026-10-11-automatic-word-sync.md` for the installed job, live run, scheduled run, exact-word readback, unchanged repeat, private remote backup and Protégé inspection. Unit fixtures are isolated and never published as Adam's words.
