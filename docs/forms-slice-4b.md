# Slice 4b: forms must fit past answers for different words

Base: `3dba8c53d30d02acceeb6ba3bf5fe25374509eb6`.
Branch/worktree: `codex/forms-slice-4b`,
`/Users/adamblair/.codex/worktrees/nucleus-forms-slice-4b`.

## What changed

The night schema and prompt only offer count minimums (`{"min": 2}`) or ranges
(`{"min": 2, "max": 10}`). The deterministic check refuses exact integers,
equal range endpoints, and maximum-only conditions. Historical payloads and
the day filler's count semantics are preserved. Approval rechecks the new rule.

Coverage is measured across **all past painted answers**, independent of which
misses or downvotes triggered this pass. A complete saved miss snapshot takes
precedence; otherwise the original printed answer is reconstructed. Today's
links never stand in for the saved screen. Unrecoverable screens are excluded,
as before. Unfinished questions, failed answers, and model answers do not count.

Each successfully filled question ID counts once. Multiple miss/downvote/
bootstrap entries cannot inflate it. Different words means the words actually
bound into the sentences: listing three words on a screen whose fill is about
FLOW still counts as FLOW only. Fewer than three answered question IDs **or**
fewer than two bound words returns exactly `fits too few answers`.

The additive `form_night_coverage` table saves all successful matches, including
their question IDs, saved screens, exact filled sentences, and source parts.
Nothing in earlier runs is rewritten. The semantic reviewer sees every distinct
filled sentence, while the page retains at most three examples, one per word.
`/forms` shows the answer and word counts and sorts by answer count descending,
then by form number. The form file remains the sole day-path approval source.
No change enables `NUCLEUS_FORMS_ONLY`.

## Re-proposing the three narrow forms

```sh
cd /Users/adamblair/.codex/worktrees/nucleus-forms-slice-4b
/Users/adamblair/Documents/nucleus/.venv/bin/python -m nucleus.forms night \
  --store "$HOME/Library/Application Support/nucleus/forms-review/nucleus.sqlite3" \
  --bootstrap --widen F-25 F-26 F-31
```

This command **already ran**. `--widen` preserves each template and non-count
condition and turns exact counts into minimums. New numbers and the author
`program/widen-counts` identify this mechanical re-proposal. There is no writer
model call. Candidates still pass all normal checks and, if eligible, the
semantic reviewer. Old decisions and new results are committed together only
when the run succeeds. Repeat detection includes both sentence and conditions,
so the widened form differs from its narrow original.

| Original → widened | Count conditions | Answers | Words | Result |
| --- | --- | ---: | ---: | --- |
| F-25 → F-36 | ≥15 rows, ≥1 word | 32 | 1 | fits too few answers |
| F-26 → F-37 | ≥15 rows, ≥1 word | 32 | 1 | fits too few answers |
| F-31 → F-38 | ≥12 rows, ≥3 words | 1 | 1 | fits too few answers |

The first two match repeated answers for FLOW; the third matches PULLED. The
two-word requirement refuses all three. The old forms are kept with the exact
reason `fit one screen only`. No candidate reached semantic review, and no
model call was added. There are now no pending or approved real forms.

The run read 120 historical inputs, of which 106 had recoverable screens; the
same 14 previously unrecoverable screens remain recorded with their reasons.
See [the run summary](forms-slice-4b-night.json) and
[the preservation proof](forms-slice-4b-proof.json). Full private screen records
are in the local review folder's `slice-4b-night.json`, not this public repo.

## Review server and verification

The new worktree serves **http://100.111.154.126:8767/forms** against
`~/Library/Application Support/nucleus/forms-review/nucleus.sqlite3`.
`slice-4b-server.json` records PID 58000 and the command; `slice-4b-server.log`
holds its output. Only the old review process was stopped. Port 8766 still has
its original PID 1941 and was never queried. The live database was never opened.
No launchd job was changed. The review worktree must stay in place while its
manual server runs. The actual review page correctly shows an empty queue.

**332 tests pass.** New tests cover exact integers and disguised exact ranges,
too few answers, too few words, consumed history, source deduplication,
unpainted/unfinished exclusions, distinct examples, widened-form signatures,
atomic failed re-proposals, sorted counts, and stale coverage on approval.
Existing positive fixtures were extended with actual painted answers meeting
the new floor; their safety assertions remain. A baseline HTTP test exposed an
unread-body connection reset; bounded POST bodies are now consumed before the
wrong-content-type response.

Browser tests used separate synthetic data on 8769: F-2 (5 answers / 4 words)
appeared above F-1 (3 answers / 2 words), with three and two distinct-word
examples. At a 480-pixel CSS viewport there was no horizontal overflow; buttons
were 50 pixels high and examples 25-pixel type. Yes and No were clicked on these
test forms and their file/database results read back. The fixture was stopped.
The actual 8767 phone URL then returned HTTP 200 and displayed the empty queue.
No physical phone was operated. Screenshots stay local.

The copy was backed up before this pass. Both integrity checks pass and the
backup SHA-256 is unchanged. Every earlier row remains; only the three old
proposal decision fields changed. The run added three retained rejected forms,
their coverage, and the run/results/rechecks. All 65 measured fills were
reproduced exactly. Real `forms.txt` is empty; nothing was approved or merged.
Work stops at slice 4b.
