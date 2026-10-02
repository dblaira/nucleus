# Cowboyai Forms Plan

October 2, 2026

## Recommendation

- **Expected going in** — forms would be a new way to answer questions
- **Result, better than expected** — forms have one exact job already waiting: the explanation paragraph under the rows
  - Today that paragraph is written live by a model, after the rows appear
  - **21%** — share of those paragraphs that ever reached the screen
  - **15.6 seconds** — average wait for the ones that did
- **What to build tonight** — four slices, in order. Codex stops at the end of any slice and nothing is broken.

## Adam's words this plan stands on

- "There could be hundreds of nuanced, but clearly coded forms to choose from that would express the response in a narrative or explanatory form."
- "The real trick would be to have AI update or improve the decision tree of narratives so the well would never run dry."
- "I agree every form will need my yes, but that is not a problem if this premise holds."
- "allow AI to be used on a nightly basis, rather than in the actual moment of use for the user."
- From September 12, the reason the paragraph exists: "It just regurgitates my words. The meaning is there, but no explanation to help to use it."

## The day, after this is built — what happens first, second, third

1. **Question in** — same as today
2. **Dictionary reads it** — same as today
3. **Your phrases found** — same as today
4. **Rows painted from your links** — same as today, no model
5. **NEW — a form is picked** — plain code looks at the rows and picks one approved form
   - The form's blanks are filled only from what is on the screen: your words, the middle words, the counts
   - The paragraph appears with the rows, no wait
   - The trace line reads: `5 form F-7 chosen`
6. **No form fits** — today's live paragraph runs, exactly as now. The miss is written down for the night.

## The night — what happens first, second, third

1. **03:00** — one hour after the links pass that already runs at 02:00
2. **Read the misses** — the day's questions where no form fit, and any paragraph you thumbed down
3. **AI writes new forms** — at most 12 a night, each one a rule plus a sentence with blanks
4. **Code checks every form** — any form that breaks a rule below is thrown out, with the reason saved
5. **Code fills each form** — with up to 3 real past answers it would have fired on, so you judge real sentences, not blanks
6. **Morning** — the forms wait for you on the phone page. Yes or no. Nothing is used without your yes.

## One form, shown whole

| Part | What it holds |
|---|---|
| **Number** | F-7 |
| **Fires when** | the answer is aligned · the rows carry the middle word "depends on" |
| **Sentence** | Your rows say {word} depends on {count} things you have written down. |
| **Filled with FLOW** | Your rows say FLOW depends on 3 things you have written down. |
| **Where the 3 comes from** | FLOW's links today: depends on 3 · supports 3 · requires 2 · rejects 2 · explains 2 |
| **Status** | proposed → yes → approved, or no → rejected and kept |

## The rules no agent may change

- **No model in the day path when a form fits** — the paragraph comes from code
- **No form is used without Adam's yes** — proposed forms are never chosen
- **Blanks are filled only from the screen** — his words, his middle words, his records, counts; nothing else
- **Middle words only from his list of 43** — the same list the links already use
- **No advice** — the forms pass the same check the live paragraph passes today: no "should", no "try to", no next steps
- **Nothing is deleted** — a rejected form stays, marked rejected
- **His files are read, never written** — meanings.txt, routes.txt, the graph, the ledger
- **Every form has a number on the screen** — "If it is on the screen and it has no number, it failed."
- **The 58 tests that pass today still pass**

## Tonight's four slices, for Codex

Repo: `/Users/adamblair/Documents/nucleus`. Read `HANDOFF.md`, then `README.md`, then this file.

### Slice 1 — the forms themselves

- **New file** `nucleus/forms.py` — load forms, check a form, fill a form
- **Approved forms live in** `forms.txt` at the repo root, one block per form, readable by Adam, kept in git
- **Proposals live in** a new table `form_proposals` in `nucleus.sqlite3`
- **A form** — number, fires-when conditions, sentence with blanks, status, who wrote it, date
- **Allowed conditions** — answer label · middle words present on the rows · middle words absent · number of records · number of his words · any word missing links
- **Allowed blanks** — `{word}` `{other_word}` `{kind}` `{count}` `{word_count}` `{strongest_kind}` — `{count}` is the number of rows carrying the middle word the form fires on
- **The check** — reuse `explain.check` and its ADVICE pattern; refuse unknown blanks, unknown conditions, middle words not on his list, more than 4 sentences
- **Tests** — a legal form fills; an illegal blank is refused; an advice word is refused; a proposed form is never chosen
- **Kill switch** — if a filled sentence can ever contain a word that came from neither the form nor the screen, stop. Do not go to slice 2.

### Slice 2 — the day path picks a form

- **Where** — `nucleus/ask.py`, the painted branch, right before `explain_module.start`
- **Picking** — every approved form whose conditions all hold; the one with the most conditions wins; a tie goes to the lowest number
- **When one fits** — save it with `store.save_explanation`, provider `form`, model the form number; no thread, no model
- **When none fits** — call `explain_module.start` exactly as today; save a row in a new table `form_misses`
- **The switch** — environment variable `NUCLEUS_FORMS_ONLY`, off by default. On means no live paragraph at all. Adam turns it on, nobody else.
- **Acceptance, in Adam's words** — "rather than in the actual moment of use": a painted question with an approved form has zero rows in `model_calls` and an explanation with provider `form`
- **With zero approved forms** — everything behaves exactly as today. That is the state after tonight.

### Slice 3 — the night pass

- **Command** — `.venv/bin/python -m nucleus.forms night`
- **Reads** — `form_misses` since the last run, explanations thumbed down, all approved and rejected forms so nothing repeats
- **Model** — the existing door in `nucleus/model.py`, answer shaped by a new `forms.schema.json`
- **Writes** — up to 12 rows in `form_proposals`, each with up to 3 filled examples from real past answers, and every refused form with its reason
- **Schedule** — a new launchd job `com.nucleus.forms` at 03:00, log at `~/Library/Logs/nucleus-forms.log`, built the same way as `com.nucleus.links`
- **First run** — run it once by hand tonight over the painted answers already saved, so proposals wait for Adam in the morning

### Slice 4 — yes or no on the phone

- **Where** — `nucleus/serve.py`, a new page `/forms` on port 8766, the same page style as today
- **Shows** — each proposed form, its number, its fires-when in plain words, and its filled examples, biggest first
- **Two buttons** — yes moves it into `forms.txt` as approved; no marks it rejected
- **Nothing else** — no editing on the page tonight

### Stop line

- **Slices 1 and 2 together** are safe to ship alone: nothing changes on screen until a form is approved
- **Slice 3 needs slices 1 and 2.** Slice 4 needs slice 3.
- **If the budget runs out mid-slice** — leave that slice on a branch, unmerged, and write where it stopped in `HANDOFF.md`

## Open for Adam — not decided for him

- **When does the live paragraph turn off** — the switch `NUCLEUS_FORMS_ONLY` stays off until he says
- **How many forms a night** — 12 is a starting number, his to change
- **The 22% that still call the model in step 5** — not in tonight's plan. The same forms idea can reach them next.
- **Where forms live** — `forms.txt` in the nucleus repo is a proposal; the adams-language repo is the other choice

## What this rests on — measured October 1 and 2, 2026

- **108** — explanation paragraphs started since the paragraph was built
  - **23** — reached the screen
  - **77** — still marked pending, the newest from the 06:30 daily check
  - **8** — refused by the code check: 4 off his words, 2 advice, 2 wrong shape
- **15.6 seconds** — average time for the paragraphs that finished
- **1,400** — links between his words and his records, 39 middle words in use
  - supports 255 · depends on 156 · contains 121 · explains 110 · requires 92
- **58** — tests passing today
- **Source of the old method** — Robert Dale, 2023: "reliability—the absence of hallucinatory risk—is traditional NLG's moat", and "automatic variant suggestion is an obvious target for generative AI"
