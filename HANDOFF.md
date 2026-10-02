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
