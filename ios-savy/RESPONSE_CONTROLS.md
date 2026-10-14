# Saved response controls

Adam supplied the Re_Call/Understood screenshot with **Done / Unpin / Delete** and a collapsed **Completed** list, then asked for simulator testing while he was away. His exact instructions are in Cowboyai's append-only ledger, task `01a13c09-164c-7592-b0d5-0212b8684a07`.

## Scope and source

Base: `b85bde791d9ab68117d4035fe99b11d331fefb20`, branch `codex/cowboyai-response-controls-20261014`.

The matching source is `/Users/adamblair/Developer/GitHub/Re_Call/ios/ReCall/App/ActionsHomeView.swift` (`cardActions`) and `ItemListView.swift` (`CompletedBand`), inspected at Re_Call revision `28fcb8848c4fb654a2b280b46d157e4fe19443df`. CowboyAI already carries the shared SAVY swipe/card components. This change reuses them with Re_Call's complete, reopen, and soft-delete behavior.

Write scope: the trial's local conversation archive, saved-response list, completed-row accessibility, focused tests, and this handoff. The engine, service, databases, bundled history, source apps, signing, and app identity are outside this slice.

## Behavior

- Swipe a saved response right to reveal Done, Pin/Unpin, and Delete.
- Done removes the response from the active list and carousel. Completed shows a count and expands to every completed response.
- Tap a completed response's title to read its full saved answer. Tap its checkmark to reopen it. Its existing pin and notes remain. Long-press offers Reopen and Delete.
- Delete removes the response from active and completed screens. It retains the local record and source identity, preventing reimport, late network results, or stale editors from bringing it back. It does not delete the engine's history or linked entries.
- Edit remains in the answer's existing context menu.
- A failed save keeps the response visible and reports the failure.

The existing `Reminder.status` and `completedAt` fields hold this state. Existing archives default to active without a migration. All persistence uses the archive's atomic write; published state changes only after a successful write.

## Acceptance checks

`CowboyFoundationTests` exercises completed/reopened pinned answers, exact source bytes and notes, soft deletion from both active and completed states, import and refresh, stale editors, unrelated server identities, linked writing, failed writes, and all 168 bundled conversations.

`CowboyFoundationUITests/testDoneDeleteAndReopenSurviveRelaunchWithoutReturningToTheCarousel` exercises the actual swipe controls, collapsed count, completed answer, reopen, two restarts, and both active-list and carousel removal. `testCompletedResponseCanBeDeletedFromItsMenu` covers deleting from the completed row's context menu and restarting. The existing multi-pin/relaunch and real offline-history UI tests remain regression checks.

Simulator checks use the isolated `CowboyAI-UI-Tests` directory. Adam performs the phone Run/install himself.

## Verified result — October 14, 2026

All 20 selected tests passed on the iPhone 17 Pro Max simulator (16 foundation tests and 4 interface tests). Screenshots of the swipe controls, expanded Completed list, original answer, and reopened pinned card were inspected. The completed row now keeps Reopen's accessibility label separate from the answer title.

Result bundle: `/Users/adamblair/Library/Developer/XcodeBuildMCP/workspaces/Cowboyai-89a3407fd2e7/result-bundles/test_sim_2026-10-14T20-33-18-137Z_pid35770_593e59e6.xcresult`.

The bundled history is unchanged: SHA-256 `f9141d23d05e43d9010a88256271848839b2faebd005ac82fdb49575f4d7192f`. The phone project remains `CowboyAITrial.xcodeproj`, scheme `CowboyAITrial`. Physical-phone behavior is **UNVERIFIED** for this change; the remaining check is Adam's next Run and swipe on the phone.
