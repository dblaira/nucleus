# CowboyAI actual-use verification — October 14, 2026

The missing Ask path and the hidden ontology explanation are repaired. The
simulator completed 22 checks with no failures. Testing Adam's actual How-To
example also exposed an unrelated opening quote in Nucleus; the correction is
now deployed at `6ff807a`. The three real-question flows passed again against that deployed engine, and
the final entry-screen contrast check passed. Evidence is recorded below.

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

These are unmodified simulator screenshots. The final response screens use the
repaired live engine; the original defect is separately labeled.

| Screen | Evidence |
| --- | --- |
| Home with direct Ask | [Home](home-ask.png) |
| Original How-To form using Adam's example | [Question and Ask](original-how-to-form.png) |
| Entry form with keyboard open | [Reachable Ask control](entry-ask-keyboard.png) |
| Actual ontology-based explanation | [Belief and Health](final-ontology-answer.png) |
| Saved entry after app restart | [Original response reopened](final-saved-entry-answer.png) |
| Meaning opened from Adam's example | [FLOW](flow-meaning.png) |
| Record opened from a real response | [Source record](repaired-opened-source-record.png) |
| Unavailable service | [Writing preserved](connection-failure-keeps-writing.png) |
| Repaired How-To answer | [DELEGATION and FLOW](repaired-how-to-answer.png) |
| Repaired FLOW answer | [FLOW leads the answer](repaired-flow-answer.png) |
| Original defect, before engine repair | [Unrelated opening quote](how-to-answer-relevance-failure.png) |

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

## Initial source verification before the context correction

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

## Answer-quality failure found during actual use

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

The correction was made in Nucleus's source-context selection, rather than
hiding its output in the app. The unrelated conversation shared only `don't`
and `myself` with the question. Those grammar words no longer establish a topic.
Recorded exact questions take precedence over loose word matches, and the
existing operational-request exclusion recognizes requests after a preface.
Genuine later updates remain inspectable, character-for-character. No graph,
ontology, dictionary, relationship or SAVY source was edited.

The engine patch is `6ff807adb70fb20790f72bab635d23cf5d61371f`, fast-forwarded
into the clean running Nucleus checkout and activated by restarting its existing
service. Health reports that exact revision; all eight loaded module hashes match.
The candidate was first exercised against an integrity-checked copy of the live
database. The result begins with DELEGATION and FLOW, without unrelated chat
instructions, and uses no model.

Engine checks: **46 passed, one existing failure**. The failing doctor-form test
expects an older graph quote and fails identically on the unchanged baseline.
It was not altered or weakened. All 31 source-context checks, including ten new
regression cases, pass. Engine details are in
`/Users/adamblair/.codex/worktrees/nucleus-operational-context-20261014/docs/operational-context-2026-10-14/verification.md`.

## Final deployed-engine acceptance

`/tmp/CowboyAI-Repaired-Context.xcresult`: **3 passed, 0 failed**, covering real
How-To and FLOW submissions, meaning and graph-record inspection, pin/relaunch,
and the entry's doctor question with saved-response reopening. The entry answer
also received a small contrast correction so the status bar stays readable over
the navy background; its complete flow passed again in
`/tmp/CowboyAI-Final-Entry-Screen.xcresult` (**1 passed, 0 failed**).

Final source check: every tested request matches the current source bundle,
`6a4850598a77cd2c7dbdb6d3c88871f68de3831e60ce61dbcf46d622b8500d13`.
Each verified 757 originals and made zero model calls or new relationships.
`repaired-source-verification.json` contains exact hashes, current health, and
explanations. Complete responses are `repaired-live-flow.json`,
`repaired-live-ontology.json` and `repaired-live-how-to.json`.

- FLOW: `e06b3760-8ea3-4ce3-a409-cc5391ae1551`; the explanation starts with FLOW.
- Doctor: `a886807c-c373-4da8-8897-5f269e8676d6`; Belief/Health plus the accepted
  professional-advice record, visibly displayed and saved with the entry.
- How-To: `07d29947-107a-4c30-b159-04cc87c066ec`; DELEGATION and FLOW with no unrelated
  conversation opening. Adam's exact submitted question remains intact.

## Scope and handoff

App source baseline: `7b9a6a08c0313b6ccf743ae2c97a3909e04b7a7f` on
`codex/cowboyai-recovery-20261013`. Writable scope: this recovery checkout's
iOS app, its tests and recovery evidence. The existing Xcode UI-state edit is
unrelated and is excluded from the commit. Adam's final physical build remains
his action. The canonical CowboyAI ledger records his latest requirements at
`6223e28`.
