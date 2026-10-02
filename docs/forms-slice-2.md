# Slice 2 — the day path picks a form

October 1, 2026 Pacific. Base: `9695d13a7731bf489576c76f2df365700f2a3abb`
on `codex/forms-slice-1`. Implementation branch: `codex/forms-slice-2`.
Worktree: `/Users/adamblair/.codex/worktrees/nucleus-forms-slice-2`.

## Scope and authority

Objective: build only the second slice in `FORMS-PLAN.md`, prove both
acceptance paths, push without merging to main, and stop before slice 3.
Authoritative inputs: Adam's current request, the plan read from
`/Users/adamblair/Documents/nucleus/FORMS-PLAN.md`, HANDOFF/README, Cowboyai's
operating contract, and the slice 1 source at the specified base commit.
The current root plan differs from the committed copy only in its two date
headings; the implementation requirements are identical.

Exclusive implementation scope: `nucleus/forms.py` (selection and switch),
`nucleus/ask.py` (painted branch and live-paragraph suppression),
`nucleus/store.py` (additive misses), and the existing step-name rendering in
`nucleus/serve.py`. Tests, this verification record, and HANDOFF are included.
Dependencies: slice 1 validator/filler, the existing painted picture and
explanation path. No added package dependency.

Forbidden scope: approving a product form, modifying Adam's meanings/routes/
graph/decision ledger, live database migration or deployment, phone changes,
main merges, night generation/scheduling, and the slice 4 `/forms` page.
Adam's instruction is also appended verbatim on the separate Cowboyai ledger
branch `codex/forms-slice-2-ledger`.

## Behavior

The painted branch builds a `forms.Screen` from the exact words and records
in `links.paint`'s picture. It never looks up extra links for filling.
`forms.pick` loads `forms.txt`, considers approved forms, orders them by the
number of `when` condition keys (descending), then by numeric form number
(ascending), and takes the first one that matches and safely fills.
Unsafe filling is refused. Missing/unreadable/invalid form files produce a
recorded miss and preserve the ordinary fallback while the switch is off.

When a form fits:

- `store.save_explanation` saves provider `form`, model `F-N`, and the exact
  filled sentence with its form number prefixed: `F-7 · …`.
- The explanation is saved **before** publishing the answer, so a polling
  client cannot see a completed answer and stop before the form is available.
- No explanation thread or model call runs.
- The step is `5 form F-N chosen`; its note retains the output parts and their
  origins. The existing web trace displays that actual step name. Its layout
  and the zero-form trace remain unchanged.

When no form fits, `form_misses` receives a fresh UUID, question ID, exact
painted picture JSON (including quotes, word/record IDs, kinds, and missing
words), reason, and timestamp. Existing question storage retains the input.
Misses are append-only, including repeated attempts. With the switch off,
`explain_module.start` receives exactly the same arguments as before.

`NUCLEUS_FORMS_ONLY` remains unset/off. Only `1`, `true`, `yes`, and `on`
(case-insensitive) enable it. If Adam later enables it, no live explanation
paragraph starts on either the painted or ordinary model-answer branch. It
does not turn off the existing primary model-answer path outside this slice.
The existing `explain_call=False` option still skips all paragraphs and does
not attempt selection or record a miss.

`forms.txt` remains empty. Test fixtures do not approve a product form.

## Acceptance evidence

**154 tests pass**, including all 132 tests from slice 1. The 22 new cases
cover both acceptance paths, pending-to-shown fallback with the real thread
code and a controlled model callback, ranking/numeric ties, refusal and file
failure, hidden rows, opt-out, switch behavior, miss persistence, and saving
the paragraph before publishing the answer. Switch-on tests are temporary
pytest environment overrides, automatically restored; service/configuration
was never changed.

A separate probe made a read-only SQLite backup of the running service's
database, verified integrity, and worked only on isolated copies. Every
existing table's rows were fingerprinted before and after `Store` initialized
the new tables; all original contents matched. The probe used the actual
dictionary reader and saved FLOW links, without calling an external model.

| Acceptance | Observed result |
| --- | --- |
| Approved F-7 fixture, painted FLOW | 15 painted rows; `model_calls = 0`; explanation provider `form`, model `F-7`; no explanation thread |
| Filled paragraph | `F-7 · Your rows say FLOW depends on 3 things you have written down.` |
| Zero approved forms compared directly to `9695d13` | Same answer, words, records, phrases, step names/notes, saved reply JSON, and explanation content/provider/model |
| Fallback calls | One explanation thread and one `model_calls` row on each version, using the same deterministic verification callback |
| Miss | One row with reason `no approved forms`; snapshot matches the exact painted records |
| Existing page | Inspected rendered paragraph, visible `F-7`, and `5 form F-7 chosen` in an isolated read-only browser preview |

Machine-readable results: [forms-slice-2-proof.json](forms-slice-2-proof.json).
Rendered proof: [forms-slice-2-rendered.jpg](forms-slice-2-rendered.jpg).
This is verification of the branch on a separate database, not a deployment
to the running service or installed iPhone app.

**Stopped before slice 3. No merge to main, no product forms approved, no
deployment, and `NUCLEUS_FORMS_ONLY` remains off.**
