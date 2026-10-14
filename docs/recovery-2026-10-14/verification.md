# CowboyAI actual-use verification — October 14, 2026

The missing Ask path and the hidden ontology explanation are repaired. The
simulator completed 22 checks with no failures. **The app does not yet pass the
overall usefulness review:** Adam's How-To example exposes an unrelated opening
quote selected by the existing Nucleus service.

## What Adam can now do

- Open **Ask CowboyAI** directly from the home screen. This opens the original
  Theme → Decide → question → Ask form shown in his screenshots.
- Ask from the Reminder, Action, or Calendar entry form using the cream
  **Ask CowboyAI** row. The button remains visible above the keyboard. Untouched
  template prompts alone do not enable it.
- Receive the existing Nucleus response and see the actual explanation from the
  ontology and graph. The middle answer's fixed paragraph remains unchanged below
  that explanation; it no longer hides it.
- Save a new entry with its response and reopen that same response after restarting
  the app. Existing conversation origins remain immutable.
- Return to the entry after a connection failure with the writing intact and the
  Ask control available. An entry request cannot overwrite an unfinished question
  in the separate question composer.

## Visible evidence

These are unmodified screenshots from the final simulator test run.

| Screen | Evidence |
| --- | --- |
| Home with direct Ask | [Home](home-ask.png) |
| Original How-To form using Adam's example | [Question and Ask](original-how-to-form.png) |
| Entry form with keyboard open | [Reachable Ask control](entry-ask-keyboard.png) |
| Actual ontology-based explanation | [Belief and Health](ontology-answer.png) |
| Saved entry after app restart | [Original response reopened](saved-entry-answer.png) |
| Meaning opened from Adam's example | [FLOW](flow-meaning.png) |
| Record opened from a real response | [Source record](opened-source-record.png) |
| Unavailable service | [Writing preserved](connection-failure-keeps-writing.png) |
| Remaining relevance failure | [How-To answer](how-to-answer-relevance-failure.png) |

## Simulator checks

Final result: **22 passed, 0 failed, 0 skipped**, 269.702 seconds, in
`/tmp/CowboyAI-Actual-Use-Final.xcresult`. Full cases and build-log path are in
[simulator-tests.json](simulator-tests.json).

The 11 UI checks exercised actual typing, keyboard accessibility, submission,
opening meanings and records, persistence after relaunch, the radial FAB,
carousel movement and metadata, white leading pinned cards, linked actions,
calendar scheduling, and connection failure. Eleven unit checks covered exact
writing, draft isolation, source preservation, local persistence and schedules.

The three answer scenarios used the real service. Canned conversation fixtures
were used only to populate the surrounding carousel/reminder regression checks.
The connection-failure case used an unavailable local port through a DEBUG-only,
test-only override; the live service and saved endpoint were not changed.

Simulator: **CowboyAI-Recovery**, iPhone 18 Pro Max, iOS 27,
`D2BC1BBD-8375-4225-A9BE-F50C1D65E023`. No physical device was accessed.

## Nucleus and current sources

The app's existing endpoint remains `http://100.111.154.126:8766`.
The service reports revision `25d3c8a954ffb98d6eb361075c41d8b8415d8345`.
All eight loaded module hashes match the running worktree's source files.

For each of the three final real submissions, the saved answer's source bundle
fingerprint matches the current graph, decision ledger, shape, upper ontology,
meanings and routes. Each request checked 752 current original records, created
zero relationships, and made **zero model calls**. Its explanation was produced
by `code / narrative`. Current bundle SHA-256:
`6da11d5fd9d9be2ad55fa0f05aff8659c4679fbd71c4cd4f5e287c1909f7de5b`.

| Real input | Question ID | Observed result |
| --- | --- | --- |
| What is FLOW? | e1be8760-1973-4c43-b385-9d52d3c40cbf | FLOW meaning and source record opened; pinned answer survived relaunch |
| What are reasons I would avoid going to the doctor? | 01384b09-1405-43bc-9788-a7f0d7f4ffd7 | Visible Belief/Health explanation and accepted professional-advice record; saved entry reopened its response |
| Adam's neutral-moments How-To example | a0150ec8-afe6-4fe0-9c52-970ab1593186 | Exact question preserved, live answer returned, FLOW meaning opened; relevance failure below |

Raw responses and source fingerprints are in `live-flow.json`,
`live-ontology.json`, `live-how-to.json`, and `live-source-verification.json`.
This verifies access to the current sources, not the relevance of every selected
record. Normal real submissions were recorded in Nucleus's history. Local UI
test storage is isolated from normal app storage.

## Remaining answer-quality failure

Adam's original example begins:

> I have neutral moments many times per day that I don't have a plan for how to react.  I want a plan.

The live response instead opens with:

> Later in the same conversation, 2026-10-13: “it's noon. I'm out.  summarize what we did hear and add it to both an apple note and a ms word file”

That operational instruction is unrelated to the question. The remainder brings
forward DELEGATION and FLOW, but the unrelated opening fails the relevance review.
The UI interaction test passing does not make this a useful answer.

Read-only source trace in the running Nucleus checkout:

- `nucleus/contextual_sources.py:57` reviews current accepted originals. Literal
  topic overlap can anchor another recorded conversation. It then retains the
  newest eligible later message in that conversation.
- Its operational-request exclusion is anchored at the beginning of the text.
  The quoted message begins with a time/sign-off and the exclusion does not
  recognize the later summarization instruction.
- `nucleus/ask.py:146` adds those context records to the response; line 160 puts
  their text before the actual explanation.

The remaining repair belongs in Nucleus's source-context selection. It must
preserve genuine later updates and exact wording while excluding unrelated
operational messages. It must not hide the symptom in the iOS presentation,
invent new relationships, or silently change the accepted answer criteria.
No engine, graph, ontology, dictionary, or SAVY source was edited in this repair.

## Scope and handoff

App source baseline: `7b9a6a08c0313b6ccf743ae2c97a3909e04b7a7f` on
`codex/cowboyai-recovery-20261013`. Writable scope: this recovery checkout's
iOS app, its tests and recovery evidence. The existing Xcode UI-state edit is
unrelated and is excluded from the commit. Adam's final physical build remains
his action. The canonical CowboyAI ledger records his latest requirements at
`6223e28`.
