# Forms review repair — ready branch, not deployed

Base: `e1d91f7c8e203ae7d700766d37dd5b84ad57093b` (slice 7c).
Branch: `codex/forms-review-fix`.
Worktree: `/Users/adamblair/.codex/worktrees/nucleus-forms-review-fix`.

Adam reported that the first review cards made no sense, then requested action.
While this repair was being prepared, another session changed the shared review
copy and began a separate short-form implementation. Adam chose that session
to finish and restart the page, and asked this session to keep its fix ready.
This branch is therefore an integration candidate, not the running review app.
His exact feedback and ownership decision are on private companion branch
`codex/forms-review-fix-ledger`.

## What was broken

The page printed an example's filled answer under the label “Your question”
without printing its saved question. Yes approved a reusable template and its
conditions, but that scope was not explained beside the decision.

The night reviewer checked quote copying, row direction and author style. Its
instructions did not require those quotes to apply to the actual question.
The review list also deduplicated by filled sentence, so two different
questions producing the same answer collapsed into one review example.
Existing pending forms received coverage/structure checks but did not receive
the new candidates' semantic review.

## What this branch changes

Each exact question now appears immediately before its “Proposed answer”.
Real and practice questions stay distinct. The two Yes/No buttons retain their
existing action; the text beside them explains that Yes allows this way of
answering future matching questions and No rejects and retains the form.
Counts, firing conditions and graph-check information are in a closed native
details section after the decision. The palette, hat, photo, numbers, fit
ordering, exact example text and up-to-three-example rule remain.

Missing question/answer text disables Yes and shows the reason on the card.
The server also refuses a direct Yes request with missing question context;
disabling the visible button alone is not the guard. No remains available.

Night semantic review now keeps distinct question/source/answer contexts and
requires relevance to the question, including the intended dictionary sense.
A same-spelling ordinary word and a personal dictionary word are not enough to
establish relevance. Exact quotes and valid graph paths alone do not pass this
check. An `off_topic` verdict refuses the whole candidate with
`does not answer the question: ...`; a bad matching example is not hidden or
subtracted to manufacture passing coverage.

Only the author's literal words are graded for reading level, negatives,
advice or style. Copied source text remains exact and exempt from those style
checks. Its applicability to the question is checked separately.

Every measured match receives a `context_review` annotation only after all
bounded semantic packets for that form pass. It contains the policy version
and a SHA-256 digest of the complete form payload, exact question, screen,
filled text and source parts. The annotation is excluded from its own digest.
Approval checks require that current evidence; absent or changed evidence
blocks Yes. The existing page version includes the matches and therefore also
changes when this evidence changes. Already completed human decisions remain
protected. No new proposal status or database table is introduced.

Existing pending forms with missing/stale evidence enter the same bounded
night review as new candidates. Current unchanged evidence can be reused.
All distinct question contexts remain in the packets; exact repeated contexts
may share a review. The 12-form schema limit applies to each packet, including
when old pending and new forms are reviewed together. Complete prompts/replies
retain the existing independent model-call receipts.

## Integration boundary

No real night pass or model call was made for this ready branch. Tests use
temporary synthetic stores and model replies. The visual preview uses made-up
examples, serves static HTML on an ephemeral loopback port, and opens no
database. It cannot approve anything.

This session did not change the shared review copy, approved catalog, graph,
dictionary, source records, service on 8767 or live service/database on 8766.
The other session's branch and new forms are not copied, reset or merged here.
Nothing is approved or merged by this repair. The forms-only setting stays off.

Before deployment, the owning session needs to integrate this patch with its
short-frame implementation, resolve any intentional frame-rule differences,
and rerun the review tests. This branch's base understands slice 7c frames;
it must not replace a newer short-frame runtime by itself. Pending forms will
need a current night relevance check before Yes becomes available under the
new guard. Existing day selection and graph-label rules are unchanged; this
repair adds no daytime model or general-purpose word-sense classifier.

Validation results are recorded in `HANDOFF.md`. Full private source examples
and screenshots of actual questions remain outside the public repository.
