# Slice 4: Yes or No

Base: `04fe394fffbb9354212cf6cdb6f123d22735a2c8`.
Branch: `codex/forms-slice-4`.
Worktree: `/Users/adamblair/.codex/worktrees/nucleus-forms-slice-4`.

## Running review

Open **http://100.111.154.126:8767/forms** on the phone. The manual server uses
the existing database copy in
`~/Library/Application Support/nucleus/forms-review/nucleus.sqlite3` and this
branch's `forms.txt`. Its process details and log are `slice-4-server.json`
and `slice-4-server.log` in that folder. Leave this worktree in place while the
server runs. Later Yes choices will modify its `forms.txt`; they are not
automatically committed or pushed.

Startup options are `--port` and `--store`. Their defaults remain 8766 and the
live database. No request was made to the service on 8766; its original PID
1941 remained running. The live database was never opened. The review process
on 8767 is separate; no launchd job was installed or loaded.

The page reuses the original page's palette, hat, photo, and type. It shows
each pending form's number, filled examples in the largest card type, and its
fires-when in plain words. There are exactly two buttons per form and no
editing controls. Examples come from the saved night-pass screens, with exact
text and source-row provenance checked again before approval.

## Decisions and preservation

**Yes:** recheck the saved form and examples, preserve existing file blocks
and comments, append an approved TOML block, validate the complete file, then
publish it with an atomic rename. Write an approval receipt in the copy.
**No:** mark the proposal rejected with `Adam said no on /forms.` and retain
its payload and examples. The queue then shows the remaining proposals.

`forms.txt` remains the only authority used by the day picker. The additive
`form_approvals` table stores proposal ID, approval time, and the file path.
It avoids rebuilding the original proposals table or rewriting its original
payload. `Store.form_proposals()` and night reports expose the effective
approved status through this receipt. Raw proposal rows retain their original
`proposed` / `rejected` schema; neither those rows nor receipts are inputs to
the day picker.

The decision holds the same database lock as the night pass plus a lock for
the worktree's forms file. Repeated identical choices are idempotent; an
opposite choice or stale saved examples yields a conflict. Requests carry a
server token and same-origin check; they cannot submit edited form text.
An outside file edit is preserved and causes a conflict.

The file is published before the receipt. If receipt persistence fails after
publication, the approved file is kept, and repeating the original Yes repairs
the receipt without duplicating the block. The queue checks the file as well
as the receipt, so an already-published Yes is not offered for a second choice.
All previous template, pattern, quote, advice, and approval checks remain.

## Verification

- **307 tests pass** (`/Users/adamblair/Documents/nucleus/.venv/bin/python -m pytest -q`).
  Baseline: 273. New cases cover Yes, No, proposed-never-chosen, stale and
  concurrent choices, duplicate numbers, file failures, interrupted receipts,
  forged/editing requests, startup defaults, and independent server stores.
- Browser clicks on two separate synthetic test forms produced one approved
  file entry and one retained rejected proposal. The empty queue was observed,
  and the resulting file and database were read back. This fixture used its
  own files on port 8769 and was stopped afterward.
- The real phone URL returned HTTP 200 and rendered F-25, F-26, and F-31.
  At a 403-pixel browser width there was no horizontal overflow, examples used
  25-pixel type, and each of the six buttons was at least 50 pixels high.
  All cards were visually inspected. No physical phone was operated.
- All 15 existing database tables retain exactly the same rows as
  `slice-4-before.sqlite3`. `form_approvals` is the only new table and is empty.
  The backup SHA-256 is unchanged; both databases pass `integrity_check`.
  No model call was added. See [the proof](forms-slice-4-proof.json).
- Real proposals remain **3 proposed, 32 rejected, 0 approved**. This branch's
  `forms.txt` is empty. `NUCLEUS_FORMS_ONLY` is off. No merge to main.

Screenshots, copied screen records, and the browser response containing the
session token are local only. No real proposal was decided during verification.
The temporary mockup and fixture servers were stopped; the requested review
server on 8767 remains running. Work stops at slice 4.
