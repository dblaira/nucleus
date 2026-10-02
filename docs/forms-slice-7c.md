# Forms slice 7c

Base: `265eb880d9bff33de43a228f056cfa1acecd81df`. Branch:
`codex/forms-slice-7c`; worktree:
`/Users/adamblair/.codex/worktrees/nucleus-forms-slice-7c`.
Only the existing review copy runs this slice. Adam's complete request is
preserved on private companion branch `codex/forms-slice-7c-ledger`.

## A middle form from the question parts

Two new blanks copy the graph screen's exact question parts:
`{lined_up_part}` connects to accepted records; `{open_part}` connects to none.
They are Adam's question text, including punctuation, casing and spelling.
The literal frame is:

> “{lined_up_part}” lines up with {word}: “{meaning}”. “{open_part}” is still open.

This frame requires `answer=not_sure` and `graph_parts=true`. The named word
must belong to the connected part and its meaning must be printed on the same
screen. Both parts must be visibly printed, with matching graph evidence.
Only this exact frame receives the two-sentence / “still open” exception.
Single-part, count-fallback, dont_know and hidden graph data cannot supply
these blanks. Source words inside blanks are never judged for style, reading
grade, advice or negatives; the author's literal words remain checked.

Screens retain checked part metadata and visible proof text. SPARQL ASK checks
the same visible part conditions, inside an isolated temporary context, under
the existing shared 300 ms query budget. The graph's source triples are not
changed. Day use picks only an approved form with plain code and zero model
calls. Proposed and rejected forms are never chosen.

Historical screens are replayed with separate graph-part evidence. Original
answers, raw screen text, rows, meanings and why lines remain exact. An omitted
meaning can be recovered only from the whole exact quote already printed in
that saved screen. Current dictionary changes cannot replace a historical
quote. The replay policy is `graph-parts-text-v3`.

## One idea, one form

Forms with the same explicit answer and the same set of quoted middle words
are one idea, even when counts or wording differ. Graph-part middle frames
have their own idea key. Code measures all valid waiting and new forms against
the complete saved screen history, keeps the one fitting the most different
questions, and refuses the others as `same form`. Ties keep the earlier form.
Invalid or semantically refused candidates cannot displace a valid form.
Adam's Yes/No decisions and the approved catalog are protected.

F-48 is rejected in favor of F-54 (7 versus 8 questions); F-47 in favor of
F-56 (6 versus 8); F-50 in favor of F-57 (5 versus 7). Original payloads
remain intact. Only those three prior waiting statuses/reasons changed.

Coverage still requires three different questions across two bound dictionary
words, including one real web or cowboyai-iphone question. Repeated questions
count once. Counts use minimums/ranges. Practice stays out of real history,
links and grades. All graph files and language/record sources remain read only.

## The one manual night pass

Run `74f40812-763d-4ded-8746-f9bbe79ad5dc` completed with **210 inputs / 202
usable**. **Eight candidates: three proposed, five refused.**

| Form | Result | Different questions | Bound words | Real | Practice |
| --- | --- | ---: | ---: | ---: | ---: |
| F-59 | Semantic review refused “requires” as necessity wording | 15 | 9 | 10 | 5 |
| F-60 | Same semantic refusal | 11 | 6 | 7 | 4 |
| F-61 | Same semantic refusal | 9 | 4 | 7 | 2 |
| F-62 | Proposed | 6 | 2 | 6 | 0 |
| F-63 | Proposed | 8 | 4 | 6 | 2 |
| F-64 | fits too few answers: only one bound word | 5 | 1 | 5 | 0 |
| F-65 | needs one real question | 3 | 2 | 0 | 3 |
| F-66 | Proposed middle frame | 68 | 44 | 6 | 62 |

F-66's 62 practice fits include previous nights' saved practice. This night
generated 20 questions, asked and saved **17**, and refused three at the normal
dictionary gate before question creation. All 17 asked questions have two
parts: **0 aligned, 17 middle, 0 dont_know**. There are zero per-question model
calls. Nothing was silently reworded to get through the gate.

The real census uses all 120 web/cowboyai-iphone question rows, deduplicated
to **85 different questions**. The normal whole-question dictionary gate,
phrase reader and graph rule yield **33 aligned, 21 middle, 30 dont_know**,
with **one dictionary-stopped question** kept separate from the graph labels.
Grade jobs, CLI and practice are excluded. The census is saved in steps and
reused on the same-run writer continuation.

Across **all 77 different saved practice questions**, this run's current graph
replay labels are **15 aligned, 62 middle, 0 dont_know**. All 77 have replay
evidence, with zero replay refusals/budget misses. The 17 new middle questions
are included in those totals. Three dictionary-stopped proposals have no saved
question and remain separate. Earlier stored answers are never relabeled in
place; these totals describe the current graph replay.

The first writer request exceeded the provider's input limit before generation:
1,408,881 characters versus 1,048,576. Its complete failed model receipt, input
hashes and database checkpoint remain intact. Only the writer/review stage
was resumed under the same run ID, after verifying that practice had finished
and no forms had been produced. No second pass, new practice batch or extra
question was run.

Writer sampling now includes whole exact screens within a 750,000-character
base budget, spread across labels, real/practice and bound words. Full saved
history still determines coverage. The successful writer request was 750,146
characters including the graph suffix. Semantic review uses three bounded
packets (743,364 / 736,214 / 46,658 characters), reviewing every distinct fill
without clipping or dropping source text. Successful receipts stay independent
if a later packet fails. This pass has one failed writer attempt and five
successful night calls: practice writer, form writer and three semantic reviews.

## Verified copy and page

**617 tests pass** (14.38 seconds). New tests cover exact open-part copying,
source-word style exemptions, graph ASK/source isolation, the approved day
path with zero model calls, proposed-form exclusion, widest coverage per idea,
human Yes/No preservation, failed candidate ordering, unique real census,
whole-screen packet limits and complete semantic-review coverage/receipts.

Backup `slice-7c-before.sqlite3` SHA-256:
`5585c383eec655b962e3bc26b23a1bd1fba010f8837cc4a4f9520106dfd289e5`.
Backup and copy integrity pass. Of **5,444 original rows**, **5,441 stay exact**;
the other three retain every original field except the authorized duplicate
rejection status/reason/time. All **13 source hashes/sizes/mtimes** stay exact.
Real history, 1,400 links, 126 grades, earlier answers and approval receipts are
preserved. The approved catalog is unchanged. All 227 saved waiting-form fills
were refilled, with 753 exact source parts including 144 exact question-part
copies across 72 middle fills. All waiting forms meet the coverage floors.
An independent audit refilled all **357 measured matches** (new candidates and
prior-form rechecks), checked **999 exact source parts**, and confirmed every
part's connected/missing/reached-record metadata with forward traversal over
asserted source relations and validated copy links. It separately checked 56
new practice meaning quotes and 351 accepted record quotes word for word.

Saved practice graph/form-query totals are **3.982–40.705 ms**, median **15.061
ms**, zero budget misses/count fallbacks. The running review graph has **14,591
triples**, startup **336.672 ms**; startup is outside the per-answer query budget.
These are graph-query measurements, not full-answer latency.

**Phone: http://100.111.154.126:8767/forms**. Review PID **42349** uses this
worktree and copy. Its private launcher/manifest/log are `slice-7c-start.py`,
`slice-7c-server.json` and `slice-7c-server.log` beside the copy. Browser/HTTP
verified ten waiting cards, F-66 first, descending distinct-question counts,
up to three examples from different words, Yes/No only, no editing fields or
horizontal overflow. Practice direct-history URLs return 404. The page has
**10 waiting / 56 rejected / 0 approvals** at verification.

Only former review PID 8264 was stopped. Live PID 1941 on 8766 is unchanged;
no live database was opened and no request went to 8766. `NUCLEUS_FORMS_ONLY=0`.
No launchd job was installed/loaded, no approval was made, and nothing was
merged. Full private questions, quotes, RDF, model traces, checkpoints and the
rendered screenshot stay local because the nucleus repository is public.

See the sanitized [night summary](forms-slice-7c-night.json) and
[preservation proof](forms-slice-7c-proof.json). **Stop after slice 7c.**
