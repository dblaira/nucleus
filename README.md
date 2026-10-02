# nucleus

Adam, 2026-09-10: "That is the nucleus." "The RDF, Ontology, Dictionary all stay." "Forget what you see in Cowboyai now. Create an independant system around this foundation that is constrained to give answers with the 3 different formats."

## The three answers, in Adam's words

1. "aligned and why"
2. "Not sure.  some correlation, but not enough for causation, more data may help."
3. "I don't know" there is nothing in your records that points to a conclusion.

Under "Not sure" there is a second box, in his word: **possibility**. "So it's the more data may help that I believe is a perfect opportunity for AI to use its inference to help me. What I mean by that is that's a time for creativity." It is the only place the model may propose anything. What it proposes is saved as a candidate and never enters the graph or the dictionary without his yes.

"I don't know from Cowboyai means I know from myself or the user."

## The nucleus, read whole every time

- `/Users/adamblair/Documents/Main/Ontology/accepted/accepted-graph.ttl` — 239 records
- `/Users/adamblair/Documents/Main/Ontology/accepted/decision-ledger.json` — 259 decisions, 191 accepted
- `/Users/adamblair/Documents/Main/Ontology/shapes/connection-shape.ttl` and `upper/bfo-bridge.ttl` — the rulebook
- `/Users/adamblair/Documents/adams-language/meanings.txt` — his dictionary
- `/Users/adamblair/Documents/adams-language/routes.txt` — his routes

"The reason for it is so it can be grounded in my meaning. Of course it has to go through all the fucking records."

## The path of one question

1. Question in. Saved with its time.
2. The dictionary reads it with its own program (`npm run brief-json` in adams-language). A mark with no number stops here. Two meanings, none named, asks here.
3. The five files above are read from disk, whole. Code adds one derived list: the graph records that have no accepted decision in the ledger, so the model does not cite them.
4. One model call. The exact prompt and reply are saved.
5. The gate. Code checks the reply: one of the three answers; every cited record exists, its quote is character for character, its latest ledger decision is accepted; every why is one sentence; possibility only under not_sure, every link a real record or word.
6. The answer, the records, the seconds per step go back to whoever asked and into the store.

## Run it

```
.venv/bin/python -m nucleus.ask "What is FLOW?"
.venv/bin/python -m nucleus.serve        # http://127.0.0.1:8766/
.venv/bin/python -m nucleus.grade        # questions.txt through the path, report to Apple Notes
.venv/bin/python -m pytest
```

The server accepts `--port` and `--store`. With no options it still uses port
8766 and `~/Library/Application Support/nucleus/nucleus.sqlite3`.

The slice 7 review runs from its separate worktree against the existing copy:

```sh
cd /Users/adamblair/.codex/worktrees/nucleus-forms-slice-7
NUCLEUS_FORMS_ONLY=0 .venv/bin/python -m nucleus.serve \
  --port 8767 \
  --store "$HOME/Library/Application Support/nucleus/forms-review/nucleus.sqlite3"
```

`/forms` shows pending forms with Yes / No. Yes writes an approved block to
`forms.txt` in the running code's worktree; No keeps the rejected proposal in
the selected database. See [slice 7](docs/forms-slice-7.md) for the running copy
and verification. `NUCLEUS_FORMS_ONLY` remains off.

The review copy reads his accepted Turtle set and uses forward RDF paths for
the three labels. Forms use generated SPARQL ASK over the exact screen inside
that graph. Graph build and answer query times are saved in steps. All graph
questions share 300 ms; failure or a budget miss uses the old rule, marked
`count rule`. AI runs only at night on this graph path. Source files are read
only; derived links stay beside the copy in `forms-links.ttl`.

Approved middle-option forms replace the fixed `not_sure` opening with exact
screen quotes and a displayed missing half. Selection uses plain code. With no
approved form the graph copy prints its checked rows without a model paragraph.
The default live route is unchanged. The night pass counts different questions once and
requires three questions across two bound words, including one real question;
proposals wait for Adam's Yes. Real questions are from the web and
cowboyai-iphone surfaces. The page shows real and practice fits separately.

The copy-only night pass first asks AI for up to 20 new dictionary-targeted
practice questions, shaped by Adam's own real questions. Each uses normal ask
and quote checking, saved with surface `practice`. Practice never appears in
history, real repeats, link seeding or the morning grade. Conditions identify
one form; wording variants are refused as `same form`.

## The model

One call. The Anthropic Messages API when a key is in the keychain (`security add-generic-password -s nucleus -a anthropic -w <key>`), with the nucleus block cached. Otherwise the signed-in Codex CLI, run as a plain model call: user config and rules ignored, reasoning low, read-only, in an empty folder, answer shaped by `contract.schema.json`.

Measured 2026-09-10 on a one-line prompt: 58 s with Adam's Codex config loaded, 9 s without. On the full 378 KB prompt: 20 to 35 s without.

## Storage

`~/Library/Application Support/nucleus/nucleus.sqlite3`: questions, steps, model_calls, answers, candidates, grades. Nothing is deleted.
