# nucleus — handoff for any agent

Repo: git@github.com:dblaira/nucleus.git (private). Folder on Adam's Mac: `/Users/adamblair/Documents/nucleus`.
Read this file, then `README.md`, then `AGENTS.md` in the Cowboyai repo for the rules that govern all of Adam's work.

## What this is, in Adam's words

- "Cowboy AI is a pattern recognition service. It is a well-made extension of a person's memory and what's important to them. The selling point of this is that it doesn't go off and make things up. It works from what you have." (2026-09-11)
- "it's not going to make a decision because it never makes decisions. It just presents information ... we're not trying to answer questions. Trying to paint accurate pictures from the information given" (2026-09-11)
- "The two things are not enough. The middle must say what kind of connection exists." (his note, Narrative vs Relational)
- The three answers: "aligned and why" / "There is some relationship, but not enough to justify causation." / "I don't know" there is nothing in your records that points to a conclusion. The middle one read "Not sure.  some correlation, but not enough for causation, more data may help." until 2026-10-02, when he reworded it and said: "I will need to define the logic for the middle response." and "The middle response requires a back and forth exchange to answer questions (or options) it will return so a better causation case can be made." The exchange is not built. Do not define its logic for him. (2026-08-06, restated 2026-09-09)
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

Tests: `.venv/bin/python -m pytest` — 108 pass.

## 2026-10-07 — Adam's own form for the middle answer (governs; replaces everything Claude proposed today)

Adam wrote it in the artifact "The Middle Answer" (https://claude.ai/artifact/MWFiR9Je6jCibrhcsMNK12), saved
2026-10-07 11:19 am, and said: "My middle answer adjustments are completed." Verbatim, field by field:

- QUESTION: What are reasons I avoid going to the doctor?
- EXPLANATION: "Some relationships, but not enough to justify is an opportunity for growth.  This is a chance to
  transform potential into a new skill that can compound into something more and more valuable."
- ANSWER: "There is some relationship, but not enough to justify causation."
- Section "Reasons": "This should contain quotes of mine that have some relationship.  Not a bland fucking explanation
  of nothing."
- Section "Suggestions to move the relationships into a more predictable category": "Going the doctor is not something
  you have a history of, so it is difficult to use your aptitude for discernment. One suggestion is to take this
  context and ask AI to relate it to the your predictable patterns and find simple steps to gather data that leads to
  better discernment."
- Section "Belief": "Speed. Discernment. Curiosity.  Confidence.  These are important to you.  Do any of them apply more
  or less when moving this issue further towards a predictable outcome?"
- Last section, his question to himself: "What would you like AI to revisit? Anything come to mind?" — it replaces the
  September 9 sentence he chose that morning. The live engine still ends middle answers with the September 9
  sentence (`gate.MIDDLE_ASKS`, commit ac73004) until this form is built.

Built the same day, commit a4dcc08, live engine restarted 2026-10-07 ~12:00 pm. Adam: "yeah, that's fine. But I will not
be there to type this shit every time.  What are we going to do to automate this?" So nothing is typed per question:
`nucleus/middle.py` holds his fixed words (Explanation, Answer, Belief, last question = `gate.MIDDLE_ASKS`); Reasons is
filled by code with his own quotes the answer reached (at most 5, PROPOSAL); Suggestions is filled by the night run's
options and appears once that run has made them. GET /ask/<id> sends `middle`; his app (ios, same commit) draws it.
Real problem found while testing: the night run's advice check (`explain.ADVICE`) refused all three options for one
answer because one sentence said "when you consider going to the doctor". His Suggestions section and his rule "No
advice is given.  No next steps are suggested." need his ruling; the check is unchanged.
The readout branch `claude/middle-readout` (Claude's labels) is superseded; kept, not merged.

## 2026-10-07 — the middle answer asks in his words of September 9

Asked which of his own sentences leads the middle answer, Adam, 2026-10-07: "Perfect. Use Sept 9". The sentence is the
end of his own 2026-09-09 definition of the middle answer: "If you would like to add go deeper in one area by sharing
more of what you believe I could re-access with more input." It is `gate.MIDDLE_ASKS`; `gate.compose` puts it, as its
own block, right after the first line of every new middle answer. In his app it reads at the end of YOUR ANSWER, in the
answer's own type, after the meaning paragraph. No screen code changed. Saved answers are not rewritten.

## 2026-10-03 — what follows the middle answer: more information, logged, the night run, three options

Adam, 2026-10-03: "The response, "There is some relationship, but not enough to justify causation," will be followed by
requesting more information, which will be logged and then analyzed by the LLM during the night run.  During the
overnight run, all middle responses will use AI to generate options that might move the situation further down the
spectrum from correlation to causation.   Three options are a good starting point.  I will set the criteria for the
three options later, but they will all align in attitude and speed. But they offer different ways to broaden my
perspective and create better opportunities for causation. What this means is that thinking bigger is also thinking
broader because it brings in other relationships that are probably affecting the predictability of a situation."

| piece | file | state |
| --- | --- | --- |
| the request for more information, under the middle answer | `ios/nucleus/LiveAnswerView.swift` `moreInformation`, the page in `serve.py` | a field headed MORE INFORMATION and a Log button; what he gave shows above it |
| the log | `store.more_information`, `POST /more` in `serve.py`, table `more_information` | only after a middle answer; nothing is ever deleted |
| the night run | `nucleus/night.py`, launchd `com.nucleus.night`, 02:20, log `~/Library/Logs/nucleus-night.log` | one model call for each middle answer of his with no options yet, or with more information logged since its last options |
| three options | table `options`, `night.check` | each brings in one accepted record or one dictionary word of his that the answer did not use, shown in his own words, then one sentence for what it may be doing and one for the information that would show it. Code refuses anything else. |
| where he sees them | `night.with_options`, `GET /ask/<id>` | under the middle answer in the box his app already draws, named in his word "possibility". The saved answer is not rewritten. |

The criteria for the three options are his to set: "I will set the criteria for the three options later". The
contract handed to the model is his sentences above and the engine's standing rules; nothing else was decided.
Whose middle answers the night run works on is a PROPOSAL in `night.py`: his own entries, not the daily grade,
from 2026-10-02 on.

## 2026-10-02 — the meaning in normal sentences, with no model, judged by his knowledge graph and dictionary

Adam, 2026-10-02: "after adding the ontology and the knowledge graph to the dictionary and everything I have, I should
have more meaning that doesn't require a fucking large language model to help me with, and and it's just the output is
put in a reasonable state to where I can read it like a normal fucking sentence or statement or narrative". Then, on an
entry that held none of his dictionary words ("What are reasons I would avoid going to the doctor?"): "It did not use the
ontology and knowledge graph. We should be in Cowboyai. Not Nucleaus. Add my ontology and knowledge graph, and make sure
my entry is judged according the knowledge graph and dictionary."

| piece | file | state |
| --- | --- | --- |
| the paragraph under the answer, built by code from his own sentences, only the person changed (I → you, Adam → you) | `nucleus/narrative.py`, `nucleus/person.py` | on in the live service: `NUCLEUS_NARRATIVE=1` in `launchd/com.nucleus.serve.plist`; milliseconds; the model is never asked while it is on |
| an entry with none of his dictionary words: his ontology says which life domain it sits in, his knowledge graph says what it holds there | `Narrator.domains_named`, `Narrator.domain_road` | "You said doctor. In English that is “a licensed medical practitioner”. Your ontology files that under Health: …" then the accepted records, then what his tracked weeks measured |
| the English dictionary that carries a word to his ontology's own definition words | `nucleus/english.py` (WordNet through `nltk`, read only; data in `~/nltk_data`) | first sense only, in the part of speech English uses most; names, curse words and question words are never carried; not installed → no bridges, nothing else changes |
| the judgment when no dictionary word is told | `Told.judged`, used in `ask.py` | PROPOSAL, and since 2026-10-02 his to define ("I will need to define the logic for the middle response."): the middle answer when his graph holds accepted records in the life domain(s) his ontology files the entry under, "I don't know" when neither his dictionary nor his graph holds anything, with one line saying which of his words are in neither |
| one record, many threads: his phone, the page and the answer being written reach it at once | `nucleus/store.py` | every door into the record opens one at a time (one lock around every `Store` method). Before: 80 entries fired at a copy with nothing between them dropped 4 requests, `sqlite3.InterfaceError: bad parameter or other API misuse`. After: 0. In the engine since September; switch on or off |
| the paragraph is saved before the answer | `nucleus/ask.py` | his phone stops looking the moment it sees the answer, so the paragraph under it is already there |
| on the page, the thumb under the paragraph | `nucleus/serve.py` | the row thumbs had taken it over and the engine refused it with 400 (his thumb of 2026-10-02 20:04 was not saved); it keeps its own door now, `/thumb-explanation`. The phone app always used that door |

Every number and word list that decides something in these files is marked PROPOSAL. Nothing was asked of Adam for
any of it: his words, 2026-10-02, "When you say one thing needs your yes, you are following your logic, not mine".
Turn it off by removing `NUCLEUS_NARRATIVE` from the installed plist and reloading the service; the path is then
exactly what it was at `c80d471`.

New machine: `.venv/bin/pip install nltk` then `.venv/bin/python -c "import nltk; nltk.download('wordnet')"`.

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
