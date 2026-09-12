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
| CowboyAI styling for the coming nucleus app | `ios/Styling/Theme.swift`, `ios/Styling/Assets.xcassets` | copied, app not built |
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
6. Whether the iPhone app (`Cowboyai/authority-hub/ios`, talks to the old service on 8765) switches to this (8766). He said he will not say "switch" until the trade is clear; the trade he understood is in the compare table of 2026-09-12 (story and "pull the same thread" vs speed and never making things up).

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
