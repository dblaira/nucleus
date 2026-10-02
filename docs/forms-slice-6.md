# Forms slice 6

Built from `e9345c64cb47482ea679923820814001ead42c8b` on
`codex/forms-slice-6`, in `/Users/adamblair/.codex/worktrees/nucleus-forms-slice-6`.
The exact request is preserved in the private Cowboyai ledger.

## Practice at night

The night pass starts with one bounded AI call for at most 20 new practice
questions. Its prompt uses exact dictionary words and meanings, and exact
question shapes from `web` and `cowboyai-iphone`. The existing dictionary reader
and phrase matcher must find the stated dictionary target. Normalized old or
repeated questions, unknown targets and overflow are retained as refusals.

Accepted questions go through normal ask, dictionary, painting/model and quote
gate on the explicit copy, with `surface="practice"`. Actual outcomes are saved;
there is no forced answer or manufactured screen. Practice keeps form selection
and miss snapshots. Its extra background explanation is skipped because the
saved answer already supplies the screen for form testing, and a background
model would outlive the bounded night operation.

The generator reply, provider/model, target check and every ask result remain
in additive `form_practice_runs` and `form_practice_results` tables. A malformed
generator fails the night before form writing. Individual ask failures stay
auditable and never count as fitting screens.

## One real question anchors each form

Coverage uses complete saved real and practice screens. Grade, command-line and
unknown surfaces cannot count as Adam's questions. Each normalized question
counts once globally; a real screen takes priority over a repeated practice
screen, and repeats cannot add another bound word. All different filled texts
still reach the semantic reviewer.

A form needs at least three different fitting questions, two words actually
bound into the form, and one real question. The first two floors retain
`fits too few answers`; an all-practice form is refused as
`needs one real question`. Counts remain minimums or ranges. All earlier exact
quote, missing-half, no-advice, fifth-grade, and approval rules remain.

Conditions alone identify a form, with nulls removed and middle-word lists
sorted. The first proposal is kept; the rest with those conditions are refused
as `same form`, regardless of wording. Changed or widened conditions remain
different. Rejected forms and their original traces remain retained.

Still-proposed earlier forms are measured again on each successful night.
The append-only `form_coverage_checks` table saves refreshed coverage and
examples together. The page reads both from the same latest completed run;
failed runs cannot publish refreshed evidence. Original snapshots remain
unchanged, and no rejected form is revived.

## Review and isolation

The same page on 8767 shows `fits N of your questions · M practice questions`,
biggest total first, with up to three filled examples for different words and
questions. Examples say whether they come from a real or practice question.
There are still only Yes and No, no editing. Nothing is approved in this slice.

Live paths, symbolic/hard links and even a mismatched Store connection are
refused before practice writes or inference. Practice is excluded from recent
history, direct answer-history endpoints, real repeat lookup/counts, grade
writes and link seeding. Source meanings, routes, graph and ledger are read
only. The live database and service on 8766 are never opened or requested.

## Verification

Tests cover normal ask and quote gating for practice, the 20-question cap,
newness/target checks, retained failures, live aliases and supplied-ID spoofing,
history/repeat/grade/link isolation, real/practice coverage, one real anchor,
condition-only identity, and default night sequencing. No test approves a real
form or operates on the runtime copy.

The one manual copy pass and final runtime verification are recorded below.

### One manual pass

Run `a73a7619-ec4f-4176-a64e-4b3ab3affba4` completed with 96 inputs / 88 usable.
The practice generator used 85 distinct real-surface questions as examples.
It wrote 20 new questions; all 20 passed dictionary target checks and normal
ask's gate. All were painted **aligned**, with zero per-question model calls.
The pass preserved the normal answer rules rather than forcing a not-sure
result to create form evidence.

The night writer returned `{"forms":[]}`: **0 proposed and 0 refused**. No
candidate reached semantic review. Two night model calls were saved, one for
practice generation and one for form writing. The 20 practice screens remain
available for future passes. There was no second runtime pass.

### Preservation and running page

**423 tests pass.** Backup `slice-6-before.sqlite3` and both integrity checks
pass; all 4,491 earlier rows are exact. Real history, grades, links, searched
words, candidates, explanations and six source hashes are unchanged. An
independent read-only audit verified all 20 new targets/screens and 307
retained source parts. There are 42 rejected forms, zero pending and zero
approval receipts; `forms.txt` remains empty.

Browser inspection of isolated synthetic fixtures verified separate real and
practice labels and largest-first ordering. The real review page is correctly
empty. Phone link: **http://100.111.154.126:8767/forms**. It runs this worktree
against only `forms-review/nucleus.sqlite3`, with `NUCLEUS_FORMS_ONLY=0`.
Manifest/log: `slice-6-server.json` and `slice-6-server.log` beside the copy.
Live PID 1941 on 8766 is untouched. Nothing approved, installed or merged.

[Sanitized night summary](forms-slice-6-night.json) and
[preservation proof](forms-slice-6-proof.json) contain counts/hashes only.
Full question, screen, generator and provider records stay local.
