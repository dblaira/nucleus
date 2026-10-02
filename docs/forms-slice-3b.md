# Forms slice 3b — explain what the pattern means

Branch `codex/forms-slice-3b`, based exactly on
`7249b63abc78e5df9277aa797fd59681ec3f5b84`.

## Result of the rerun

**11 new proposals; 1 new refusal.** The writer returned F-13 through F-24.
The separate meaning review refused **F-19** because its sentence assumed
that the thing appearing alongside a word was also the thing distinguished
from that word. Those two rows can point to different records.

**The 12 earlier proposals were also refused and kept:** F-1 through F-11
have conditions that do not require a pattern; F-12 merely lists the middle
words present. Their original payloads, examples, and first-run trace remain
unchanged. Only their current status, refusal reason, and decision time changed.
No form is approved.

The run used the same existing database copy and the same 120 historical
painted answers. There are 106 reconstructable answers and 14 skipped sources
whose printed middle words cannot be recovered unambiguously. Those skipped
answers are separate from form refusals. The copy contains no saved source
with missing links, so this run did not invent a missing-links example.

Two calls used the existing Codex door, `gpt-5.6-sol`: one writer and one
batch reviewer. Run ID: `bf075602-fcb5-4c95-8ce7-1463697ffacd`.
The pass kept 17 filled examples for proposed forms and one example for the
new refused form. Every saved example was refilled exactly from its snapshot.

### Five exact proposed examples

- **F-14:** For A VISION, including something does not establish that it is a prerequisite; containment and necessity are different claims.
- **F-16:** For FLOW, support and rejection can apply to different connections, so their coexistence does not establish a contradiction.
- **F-17:** For LIFT, moving together and being necessary are different claims; association alone does not establish a prerequisite.
- **F-21:** For FLOW, backing something and making something possible are distinct claims; support alone does not establish enablement.
- **F-24:** For LIFT, belonging within something is different from varying alongside something; correlation does not establish membership.

[The complete report](forms-slice-3b-night.json) includes each new proposal's
original payload and current status, firing conditions, filled examples and
source IDs, all refusal reasons, and the complete meaning-review reply.
[The proof](forms-slice-3b-proof.json) records preservation checks and five
examples with their full screen snapshots and part origins.

## Change and boundary

Objective: replace row inventories with proposed explanations of row patterns.
Authoritative inputs: Adam's slice 3b request in `HANDOFF.md`, the unchanged
`FORMS-PLAN.md` rules, and the preserved slice 3 database copy.
This branch owns only the night pass, its checks/schema/tests, its additive
refusal audit, and these documents. The day picker/filler, `ask.py`, `serve.py`,
`forms.txt`, and launchd plist are unchanged. Meanings, routes, graph, live
storage, installed services, and the phone are outside this change.

`forms_patterns.check` requires one of the following in the conditions:

- At least two distinct `kinds_present` together.
- A present kind from Adam's stated opposition examples: `rejects`,
  `contradicts`, `prevents`, `inhibits`, `constrains`, `limits`.
- `missing_links = true`.

Counts, an answer label, absent kinds, or a single other middle word do not
qualify. The existing list of 43 middle words is still authoritative. None
of these checks adds a middle word to that list.

A deterministic check refuses sentences composed only of counts, middle
words, and the vocabulary of describing rows. It catches the previous style,
including a sentence listing two kinds. A token outside that vocabulary is
not acceptance: every surviving candidate goes to a separate night-time
meaning review through the existing model door and `forms-review.schema.json`.

The reviewer must classify each numbered form as `explains_pattern`,
`restates_rows`, or `unsupported_meaning`, with a concrete reason. It examines
the conditions and filled examples, including scope, relationship direction,
and whether kinds can refer to different words or records. It is instructed
to judge what the conditions guarantee for every matching screen. Counts
may accompany a supported explanation but cannot be the entire explanation.
Missing links mean missing evidence, not evidence against a word or the user.
Semantic classification is a model judgment; it never confers Adam's approval.

Code validates a complete one-to-one set of reviews. Missing numbers,
duplicates, unknown verdicts, empty reasons, malformed JSON, or model failures
fail the run closed. No partial proposal batch or prior rejection is committed,
and those inputs remain available for retry. Both prompts and replies are
retained in `model_calls`, with `:review` on the second call's trace ID.

All previous safety checks still run: known blanks and conditions, exact
screen bindings, allowed middle words, no advice, four sentences maximum,
paragraph length, word provenance, safe examples, duplicate history, and
at most 12 new proposal rows. Every candidate is filled against all usable
inputs before up to three distinct examples are saved. New forms remain
`proposed`; review failures remain `rejected`, with raw payloads and examples
retained. Reports distinguish that current status from the unchanged payload.

Existing pending proposals are checked against the new structural and
inventory rules; deterministic refusals are retained in
`form_night_rechecks` with their run and proposal IDs. The rejections and new
batch commit atomically. Previously rejected rows and approved-file entries
are not rewritten. This pass's old twelve all fail those deterministic checks.

Input fingerprints now start with `patterns-v1`. This revisits old source
answers once for the changed requirement without clearing earlier consumption
history. Later passes with this same policy consume only new inputs. The
existing downvote timestamp limitation described in slice 3 is unchanged.

## Copy and proof

The live database was not opened for this work. Before the rerun, SQLite's
backup API made an additional backup of the existing review copy:

- Run copy: `~/Library/Application Support/nucleus/forms-review/nucleus.sqlite3`
- Before-run backup: `~/Library/Application Support/nucleus/forms-review/slice-3b-before.sqlite3`
- Manifest: `~/Library/Application Support/nucleus/forms-review/slice-3b-copy-manifest.json`
- CLI output: `~/Library/Application Support/nucleus/forms-review/slice-3b-night.json`
- Report with current status separated from original payload: `~/Library/Application Support/nucleus/forms-review/slice-3b-reviewed-report.json`

Command, from the slice 3b worktree:

```sh
/Users/adamblair/Documents/nucleus/.venv/bin/python -m nucleus.forms night \
  --store '/Users/adamblair/Library/Application Support/nucleus/forms-review/nucleus.sqlite3' \
  --bootstrap
```

**226 tests pass**: the unchanged 154 filler/day tests, 30 night-pass cases
with fixtures updated for the new requirement, and 42 additional pattern and
review cases. New cases cover all three firing alternatives, each named
opposing kind, all twelve old forms, restatement variants, unsupported
meaning, source-only filling, rejected-report status, incomplete review,
retry, prior-proposal preservation, rollback, and one-time policy revisiting.
No test was skipped or removed.

All original question, answer, link, explanation, and earlier model-call rows
in the copy are unchanged. Earlier night-run inputs/results are unchanged.
The twelve old proposal payloads are unchanged; their three status fields
were the only existing data updated. The new work adds twelve proposal rows,
twelve result rows, twelve prior-refusal audit rows, one run, and two model calls.
The copy and backup pass integrity checks, and the backup hash is unchanged.

`NUCLEUS_FORMS_ONLY` remains unset/off. `forms.txt` remains empty. The plist
is still repository-only; no installed plist exists and launchctl reports
no `com.nucleus.forms` service. No deployment or merge to main was performed.

**Stopped before slice 4. No approval page or approval action is built.**
