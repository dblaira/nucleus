# Forms slice 5

Base: `c660fb15776fcdebaa28401c1c68a854c09367ea`.
Branch: `codex/forms-slice-5`.
Worktree: `/Users/adamblair/.codex/worktrees/nucleus-forms-slice-5`.

Adam's scope is forms for “the middle option (of the three choices it has now)
when part of the situation is aligned but not all.” This replaces the original
plan's slice-5 forms-only rollout: `NUCLEUS_FORMS_ONLY` stays off.

The new middle forms require `answer=not_sure`. They join an exact displayed
word meaning, an exact whole record quote, and one displayed missing half.
New slots: `meaning`, `record_quote`, `missing_why`, `missing_word`, `absent_kind`.
A missing why copies a complete exact absence clause from a printed why line.
A missing word must explicitly be displayed as having no links. An absent
middle word requires a complete printed middle-word display. Model rows cannot
supply invented links or prove absent middle words.

The authored joining frame uses fifth-grade words. Exact source wording stays
whole, including negatives and punctuation. The negative exception is limited
to these new middle forms' copied sources and checked missing half; existing
row forms keep the slice-3c veto. Advice and blocked abstract words remain
refused. No outside facts, paraphrases, hidden links or question text fill a
blank. Plain code performs every daytime selection, approved forms only.

For older model screens, the two positive halves must have printed positive why
clauses and share at least two exact content words. Names, common function words
and possessive suffixes cannot supply that tie. A short unrelated record cannot
be chosen merely because it is shorter. Painted rows retain their actual named
word binding. The separate night review still vetoes unsupported meanings.

An approved middle form replaces only the first line, leaving all rows and the
possibility box intact. Its explanation is saved with provider `form` before
the answer is published; no explanation model starts. The existing answer model
path is unchanged for fresh model-gated answers. Painted and saved cases need
zero model calls when the form applies. With no approved form, all visible
answer and explanation behavior remains unchanged. A complete model-screen
miss is saved for a later night pass.

Night coverage includes rendered `not_sure` history. Different questions count
once after case, spaces and apostrophe shape are normalized. One representative
per question supplies both question and bound-word counts; repeated answers
cannot inflate either. Every different fill still reaches semantic review.
At least three different questions and two bound words are required. Count
conditions remain minimums or genuine ranges; exact numbers are refused.
The page says “Fits N different questions”, largest first, with up to three
examples for different words and questions. Yes / No and approval boundaries
are unchanged.

## One manual night pass

The copy was backed up to `slice-5-before.sqlite3`, integrity checked and hashed.
One pass ran with `--bootstrap --middle-only`, run
`4914afb5-f557-4ea5-884f-734e61a40890`: 62 inputs, 44 recoverable screens.
The writer proposed one candidate, F-39. It fit three different questions and
three bound words, but the separate meaning review refused it because a selected
momentum meaning had been paired with an unrelated learning record.
**0 proposed, 1 refused; F-39 is retained as rejected.**

That refusal exposed the quote-pairing issue. The deterministic shared-source
check above was added, with regression tests and actual accepted-source day
verification. Read-only previews under the fix fit three questions across three
words. The original refused run and examples are preserved unchanged. No second
night run was made: Adam requested “once by hand”. The real review queue remains
empty; putting new proposals there requires another authorized pass.

396 tests pass, including not_sure-only selection, repeated-question counting,
unapproved-form exclusion, exact source barriers, unsupported gaps, unrelated
quote refusal, zero-approved fallback, and no explanation-model selection.

Phone link: http://100.111.154.126:8767/forms.
Only the old review process was stopped. The review runs from this worktree with
`--port 8767 --store ~/Library/Application Support/nucleus/forms-review/nucleus.sqlite3`.
The live PID 1941 on 8766 and its database were neither opened nor requested.
No real approval, launchd installation, forms-only enablement or merge occurred.
The original dirty checkout is preserved. Exact questions, quotes, model traces,
full reports and screenshots remain local; this repository is public.

See [night summary](forms-slice-5-night.json) and
[preservation proof](forms-slice-5-proof.json). The exact instruction is appended
on private companion branch `codex/forms-slice-5-ledger`.
