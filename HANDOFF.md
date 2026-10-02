# nucleus — handoff for any agent

Repo: git@github.com:dblaira/nucleus.git (private). Folder on Adam's Mac: `/Users/adamblair/Documents/nucleus`.
Read this file, then `README.md`, then `AGENTS.md` in the Cowboyai repo for the rules that govern all of Adam's work.

## What this is, in Adam's words

- "Cowboy AI is a pattern recognition service. It is a well-made extension of a person's memory and what's important to them. The selling point of this is that it doesn't go off and make things up. It works from what you have." (2026-09-11)
- "it's not going to make a decision because it never makes decisions. It just presents information ... we're not trying to answer questions. Trying to paint accurate pictures from the information given" (2026-09-11)
- "The two things are not enough. The middle must say what kind of connection exists." (his note, Narrative vs Relational)
- The three answers: "aligned and why" / "Not sure.  some correlation, but not enough for causation, more data may help." / "I don't know" there is nothing in your records that points to a conclusion. (2026-08-06, restated 2026-09-09)
- "No advice is given. No next steps are suggested." (2026-09-09)
- "My God that is fast." (2026-09-12, on a painted picture, 0.2 s)

## What is built and running (2026-09-12)

| piece | file | state |
| --- | --- | --- |
| the path of one question | `nucleus/ask.py` | running |
| his dictionary reads the question | `nucleus/dictionary.py` → `npm run brief-json` in adams-language | running |
| his 2–5 word phrases looked up by code | `nucleus/phrases.py` | running |
| links between his words and his records | `nucleus/links.py`, tables `links`, `searched_words` | 1,290 links, 134 of 177 words |
| the middle word on every link, from his list only | `nucleus/kinds.py` reads 43 words from `Main/🗯 Narrative vs 🔥 Relational.md`; `links.kind`; `links.schema.json`, `kinds.schema.json` | 98% of links; a row reads "A VISION depends on “…”" |
| thumbs on every row of an answer | `serve.py` `POST /thumb`, `GET /ask/<id>` → `rows`; `store.thumb` | 👍 keeps (green), 👎 never paints again (dark red) |
| the nucleus iPhone app | `ios/` (xcodegen `project.yml` → `nucleus.xcodeproj`; `NucleusApp`, `AskView`, `AskModel`, `API`, `Theme`, `Assets`) | built for the iOS 27 simulator and signed for Adam's iPhone (com.adamblair.nucleus, team 7FKUS5M5QS); talks to the Mac on 8766 over Tailscale; `-ask "..."` launch argument asks at once |
| painted picture, no model, when every word in the question has links | `links.paint` in `ask.py` step 3b | 0.2 s |
| same question again, answered from what was saved | `store.find_repeat` | 0.24 s |
| one open conversation on the Codex lane holding his files | `model.call_codex_conversation`, `~/Library/Application Support/nucleus/conversation.json` | 17–19 s per new question |
| the gate: only the three answers, quotes verbatim, records accepted in the ledger, one-sentence whys | `nucleus/gate.py` | every answer |
| the phone page | `nucleus/serve.py`, port 8766, launchd `com.nucleus.serve` | http://100.111.154.126:8766/ over Tailscale |
| nightly background pass over words without links | launchd `com.nucleus.links`, 02:00, log `~/Library/Logs/nucleus-links.log` | ran once 2026-09-11 evening |
| daily grade of questions.txt to Apple Notes | `nucleus/grade.py`, launchd `com.nucleus.grade`, 06:30 | running |
| two passes + judge (for a 32k-token model) | `nucleus/twopass.py` | measured, not default |
| doors | `nucleus/model.py`: codex (default), zai (`NUCLEUS_DOOR=zai`, his prepaid GLM credits, slower), anthropic/openai (keys absent) | |
| store | `~/Library/Application Support/nucleus/nucleus.sqlite3` — questions, steps, model_calls, answers, candidates, phrase_hits, grades, links, searched_words | nothing is ever deleted |

Tests: `.venv/bin/python -m pytest` — 48 pass.

## Measured, not guessed (all on "What is FLOW?", this Mac)

| road | seconds |
| --- | --- |
| painted from links | 0.20 |
| same question again | 0.24 |
| model, open conversation | 17–19 |
| model, files re-sent (first question after his records change) | 43 |
| two passes side by side + judge | 45 |
| fresh Codex conversation per question (old default) | 26–45 |
| Z.ai glm-5.3-flash | 64–86 |
| Z.ai glm-5.3 | never finished |
| old CowboyAI service (three cloud calls) | ~180 |

Rule from this: never tell Adam something will be faster until it is timed next to the current lane on his question (skill `measure-before-claiming-faster`).

## Adam's rulings still open (do not decide these for him)

1. The line at the top of a painted picture: today a count (`links.ALIGNED_RECORDS = 3`, every touched word has links and together ≥3 records → aligned, else not_sure). Labeled PROPOSAL in the code.
2. Whether a link found by the model may be painted before his thumb. Today: yes, thumb NULL paints; thumb 0 never paints.
3. (done 2026-09-12) The middle word on every link: Adam said "do it all" → the whole list from his note. Code refuses any other word.
4. (done 2026-09-12) Thumbs on the page.
5. Expected verdict for the hopeful-project question in `questions.txt`; 48 graph records with no ledger decision (`prompt.not_accepted_block`).
6. The old CowboyAI iPhone app still talks to the old service on 8765. The new nucleus app (ios/) talks to 8766. Adam, 2026-09-12: the nucleus app "will eventually take over the name Cowboyai". He said he will not say "switch" until the trade is clear; the trade he understood is in the compare table of 2026-09-12 (story and "pull the same thread" vs speed and never making things up).

7. (2026-09-14) The name is Cowboy AI, and on screen it is the hat. Claude had put letters ("nucleus", then
   "Cowboy AI") in the hero. Adam: "It's the name that we've always had. You're the one that changed it." and "You
   know what cowboy I looked like before? The hat icon". The hero now holds the CowboyAI app's tan hat, no letters
   (skill `the-name-is-cowboy-ai`). On 2026-09-21 Adam said: "Why is cowboyai on the iphone named nucleaus? Change it back to Cowboyai."
   The iOS display name and bundle name are now `Cowboyai`. Keep `com.adamblair.nucleus` as the bundle identifier
   so updates preserve the existing app's data. The engine and internal project name remain nucleus.

## What Adam said about the product, 2026-09-12, in order

- "the rows of a users words reflected back to them are fine, but there needs to be some explanation.  This is a glorified search look up.  That isn't a product."
- "The three answers aren't enough.  A label named 'aligned'? That is a glorified search retrieval."
- "I want the styling only from Cowboyai to be ported over to this project repo. I want this so you can build an ios app version of "nucleaus", that will eventually take over the name Cowboyai."
- "I am not using your words." (the middle words are his, from his note, never Claude's)
- His run idea, logged in Cowboyai `docs/product/2026-09-12-phrases-and-pre-answers-idea.md`: phrases (built), match before any call (built), onboarding by dictation (not built), pre-answers (links are the built form), thumbs (not built), words on screen while waiting (half built).

## How to work with him (the rules that bit tonight)

- One thing per reply, his words. He reads on a phone. Articulate-leadership format, four chapters, takeaway in the heading.
- A comparison is a table whose rows are his own sentences, quoted and dated (skill `compare-in-his-sentences`).
- A yes-or-no question gets yes or no first (skill `yes-or-no-first`).
- When he says he does not understand: one real example from his data, three lines (skill `one-example-not-a-theory`).
- Never say the model decides. It paints (skill `it-paints-it-does-not-decide`).
- A correction gets a fix, proof, and a new rule in `~/.claude/skills/`. Never "you're right".
- Nothing of his is deleted without his word. Constraints on answers come from his accepted graph or his words; anything else is a proposal, flagged at the top.

## Where things are

- His files (the nucleus): `Main/Ontology/accepted/accepted-graph.ttl`, `decision-ledger.json`, `Main/Ontology/shapes/connection-shape.ttl`, `upper/bfo-bridge.ttl`, `adams-language/meanings.txt`, `routes.txt`.
- His product notes: Apple Notes ("Cowboyai.", "Marketing Cowboyai", "The Mythic Layer"), `Main/🗯 Narrative vs 🔥 Relational.md`, Cowboyai `docs/product/*.md`.
- Remote Control to this Mac: tmux session `cowboy` in `~/Documents/Cowboyai` (`tmux attach -t cowboy`).
- Apple's free server model: Small Business Program enrollment submitted 2026-09-10; permission form opens after approval; fmtest/ holds the Swift probe.

## Forms slice 1 — October 1, 2026 Pacific

Adam's request in Codex:

> "Read HANDOFF.md, README.md, then FORMS-PLAN.md in /Users/adamblair/Documents/nucleus. Build slice 1, then stop at each slice's kill switch."

The supplied plan is dated October 2. Slice 1 is built on `codex/forms-slice-1`
from `c80d471ebb394821e680c35cb98b8e9227d0c2ab` in
`/Users/adamblair/.codex/worktrees/nucleus-forms-slice-1`.
Read [docs/forms-slice-1.md](docs/forms-slice-1.md) for the format, blank
bindings, storage API, source-boundary checks, and verification. The exact
supplied plan is preserved in [FORMS-PLAN.md](FORMS-PLAN.md).

`nucleus/forms.py` loads/checks/fills; `forms.txt` is empty; proposal storage is
additive in `Store`. Baseline 58 tests and 74 new cases pass (132 total).
The F-7 example was filled against the running service's real saved FLOW rows
in an isolated test, with every output part traced. No product form was
approved. No live schema, service, answer path, or phone change was made.

**Stopped after slice 1. The kill-switch source check passes. Do not infer
authorization to proceed from this handoff. Slice 2 has not been started.**

## Forms slice 2 — October 1, 2026 Pacific

Adam's next request in the same Codex chat:

> Read FORMS-PLAN.md in /Users/adamblair/Documents/nucleus. Build slice 2 only, starting from commit 9695d13 on codex/forms-slice-1, on a new branch codex/forms-slice-2. Keep NUCLEUS_FORMS_ONLY off. Acceptance: a painted question with an approved form has zero rows in model_calls and an explanation with provider "form"; with zero approved forms, everything behaves exactly as today. All tests pass. Push, do not merge to main, update HANDOFF.md, and stop before slice 3.

Slice 2 is built on `codex/forms-slice-2`, based exactly on
`9695d13a7731bf489576c76f2df365700f2a3abb`, in
`/Users/adamblair/.codex/worktrees/nucleus-forms-slice-2`.
It selects approved forms in the painted branch (most condition keys, then
lowest numeric number), saves provider `form`/model `F-N` without an
explanation thread, records exact painted snapshots in `form_misses`, and
keeps the previous live paragraph path when none fit. Form paragraphs are
saved before publishing their answers; the existing page shows the number
and the chosen-form trace. `NUCLEUS_FORMS_ONLY` remains unset/off.

**154 tests pass**, including the previous 132. A separate probe against
isolated copies of real saved data produced zero `model_calls` rows with an
approved fixture and provider `form`. With the empty product file, a direct
comparison to slice 1 matched the answer, rows, trace, and controlled fallback
paragraph. The rendered form number and trace were inspected. Read
[docs/forms-slice-2.md](docs/forms-slice-2.md) and its linked proof for details.

`forms.txt` remains empty. Nothing was merged into main, deployed, or migrated
in the live database. Existing dirty/untracked files remain in the original
checkout. The code and handoff are on the pushed slice 2 branch.

**Stopped before slice 3. No night pass, schedule, or approval page was built.**

## Forms slice 3 — October 1, 2026 Pacific

Adam's next request in the same Codex chat:

> Read FORMS-PLAN.md in /Users/adamblair/Documents/nucleus. Build slice 3 only, starting from commit 5aded94 on codex/forms-slice-2, on a new branch codex/forms-slice-3. Run the first night pass by hand against a copy of ~/Library/Application Support/nucleus/nucleus.sqlite3, never the live file. Write the com.nucleus.forms launchd plist into the repo but do not install or load it. Keep NUCLEUS_FORMS_ONLY off. Report how many forms were proposed, how many the checks refused and why, and paste three filled examples. All tests pass. Push, do not merge to main, update HANDOFF.md, and stop before slice 4.

Slice 3 is built on `codex/forms-slice-3`, based exactly on
`5aded943ab80b64c5ce049452aa4320825d7bdb6`, in
`/Users/adamblair/.codex/worktrees/nucleus-forms-slice-3`.
The new night command reads misses, thumbed-down explanations, and prior forms;
calls the existing model door once; checks and previews up to 12 proposals;
and retains raw replies, refusals, filled examples, and source snapshots.
`forms.txt` is still empty and `NUCLEUS_FORMS_ONLY` is still off.

The first manual pass ran on
`~/Library/Application Support/nucleus/forms-review/nucleus.sqlite3`, made by
SQLite backup from the live database, with an untouched original backup beside
it. **12 forms were proposed; 0 were refused; 31 filled examples were saved.**
Of 120 historical painted answers, 106 were reconstructable; 14 lack an
unambiguous saved middle word and were kept as skipped inputs with reasons.
These are separate from the zero refused forms. All 12 remain proposed.
The pass used Codex `gpt-5.6-sol`, run ID
`4505483d-8604-4a8e-9c2c-73458bb615d8`.

**184 tests pass.** All original rows in the copied tables are preserved;
the only addition to those original tables is one night model call. Both the
backup and working copy pass integrity checks, and the original backup hash
is unchanged. Every saved example was refilled and compared exactly.
See [docs/forms-slice-3.md](docs/forms-slice-3.md),
[the first-run report](docs/forms-slice-3-first-night.json), and
[the preservation proof](docs/forms-slice-3-proof.json).

The 03:00 `com.nucleus.forms` plist is in `launchd/` only, explicitly targeting
the review copy; it is **not installed or loaded**. Nothing was merged to main,
deployed, or migrated in the live database. The original dirty checkout is
preserved. The exact request is appended on the companion Cowboyai branch
`codex/forms-slice-3-ledger`.

**Stopped before slice 4. No approval page or approval action was built.**

## Forms slice 3b — October 1, 2026 Pacific

Adam's next request in the same Codex chat:

> Build slice 3b on a new branch codex/forms-slice-3b from 7249b63. Change the night pass so forms explain what a pattern of rows means, not how many rows there are. Refuse any form whose sentence only restates a count or a middle word. Each form must fire on a pattern: two or more middle words together; a middle word that pushes against another, such as rejects, contradicts, prevents, inhibits, constrains, or limits; or a word with missing links. Keep every existing rule: blanks only from the screen, no advice, nothing used without Adam's yes. Rerun on the copy, never the live file. Report proposed and refused with reasons, and paste five filled examples. Push, do not merge, update HANDOFF.md, and stop before slice 4.

Slice 3b is built on `codex/forms-slice-3b`, from exactly
`7249b63abc78e5df9277aa797fd59681ec3f5b84`, in
`/Users/adamblair/.codex/worktrees/nucleus-forms-slice-3b`.
The night pass now requires a combination of middle words, a stated opposing
middle word, or missing links. A deterministic restatement check and a separate
night-time meaning review refuse row inventories and unsupported implications.
The day path and screen-only filler are unchanged; no model runs there for forms.

**Rerun: 11 new proposals, 1 new refusal.** F-19 was refused because it treated
two kinds as referring to the same thing, although the rows can point to
different records. **All 12 earlier proposals were retained as rejected:**
11 lack a qualifying pattern, and one only lists middle words. Original
payloads, examples, and first-run traces are preserved. None is approved.

The existing review copy at
`~/Library/Application Support/nucleus/forms-review/nucleus.sqlite3` was backed
up to `slice-3b-before.sqlite3` before the rerun. The live database was not
opened. Run `bf075602-fcb5-4c95-8ce7-1463697ffacd` used two existing-door Codex
`gpt-5.6-sol` calls (writer and reviewer), revisiting the same 120 painted
answers under `patterns-v1`: 106 usable, 14 skipped for unrecoverable middle
words. It saved 17 proposed examples and one refused example. All 18 refill
exactly. The new policy revisits each old input once without erasing history.

**226 tests pass.** Copy and backup integrity checks pass; the backup hash,
original answers/links/explanations, earlier calls/runs/results, and old
proposal payloads are preserved. The only existing fields changed are the
twelve prior proposals' status, refusal reason, and decision time.
Read [docs/forms-slice-3b.md](docs/forms-slice-3b.md),
[the complete report](docs/forms-slice-3b-night.json), and
[the proof with five filled examples](docs/forms-slice-3b-proof.json).

`forms.txt` is still empty, `NUCLEUS_FORMS_ONLY` is off, and the unchanged
launchd plist is not installed or loaded. No service/phone deployment or
merge to main was performed. The exact request is appended on companion
branch `codex/forms-slice-3b-ledger` in Cowboyai.

**Stopped before slice 4. No approval page or approval action was built.**

## Forms slice 3c — October 2, 2026 Pacific

Adam's next request in the same Codex chat:

> Build slice 3c on a new branch codex/forms-slice-3c from 25782d8. Add one blank: the exact quote of the record a row points to, for a named middle word, word for word from the screen. A form joins two or more rows into one plain sentence, for example: "{word} depends on {quote:depends on} and rejects {quote:rejects}." Refuse any form that contains a negative or a caveat (not, does not, cannot, no evidence), or the words establish, claim, prerequisite, containment, necessity, or coexistence. Write at a fifth-grade reading level. Keep every existing rule. Mark all 3b forms rejected. Rerun on the copy, never the live file, and paste five filled examples. Push, do not merge, update HANDOFF.md, and stop before slice 4.

Slice 3c is built on `codex/forms-slice-3c`, based exactly on
`25782d8017a6d9c5ee80a9b75c0d6d4c1b033c4e`, in
`/Users/adamblair/.codex/worktrees/nucleus-forms-slice-3c`.
The new `{quote:middle word}` blank copies a complete displayed quote from a
row for that same word and named middle word, preserving its exact text and
source-row identity. New proposals join two or more distinct row quotes in
one plain sentence. Negative/caveat and blocked-word vetoes apply to templates,
source quotes, and filled text. The night reviewer now checks fifth-grade
reading level and one sentence across every distinct fill, retaining at most
three examples per proposal. Pattern, advice, provenance, and approval rules
remain in force.

**Copy rerun: 11 candidates, 3 new proposals, 8 refusals.** Seven were rated
above fifth grade (five grade 6, two grade 7); one had no matching saved screen
for its required 40 rows and 4 words. **All twelve 3b forms are now rejected:**
eleven pending forms were refused for “not” or “neither,” and already-rejected
F-19 remains unchanged. Old payloads, examples, and traces are preserved.
No form is approved. The five reported examples consist of the three proposed
examples and two explicitly rejected examples; exact source text is retained.

The existing review copy was backed up to `slice-3c-before.sqlite3` before the
pass. The live database was never opened. Run
`1c9f17af-361a-4c18-a945-4fd6ad64c9f0` used two existing-door Codex
`gpt-5.6-sol` calls, revisiting 120 historical inputs under `quotes-v1`:
106 usable and 14 retained as skipped for unrecoverable printed middle words.

**273 tests pass.** All ten saved examples refill exactly, and twenty quote
parts match their saved screen rows word for word. The painted-answer test
proves provider `form`, zero model-call rows, and exact quotes present on its
returned screen. Existing zero-approved fallback tests pass. Copy and backup
integrity checks pass; the backup hash and earlier records are preserved.
Read [docs/forms-slice-3c.md](docs/forms-slice-3c.md),
[the night summary](docs/forms-slice-3c-night.json), and
[the proof summary](docs/forms-slice-3c-proof.json). This repository is public;
full screen records and five filled examples remain in the local review folder's
`slice-3c-night.json` and `slice-3c-proof.json`, with the examples also pasted in
the Codex reply. The committed summaries contain result metadata and text hashes.

`forms.txt` remains empty. `NUCLEUS_FORMS_ONLY` stays off. The launchd plist
remains uninstalled and unloaded. No merge, deployment, or live migration was
performed. The original dirty checkout is preserved. The exact instruction is
appended on companion Cowboyai branch `codex/forms-slice-3c-ledger`.

**Stopped before slice 4. No approval page or approval action was built.**

## Forms slice 4 — October 2, 2026 Pacific

Adam's next request in the same Codex chat:

> Build slice 4 only, on a new branch codex/forms-slice-4 from 04fe394, in a new worktree. Add a /forms page to nucleus/serve.py. Let the port and database path be set when the server starts; the defaults stay 8766 and the live nucleus.sqlite3, so the live service is unchanged. Run the review copy from the slice 4 worktree on port 8767 against forms-review/nucleus.sqlite3. Never touch the live file or the service already running on 8766. The page shows each proposed form: its number, its fires-when in plain words, and its filled examples, biggest first, in the same page style as today. Two buttons only, no editing. Yes writes the form into forms.txt on this branch as approved; no marks it rejected and keeps it. Keep NUCLEUS_FORMS_ONLY off. All tests pass, plus new tests for yes, no, and "a proposed form is never chosen". Push, do not merge to main, update HANDOFF.md, and report the phone link to port 8767.

Slice 4 is built on `codex/forms-slice-4`, from exactly
`04fe394fffbb9354212cf6cdb6f123d22735a2c8`, in the new worktree
`/Users/adamblair/.codex/worktrees/nucleus-forms-slice-4`.
`/forms` reuses the existing page's colors, hat, photo, and type. Each proposed
form shows its number, large filled examples, plain fires-when conditions, and
only Yes / No. Yes atomically appends an approved block to this worktree's
`forms.txt`; No retains the proposal and examples and marks it rejected.
Nothing becomes approved just by loading the page.

The server now accepts `--port` and `--store`; defaults remain port 8766 and
`~/Library/Application Support/nucleus/nucleus.sqlite3`. The review server is
running from this worktree on **8767**, against the existing review copy at
`~/Library/Application Support/nucleus/forms-review/nucleus.sqlite3`.
**Phone link: http://100.111.154.126:8767/forms**. The existing service on
8766 was never restarted or queried, and the live database was never opened.
The review server's PID and command are saved locally in `slice-4-server.json`;
logs are in `slice-4-server.log` beside the review copy. It is a manual process,
not a new launchd job.

**307 tests pass**, including Yes, No, proposed-never-chosen, repeat/stale
choices, concurrent choices, failed file writes, interrupted approval receipts,
server isolation, and the unchanged default startup / original home page.
The browser exercised both buttons on separate synthetic test forms and read
back the resulting file and database. The real review page was then inspected
at a phone-sized browser width, through the same phone URL. All three current
proposals (F-25, F-26, F-31) remain proposed. `forms.txt` is still empty.

The copy was backed up to `slice-4-before.sqlite3` before startup. Every row in
all 15 earlier tables is unchanged; the only schema addition is an empty
`form_approvals` receipt table. Both integrity checks pass, and the backup hash
is unchanged. No night pass or model call ran on the copy. Raw proposal payloads
retain their original status; Store's effective status combines the proposal
with its approval receipt. **The day picker still reads only `forms.txt`.**
See [docs/forms-slice-4.md](docs/forms-slice-4.md) and
[the preservation proof](docs/forms-slice-4-proof.json). Screenshots and exact
screen records remain local because this repository is public.

`NUCLEUS_FORMS_ONLY` remains off. No launchd job was installed or loaded, no
phone app was changed, and nothing was merged to main. The original dirty
checkout is preserved. The exact request is appended on companion Cowboyai
branch `codex/forms-slice-4-ledger`.

**Slice 4 complete. Stopped here; real forms wait for Adam's Yes or No.**

## Forms slice 4b — October 2, 2026 Pacific

Adam's next request in the same Codex chat:

> Build slice 4b on a new branch codex/forms-slice-4b from 3dba8c5. Problem: F-25, F-26 and F-31 demand an exact screen — record_count 15 or 12 and word_count 1 or 3 are exact matches in _count_matches — so each fits one past answer and stops fitting when that word gets one more link. Fix the night pass: counts in fires-when are written only as minimums or ranges, never exact numbers. Every proposed form must fit at least 3 past painted answers in the copy database, from at least 2 different words, or it is refused with the reason "fits too few answers". Re-propose these three with widened conditions under new numbers; mark the old three rejected with the reason "fit one screen only"; a widened form is not a repeat of its narrow original. On the /forms page, show under each form the number of past answers it fits, biggest first, with up to 3 filled examples from different words. Keep everything else from slice 4: copy database only, port 8767, live service on 8766 untouched, NUCLEUS_FORMS_ONLY off, nothing approved, nothing merged. All tests pass, plus tests for "exact counts refused" and "too few answers refused". Push, update HANDOFF.md, restart the 8767 page from the new worktree, and report the phone link.

Slice 4b is built on `codex/forms-slice-4b`, from exactly
`3dba8c53d30d02acceeb6ba3bf5fe25374509eb6`, in the new worktree
`/Users/adamblair/.codex/worktrees/nucleus-forms-slice-4b`.
The night writer schema, prompt, and deterministic check now allow only minimums
or nonzero-width ranges for count conditions. Exact integers, equal endpoints,
and maximum-only bounds cannot become new proposed forms. The day filler and
its existing count semantics remain unchanged.

Every candidate is checked against the whole saved painted history, including
answers consumed by prior night passes. Each answered question ID counts once;
the two-word requirement counts the word actually bound into the sentence,
not every word mentioned on its screen. Below 3 answers or 2 bound words gives
exactly `fits too few answers`. The new additive `form_night_coverage` table
retains all matching snapshots, fills, and source parts. The semantic reviewer
still checks every distinct filled sentence. The page shows the fit count,
sorts largest first, and keeps up to 3 examples for different words.

The requested re-proposals ran once on the existing copy with
`--bootstrap --widen F-25 F-26 F-31`, run
`3bd5aeff-5019-425b-8196-771924c735d4`. Exact counts became minimums; sentences
and other conditions were kept. Widened conditions have a different repeat
signature. **Three new candidates, zero proposed, three refused:**

| Old | New | Past answers fitted | Bound words | Result |
| --- | --- | ---: | ---: | --- |
| F-25 | F-36 | 32 | 1 (FLOW) | fits too few answers |
| F-26 | F-37 | 32 | 1 (FLOW) | fits too few answers |
| F-31 | F-38 | 1 | 1 (PULLED) | fits too few answers |

All old three are retained as rejected with `fit one screen only`, keeping
their original payloads and examples. The copy contains repeated FLOW answers;
wider counts do not make their two required kinds fill for a second word.
This mechanical re-proposal used no writer model; none reached the semantic
reviewer because the coverage gate refused them. No model call was added.
There are now **38 rejected, 0 proposed, 0 approved** real forms in the copy.
`forms.txt` remains empty. The actual page correctly shows an empty queue.

**332 tests pass**, including exact-count refusal, too-few-answers refusal,
coverage across consumed history, answer-ID deduplication, bound-word diversity,
repeat signatures, and largest-first review. Earlier passing cases now supply
actual painted history meeting the new floor; no gate is mocked away. A
baseline HTTP wrong-content-type test exposed a connection reset from an
unread body; the handler now consumes its bounded body before returning 400.
Browser verification used separate synthetic fixtures to show 5-fit before
3-fit, different-word examples, and working Yes/No; its file/database were read
back. The real phone URL was then verified to return HTTP 200 and show the
empty queue. No physical phone was operated.

The copy was backed up to `slice-4b-before.sqlite3` before the pass. The backup
hash and both integrity checks pass; all original rows remain. Only the old
three proposal decision fields changed, alongside the new run/results/rechecks
and coverage table. All 65 saved matches refill exactly. Read
[docs/forms-slice-4b.md](docs/forms-slice-4b.md) and
[the proof summary](docs/forms-slice-4b-proof.json). Full traces and screenshots
remain local because this repository is public.

**Phone link: http://100.111.154.126:8767/forms**. Review PID 58000 runs the new
worktree against the same copy; its manifest/log are `slice-4b-server.json` and
`slice-4b-server.log` beside the copy. Only the old review PID 51372 was stopped.
Live PID 1941 on 8766 is unchanged; no request or database open went to it.
`NUCLEUS_FORMS_ONLY` stays off. No launchd change, approval, or merge to main.
The exact request is appended on companion Cowboyai branch
`codex/forms-slice-4b-ledger`. **Stopped after slice 4b.**

## Forms slice 5 — October 2, 2026 Pacific

Adam requested forms for “the middle option (of the three choices it has now)
when part of the situation is aligned but not all.” Build from `c660fb1` on
`codex/forms-slice-5`, in a new worktree, keep the live file/service untouched,
forms-only off, no approval or merge, and run the night pass once by hand.
The exact full instruction is preserved in the private Cowboyai ledger.

Implemented on `/Users/adamblair/.codex/worktrees/nucleus-forms-slice-5`, from
`c660fb15776fcdebaa28401c1c68a854c09367ea`. Middle forms require `not_sure`, copy
exact visible word/record quotes and name only an explicit missing why, a
printed word with no links, or a genuinely absent printed middle word.
Approved middle forms replace only the fixed opening and save their explanation
with provider `form`; daytime selection is plain code. Zero-approved fallback
and the original answer generation path remain intact.

Night coverage now counts different normalized questions, once for both question
and bound-word totals. The minimum is three questions across two words. Every
separate filled text remains in review. Exact count conditions are refused.
The page shows different-question fits, biggest first, with up to three examples
for different questions and words. New model-screen misses reach later night
passes. The default night pass supports both existing and middle forms;
`--middle-only` focuses the manual pass on this slice.

**396 tests pass. One hand-run completed: 0 proposed, 1 refused.** Run
`4914afb5-f557-4ea5-884f-734e61a40890`, 62 inputs / 44 usable, proposed candidate
F-39 but the meaning reviewer refused its unrelated quote pairing. The full
refused form and trace are retained. The filler was corrected to require an
explicit positive screen half and two exact shared content words for model
quote pairs; unrelated quotes, names and possessive suffixes do not qualify.
Read-only corrected previews fit three questions across three words. There was
no second pass because Adam specified “once by hand”. **The real queue is empty;
new proposals require authorization for another pass.**

Backup `slice-5-before.sqlite3` and both integrity checks pass. All original rows
remain exact; only two night model calls and the new run/candidate/results/
coverage were added. There are 39 rejected forms, zero proposed and zero
approved. `forms.txt` stays empty. Full records remain local.

**Phone link: http://100.111.154.126:8767/forms**. The new worktree's review server
uses only the existing copy; its manifest/log are `slice-5-server.json` and
`slice-5-server.log` beside the database. Browser verification shows the real
empty queue and HTTP 200. Live PID 1941 on 8766 is untouched; no database open or
request went to it. `NUCLEUS_FORMS_ONLY` remains off, nothing is approved,
installed in launchd or merged. Companion branch `codex/forms-slice-5-ledger`
preserves the exact instruction. See [slice details](docs/forms-slice-5.md),
[night summary](docs/forms-slice-5-night.json) and
[preservation proof](docs/forms-slice-5-proof.json).

**Implementation complete; stopped at the one-pass boundary.**

## Forms slice 5 — authorized additional pass

Adam then replied, exactly: “run one additional copy”. Source: this Codex chat,
October 2, 2026 Pacific. The exact authorization is appended to the private
Cowboyai ledger on `codex/forms-slice-5-ledger`.

One additional pass ran on the existing review copy, after a fresh backup to
`slice-5-additional-before.sqlite3`. The corrected pairing policy is explicitly
versioned `middle-question-v2`, so previously consumed source screens are
revisited under the revised eligibility without altering old runs or inputs.
The only code change for this continuation is that policy version and its test
expectation. **396 tests pass.**

Run `477f4561-6997-4ee5-885c-4c1c164e19c8` completed with 62 inputs / 44 usable.
**Three new candidates, zero proposed, three refused:** F-40, F-41 and F-42 each
fit **one different question and one bound word**, below the three-question,
two-word floor. All have reason `fits too few answers`. Their conditions require
2–3 rows and 4–5 words; only one past question meets those bounds and safely
fills. No candidate reached the separate semantic reviewer. One night writer
model call was added; no daytime question or answer was made.

The copy now has **42 rejected, 0 proposed, 0 approved** forms; `forms.txt` remains
empty. F-39 and all earlier rejections, examples and traces remain unchanged.
Both integrity checks pass, and every original row in the pre-run backup is
preserved exactly. No third pass was made.

The review page was restarted from the slice-5 worktree on **8767**, against the
copy only. Phone link: **http://100.111.154.126:8767/forms**. The actual page
correctly shows “No forms waiting for your yes.” Live PID 1941 on 8766 remains
untouched; no request or database open went to it. `NUCLEUS_FORMS_ONLY` is off.
Nothing is approved or merged.

See [additional night summary](docs/forms-slice-5-additional-night.json) and
[preservation proof](docs/forms-slice-5-additional-proof.json). Full questions,
source quotes, traces and screenshots remain local because this repository is
public. **Stopped after the one authorized additional pass.**
