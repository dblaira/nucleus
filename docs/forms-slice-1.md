# Slice 1 — the forms themselves

Built against `c80d471ebb394821e680c35cb98b8e9227d0c2ab` on
`codex/forms-slice-1`. User request received October 1, 2026 Pacific; the
supplied plan is dated October 2. Implementation stops before slice 2.

## Scope

`nucleus/forms.py` loads, checks, and fills forms. `nucleus/store.py` adds
`form_proposals` on Store initialization, preserving all existing tables.
`forms.txt` has zero forms. There is no day-path integration, ranking,
background pass, approval action, phone page, switch, or service deployment.
No live database was opened with the modified Store. Schema preservation was
exercised on a temporary database containing existing questions and answers.

The user authorized slice 1 as written, including `forms.txt` in this repo.
The plan's longer-term ownership question remains open; no files were written
in adams-language. Existing working files in the original nucleus checkout
were left intact. The exact supplied `FORMS-PLAN.md` is included here.

## File format

`forms.txt` uses TOML, one `[[forms]]` block per form. An empty file is
represented as `forms = []`. Remove that empty-list declaration when adding
the first block. All six top-level fields are required. Strings retain their
case and spacing. Dates are quoted ISO dates. Duplicate numbers, unknown
fields, invalid syntax, and missing files fail closed.

This is a **proposed example**, not an approval:

```toml
[[forms]]
number = "F-7"
sentence = "Your rows say {word} depends on {count} things you have written down."
status = "proposed"
author = "Cowboyai Forms Plan"
date = "2026-10-02"
[forms.when]
answer = "aligned"
kinds_present = ["depends on"]
```

`load()` preserves each form's status. `check()` never approves a form.
`fill()` returns `None` for proposed or rejected forms, unmet conditions,
and missing or ambiguous blank values. Malformed forms or screens and unsafe
filled text raise `forms.Refused`. The caller must treat refusal as no form;
it must never show partial output. Approved status belongs only to Adam's yes.
There is no approval writer in this slice.

## Conditions

All specified conditions must hold. At least one condition is required.

| Key | Value |
| --- | --- |
| `answer` | `aligned`, `not_sure`, or `dont_know` |
| `kinds_present` | Nonempty list; every exact middle word appears in the rows |
| `kinds_absent` | Nonempty list; none of the exact middle words appears |
| `record_count` | Exact nonnegative integer, or `{min = N, max = N}`; either bound may be omitted |
| `word_count` | Same syntax, counting distinct displayed words |
| `missing_links` | Boolean supplied from the picture's missing-links state |

Middle words are read from the existing `kinds.load_kinds()` source. No copied
list or new relationships govern production. Count booleans, negative counts,
reversed ranges, contradictory middle-word conditions, and unknown keys fail.

## The screen and blanks

The caller supplies one immutable `Screen` snapshot: answer label, displayed
words in order, displayed `Row(word, record, kind)` values in order, and the
missing-links flag. Each record appears once, matching today's painted rows.
Every row word must be in the displayed words. A row may have no middle word;
unknown middle words fail. Never construct this snapshot from additional
hidden links. Slice 2 owns connecting it to the exact displayed picture.

| Blank | Source and binding |
| --- | --- |
| `{word}` | Word of the first row carrying the single firing middle word; otherwise the first displayed word |
| `{other_word}` | First distinct displayed word other than `{word}` |
| `{kind}` | Exact middle word copied from a matching row; requires one `kinds_present` entry |
| `{count}` | Number of displayed rows carrying that same middle word; requires one `kinds_present` entry |
| `{word_count}` | Number of distinct displayed words |
| `{strongest_kind}` | Most frequent middle word in displayed rows; ties keep the first one on screen |

If `{word}` and `{count}` occur together but the matching rows carry several
different words, the form does not fill: a total over several words cannot
be presented as one word's count. These are deterministic binding conventions
for implementation, not new definitions or accepted relationships.

`Filled` carries the form number, exact paragraph, and a `Part` for every
literal or replacement with its origin. It does not add a number to the
paragraph text. The later screen integration must display `Filled.number`.

## Kill switch

Only literal template slices, exact screen words/middle words, and decimal
counts of those rows/words are concatenated. There is no model, search,
question input, quote lookup, inflection, case normalization, fallback text,
Python formatting access, or recursive expansion. Python conversions,
attributes, indexes, format specifications, and unknown braces are refused.

A token check after concatenation refuses any word made by joining pieces
that did not appear in any source piece, including `prefix{word}` and
`{word}{other_word}`. Both the template and filled paragraph reuse
`explain.check` (including its ADVICE pattern), and are checked for one
paragraph and at most four sentences. Sentence counting is conservative:
abbreviations may be refused rather than allowing extra sentences through.

The code cannot emit a filled sentence that breaks this source boundary.
Tests exercise the boundary, including 200 deterministic variations of screen
words and row counts, unicode, contractions, punctuation, inserted braces,
advice in a screen value, and accidental word joins.

## Proposals

`Store.save_form_proposal` inserts a new UUID on every call, even for repeated
form numbers. It retains the complete JSON payload. A supplied refusal reason
marks the new row rejected. `reject_form_proposal` retains the original and
cannot overwrite an earlier rejection. No delete or approval method exists.

`form_proposals()` returns the original `payload` for inspection plus `form`
with the database's status. Use `form` for validation, never raw `payload`:
a model writing `status = approved` is still a proposal. The eventual day path
must load approved forms from `forms.txt`, never the proposals table.

## Verification and stop

Baseline: **58 passed**. Final: **132 passed**, including those original 58.
The schema addition preserves existing question/answer rows and SQLite
integrity in an isolated database. Proposal persistence survives reopening.

The running service's read-only saved-answer endpoint returned 15 FLOW rows,
including exactly three `depends on` rows. The plan's F-7 example, used only
as an isolated test fixture, filled as:

> **F-7** — Your rows say FLOW depends on 3 things you have written down.

[The proof](forms-slice-1-proof.json) identifies the three exact record IDs and
the source of every output part. This verifies the filler against real saved
rows; it is not a new paragraph delivered to the phone. Product `forms.txt`
remains empty. The existing service and phone were not changed.

**Stopped at the end of slice 1. The source-boundary check passes. Slice 2 has
not been started.**
