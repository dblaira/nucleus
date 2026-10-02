# Forms slice 7b

Base: `f3d94971ceb9281b3c6000ae3ff55ea9eff3223f`. Branch:
`codex/forms-slice-7b`; worktree:
`/Users/adamblair/.codex/worktrees/nucleus-forms-slice-7b`.
Only the existing review copy uses this slice.

## The form's own words

`forms.literal_words` extracts only literal text outside validated blanks.
Advice, negatives/caveats, abstract-word, length and paragraph checks use that
text. Sentence checks use the frame with neutral blank positions. Night review
receives `literal_words` and judges its reading grade and sentence structure;
examples prove copying, binding and faithful row direction. Record/dictionary
words inside blanks are never judged for style, vocabulary, negatives, advice,
length or sentence marks. Complete sources remain exact. Existing grounded
middle-half tails, exact source provenance, pattern requirements, approval and
coverage gates remain.

`--recheck F-43 F-44 F-45 F-46` explicitly rechecks those retained rejected
forms under fresh numbers. The old payloads and reasons remain unchanged.
Only each named original's condition signature is exempted for its one
replacement. Approved catalog entries and all other retained forms still block
repeats; later variants remain `same form`. No failed writer trace is saved
when only a program recheck and a semantic review were attempted.

## Parts of the situation

Questions split at whole words but, yet, still, though, although and sentence
breaks. Each part is an exact input slice. The existing dictionary reader and
phrase matcher find its words. One shared SPARQL query asks for all asserted
forward paths; per-part evidence maps those reached records back to each
part's words. One reached word connects that part. Every part connected means
aligned; some means middle (`not_sure`); none means `dont_know`. A single part
keeps the existing all/some/none word rule.

The connected part's screen why prints each unconnected question part exactly
as missing record evidence. These visible why clauses can fill the existing
missing-half blank. No new blank, edge, dictionary meaning, source quote or
record is invented. A stopped or ambiguous dictionary part cannot supply hits.
Graph failure and a shared 300 ms query-budget miss retain the named count-rule
fallback. Dictionary reading milliseconds are recorded separately; the graph
query is counted once across parts and shares its budget with form ASK checks.

Historical replay changes only a hypothetical screen label and adds graph
part evidence. Every saved answer and every original screen source remains
unchanged. The policy version resubmits old screens for the new checks.

## Night practice and review

Up to 20 practice questions come from the night AI. At least half of valid new
questions must have two parts, rounding up for an odd batch. Code checks after
newness and dictionary-target validation, before any ask. An insufficient
batch is retained with its refusal reasons and fails closed. Questions are
never rewritten or removed to make a quota or label pass. Actual answered
practice labels are reported as aligned, middle and dont_know.

Normal graph ask uses the copy, surface `practice`, and no model. Practice stays
out of real history, real repeats, links and grade. Forms still need three
different questions across two bound words, including at least one real web or
cowboyai-iphone question. Counts use minimums or ranges; proposed/rejected forms
never enter day selection; only Adam's Yes can approve.

The review page keeps its existing style, real/practice fit counts, descending
fit order, up to three examples from different words, and Yes/No only. All graph
sources remain read only and derived links stay beside the copy.

## Run

```sh
NUCLEUS_FORMS_ONLY=0 .venv/bin/python -m nucleus.forms night \
  --store "$HOME/Library/Application Support/nucleus/forms-review/nucleus.sqlite3" \
  --bootstrap --recheck F-43 F-44 F-45 F-46

NUCLEUS_FORMS_ONLY=0 .venv/bin/python -m nucleus.serve --port 8767 \
  --store "$HOME/Library/Application Support/nucleus/forms-review/nucleus.sqlite3"
```

Defaults remain 8766/live and their existing answer route. Nothing is installed
in launchd, approved, merged or deployed to the live service. Full source
quotes, questions, RDF, traces and screenshots stay local; this repository is
public. Sanitized verification is saved beside this document.

## Verified result

One manual night pass: `cabffe5e-af43-4e20-883f-b0bb61cb832b`, 176 inputs / 168 usable.
**12 candidates: 10 proposed, 2 refused.** F-43 → F-47, F-44 → F-48 and
F-46 → F-50 pass. F-45 → F-49 still fails the literal word “correlates”, grade 7.
F-55 fits too few answers. Old rows and reasons stay exact. Twenty new questions
across twenty target words, all two-part: **3 aligned, 17 middle, 0 dont_know**.
Three night calls; zero per-question model calls.
All ten waiting forms require aligned; this pass proposed no new middle form.

**546 tests pass.** Actual graph/form queries **3.447–47.901 ms**, median
**8.3345 ms**, zero budget misses/fallbacks. Multipart dictionary reading is
separate: 565.311–811.772 ms, median 598.903 ms. These figures do not establish
full answers under 300 ms. Startup built 14,591 triples in **351.679 ms**.

All **5,095 original rows** and 13 source hashes/sizes/mtimes are unchanged.
Backup SHA-256 `78d8675752d9d61f5baf0aa434152a724e62b65e66f5a3f0ddf321e24205057a`;
backup and copy integrity both pass. Real history, links, grade, earlier forms
and approval receipts stay exact. Zero approvals; ten waiting forms and 48
retained refusals. The approved catalog is empty.

**Phone: http://100.111.154.126:8767/forms**. PID 8264 uses this worktree and
copy. Browser/HTTP verified all ten cards, descending fit counts, up to three
examples from different words, Yes/No only, and no editing fields or overflow.
Practice direct history is 404. Only review PID 90996 was stopped; live PID 1941
on 8766 is untouched. Private launcher/manifest/log, backup, full night trace
and screenshot stay beside the copy or in the task's local visualizations.
Nothing is approved, merged or installed. **Stop after slice 7b.**
