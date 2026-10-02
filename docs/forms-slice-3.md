# Forms slice 3 — the first night pass

Built on `codex/forms-slice-3` from exactly
`5aded943ab80b64c5ce049452aa4320825d7bdb6` (`codex/forms-slice-2`).
Slice 4 is not built. There is no approval endpoint or phone page.

## Observed first run

**12 proposed, 0 refused by the form checks, 0 approved.**
The existing Codex door (`gpt-5.6-sol`) made one call and returned 12 forms.
The pass saved 31 distinct filled examples, at most three per form.
No refusal reason exists for this run because every returned form passed.

The copy contained 120 painted answers. Code reconstructed 106 from the
saved answer text and reply JSON. Fourteen were skipped because a saved row
had no unambiguous printed middle word; it did not borrow a relationship
from today's links table. Those are skipped source answers, not refused forms.
Each skipped answer and reason is retained in the run inputs and report.
There were no form misses or thumbed-down explanations in this first copy.

Three exact saved examples, all still awaiting Adam's yes:

- **F-4:** Your screen connects FLOW with 3 supports rows.
- **F-5:** The rows associate LIFT through 8 entries marked correlates with.
- **F-11:** For MOMENTUM, the most frequent displayed relationship is depends on.

[The full report](forms-slice-3-first-night.json) contains every form's
conditions, original model object, number, status, and examples with question
IDs, screen snapshots, and the origin of every filled part.
[The preservation proof](forms-slice-3-proof.json) records counts and the backup hash.

## Copy and command

The live database was opened read-only and copied with SQLite's backup API,
which includes committed WAL contents. Both backup and working copy passed
`PRAGMA integrity_check` before the pass. The original backup was kept:

- Source: `~/Library/Application Support/nucleus/nucleus.sqlite3`
- Untouched backup: `~/Library/Application Support/nucleus/forms-review/slice-3-original.sqlite3`
- Run copy: `~/Library/Application Support/nucleus/forms-review/nucleus.sqlite3`
- Copy manifest: `~/Library/Application Support/nucleus/forms-review/slice-3-copy-manifest.json`
- Local first-run report: `~/Library/Application Support/nucleus/forms-review/slice-3-first-night.json`
- Run ID: `4505483d-8604-4a8e-9c2c-73458bb615d8`

The command was run from the slice 3 worktree, using the existing venv:

```sh
/Users/adamblair/Documents/nucleus/.venv/bin/python -m nucleus.forms night \
  --store '/Users/adamblair/Library/Application Support/nucleus/forms-review/nucleus.sqlite3' \
  --bootstrap
```

`python -m nucleus.forms night` defaults to that existing review copy.
`--store` can select another existing copy. The live path, symlinks to it,
and hard links to it are refused **before opening Store or creating tables**.
An absent database is refused. `--bootstrap` adds historical painted answers
for a first pass; an ordinary pass reads new misses and thumbed-down paragraphs.
The command refuses to run with `NUCLEUS_FORMS_ONLY` on; it never changes it.

## Inputs, checks, and retention

`nucleus/forms_night.py` calls the unchanged `nucleus/model.py` door with
`nucleus/forms.schema.json`. Each proposal supplies only `when` and `sentence`.
Unused schema conditions are null on the wire and omitted in the saved form.
Code assigns a number above every existing number, author/provider/model, date,
and `proposed` status. The model cannot approve anything.

All six condition types and six blanks use the existing checker/filler.
`forms.preview` shares that code but permits proposed text only for review;
`fill` and `pick` still select approved forms only. Each candidate is checked
against all usable inputs, including those beyond its first three examples.
Unsafe fills refuse the whole candidate. No matching safe example also refuses it.
Every displayed part is from the form or the saved screen; counts are derived
from that screen. Proposed forms remain separate from the empty `forms.txt`.

Approved-file forms and database proposals/rejections are supplied to the
model, including refusal reasons. Exact duplicates are refused after
normalizing condition order and sentence case/spacing. Semantic near-duplicates
still require Adam's review; code does not invent a model-based equivalence rule.

Each pass writes at most 12 rows to `form_proposals`. A nonconforming model's
additional items are kept as refused raw results with `night limit: more than
12 forms`; they cannot create more proposal rows or disappear from later prompts.

Two additive audit tables retain the work:

- `form_night_runs`: inputs and source reasons, exact prompt/reply,
  provider/model, start/finish, completed/failed state, and error.
- `form_night_results`: original model object, associated proposal ID,
  refusal reason, and up to three filled examples with snapshots/provenance.

The exact model call is also saved in `model_calls` under `forms-night:<run-id>`.
The proposal rows, result rows, and successful completion are one transaction.
A failed call, malformed response, or write failure consumes no inputs and
leaves no partially saved batch. Full responses survive parse/write failures.
A per-copy process lock prevents overlapping passes on the same path.

Successful runs consume input fingerprints instead of a question's old creation
time: a later downvote or a miss arriving during a call remains eligible.
A failed/interrupted run can be retried. An unchanged downvote is handled once.
The existing explanation table has no thumb-event timestamp, so an up/down
cycle ending on the same unchanged paragraph cannot be distinguished from its
previous downvote. This slice does not change the thumbs API or its storage.
Historical sources that cannot be reconstructed are explicitly kept as skipped.

## Schedule and verification

`launchd/com.nucleus.forms.plist` follows the links job's structure, with
03:00 and `~/Library/Logs/nucleus-forms.log`. It explicitly targets the review
copy and contains no switch override. **It is not installed or loaded.**
`plutil -lint` passes; `~/Library/LaunchAgents/com.nucleus.forms.plist` is absent,
and `launchctl print gui/501/com.nucleus.forms` reports no such service.
Installing any future schedule or selecting production storage is a separate action.

**184 tests pass**: the previous 154 plus 30 night-pass cases. Coverage includes
proposed/day separation, valid provenance, every refusal category, duplicate
history, overflow retention, new/late inputs and downvotes, failed-call retry,
transaction rollback, concurrent-run exclusion, copy guards, and the plist.

The saved first-run examples were refilled from their recorded screens and
compared character for character. Every question ID exists in the copy. The
empty approved file still picks no form for all 31 examples. The copy passed
integrity checking after the run. All original rows in all ten source tables
are unchanged; the only addition to those tables is the one night model call.
The untouched backup's SHA-256 is unchanged.

No live schema or service change, deployment, phone change, approved form,
merge to main, or slice 4 work is part of this slice.
