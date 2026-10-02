# Forms slice 3c — exact row quotes

October 2, 2026 Pacific. Branch `codex/forms-slice-3c`, based exactly on
`25782d8017a6d9c5ee80a9b75c0d6d4c1b033c4e`.

## What changed

`{quote:depends on}` copies the complete displayed quote of a row for the
named middle word. It uses the same word as `{word}` and records the source
as `screen.rows[N].quote`. The screen snapshot carries the quote and record ID.
The painted branch and historical reconstruction use the same display unescape
as the existing row renderer. Spaces, punctuation, braces, and wording remain
exact; there is no record lookup, clipping, paraphrase, or recursive filling.
Old snapshots without quotes still support old blanks but cannot fill quote slots.

Each quoted kind must be in `kinds_present`. Among that word's rows with that
kind, the filler chooses the shortest complete quote that passes the checks:
fewest words, then character length, then original screen order. A missing safe
quote makes the form inapplicable. It never borrows a different word's row.
For two or more kinds, `{word}` remains the first displayed word.

Night proposals must join at least two distinct named quote slots and include
`{word}` in one sentence. Repeating one slot cannot stand for two rows. The
slice 3b pattern gate still applies. Counts and middle-word inventories are
refused. The concrete join requested by Adam is sufficient; the old abstract
commentary is no longer requested.

The literal template, each eligible quote, and final filled text pass the
existing advice, paragraph, and provenance checks plus new negative/caveat and
blocked-word checks. The checks include contractions, case and Unicode variants,
and inflections of the blocked words; checking never changes source text.
The night reviewer assesses faithful direction, one sentence, negatives/caveats,
and fifth-grade reading level across **every distinct filled example**. An
integer grade above 5 refuses the proposal; missing or malformed judgments fail
the run closed. Up to three examples per proposal are saved as before, with all
reviewed examples retained in the model-call prompt.

Nothing in either review approves a form. The day uses only Adam-approved
`forms.txt` entries, with no model when one fits. The file remains empty and
`NUCLEUS_FORMS_ONLY` stays off. No slice 4 page or approval action exists.

## Copy run

The existing review copy was backed up using SQLite's backup API to
`~/Library/Application Support/nucleus/forms-review/slice-3c-before.sqlite3`.
Both files passed integrity checks before the pass. The live file was never
opened. Command, run from this branch's worktree:

```sh
/Users/adamblair/Documents/nucleus/.venv/bin/python -m nucleus.forms night \
  --store '/Users/adamblair/Library/Application Support/nucleus/forms-review/nucleus.sqlite3' \
  --bootstrap
```

Run `1c9f17af-361a-4c18-a945-4fd6ad64c9f0` completed through the existing model
door: Codex `gpt-5.6-sol`, one writer call and one separate reviewer call.
Policy `quotes-v1` revisited the historical inputs once: 120 painted answers,
106 usable, 14 retained as skipped because their saved middle words could not
be recovered unambiguously.

The writer returned **11 candidates: 3 proposed and 8 refused**.

| Forms | Result | Reason |
|---|---|---|
| F-25, F-26, F-31 | Proposed, awaiting Adam | Reviewer rated each grade 5; faithful row joins |
| F-28, F-29, F-30, F-33, F-35 | Rejected | Reviewer rated grade 6 |
| F-27, F-32 | Rejected | Reviewer rated grade 7 |
| F-34 | Rejected | No safe filled example; no supplied screen has its required 40 rows and 4 words |

The raw reviewer also objected to F-27's “is part of” relationship as
“containment.” That is an overbroad reading of the banned **word**; the allowed
middle word is not banned by the program. Its grade 7 independently refuses it.
The complete review response is retained unchanged in the local report and copy.

**All twelve slice 3b forms, F-13 through F-24, are rejected.** Eleven changed
from proposed to rejected: ten contain “not” and one contains “neither.” F-19
was already rejected and its original reason and decision time remain intact.
All original proposal payloads and earlier examples remain intact.

## Verification

**273 tests pass.** This includes quote provenance, exact whitespace and
punctuation, missing quotes, same-word binding, shortest safe whole-row choice,
negative/caveat and blocked-word refusal, quote advice refusal, named-kind
validation, duplicate-slot and multiple-sentence refusal, fifth-grade limits,
malformed-review failure, and all-3b rejection with original payload retention.
The painted-answer integration test proves provider `form`, zero model-call
rows, and exact quotes present in the returned screen. Existing zero-approved
fallback, copy-only guard, transaction, retry, and approval tests still pass.

All 10 saved examples refill exactly; all 20 quoted parts match their original
saved screen rows word for word. The backup hash is unchanged and both database
integrity checks pass. Earlier answers, links, explanations, calls, runs,
results, and proposal payloads are preserved. Only the eleven pending 3b
proposals' status, reason, and decision time changed. The pass added two model
calls, one run, eleven results and proposals, and eleven refusal audit entries.

The unchanged launchd plist remains in the repo only: no installed plist and
`launchctl print gui/501/com.nucleus.forms` returns service-not-found (113).
No service or phone deployment, merge to main, or live database migration was
performed. The original checkout's dirty and untracked files remain untouched.

Evidence: [night summary](forms-slice-3c-night.json),
[preservation and quote proof summary](forms-slice-3c-proof.json).
This repository is public. Committed evidence contains counts, form templates,
review results, and hashes of filled text; it omits personal screen text,
questions, and quotes. The complete report and proof remain locally in
`~/Library/Application Support/nucleus/forms-review/slice-3c-night.json` and
`slice-3c-proof.json`. The local proof contains five filled examples: all three
proposed examples and two rejected examples, with grade and status. Five exact
examples are also supplied in the Codex reply. Only three passed; source quotes
were not rewritten to manufacture two more.

**Stopped before slice 4.**
