# CowboyAI recovery — 13 October 2026

Physical phone: never accessed. Final physical-device build belongs to Adam.

Source base: 5d307ba7eb90dc7f4278e853087167032e8a0841. Original nucleus main and cowboyai-savy-native worktree were preserved.

## Verified
- Simulator build succeeds for iPhone 18 Pro Max / iOS 27 on isolated CowboyAI-Recovery simulator.
- 14 of 14 persistence and UI tests passed in /tmp/CowboyAI-Recovery-Tests-2.xcresult: chronological history, actual explanation previews, pinned SAVY carousel, swipe navigation, reminder origin reopen, linked-action persistence after relaunch, schedule editor/calendar.
- After FAB change, calendar creation test passed again (/tmp/CowboyAI-Recovery-FAB-2.xcresult).
- Final FAB test passed (/tmp/CowboyAI-Recovery-FAB-3.xcresult): tap opens all four arc choices, tap closes, Question opens real question field and Ask action.
- FAB copied from SAVY-iOS/SAVY/SavyShellComponents.swift: original spring constants, four arc positions, drag target math, highlight, haptics and dimmed dismissal. SAVY Post maps to CowboyAI Question.
- Existing live Nucleus service returned 91 recent conversations and complete latest response with later-context sections and 119 evidence rows. Answer engine, ontology and graph were not changed.

## Actual limits
The simulator checks use isolated fixtures for repeatable UI tests. Physical-device behavior and actual notification/calendar delivery were not tested. Drag selection code matches SAVY, but only tap selection was exercised automatically. The live answer path was subsequently verified at Adam's request; see the follow-up below.

## Adam, verbatim, this chat
“that does not look like the SAVY app carousel.  You have 8 minutes”
“better.  fix the FAB.  The animation is wrong. Check SAVY.  you have 5 minutes”

## Open for final build
/Users/adamblair/.codex/worktrees/cowboyai-recovery-20261013/ios/nucleus.xcodeproj
Scheme: nucleus (display name Cowboyai).

## Follow-up: live Nucleus verification, 2026-10-13 7:49 pm PDT

Adam, verbatim: “Check that this corrected version is using Nucleus with the updated ontology and knowledge graph. Use the simulator only. Do not access my phone.”

Verified corrected app commit bb0123d on simulator D2BC1BBD-8375-4225-A9BE-F50C1D65E023 with real requests, no UI fixtures and no endpoint override. The app uses the normal Nucleus endpoint on port 8766. Physical phone never accessed.

- What is FLOW? → aligned and why; visible in simulator, 46 evidence rows, 734 accepted originals checked, zero model calls.
- What are reasons I would avoid going to the doctor? → middle answer; visible in simulator. Engine explanation explicitly used the current Health and Belief ontology definitions and an accepted record common to both domains. Zero model calls.
- Both persisted answers contain exactly the SHA-256 fingerprint of the current complete Nucleus input bundle: accepted graph, decision ledger, connection shapes, BFO bridge, canonical meanings and routes.
- Graph fingerprint also matches the latest successful automatic sync (7:42 pm PDT); 13,909 triples. Neither check created a graph relationship.
- Runtime engine identifies as 25d3c8a954ffb98d6eb361075c41d8b8415d8345. All eight reported loaded engine module hashes match its source files.
- Complete raw answers, source fingerprints and simulator screenshot accompany this report. No application or engine code was changed for this verification.

## Follow-up: actual SAVY card code, 2026-10-13 8:09 pm PDT

Read the current SAVY `RootView.swift`, `ReminderStore.swift`,
`SavyReminderScreens.swift` and `SavyCarouselDetails.swift` together at commit
87f2b8c535fd7069d9748159a78d3770247f1a2c. SAVY's home feed selects pinned
entries. CowboyAI was adding unpinned conversations to that feed, causing
them to use SAVY's compact title-only layout. CowboyAI now keeps pinned
question/response pairs in the cream carousel and keeps other conversations
available under Recent responses. No saved pin or metadata is invented.

Removed three inherited medium-detail exceptions from the port. The shared
card implementation from `enum SavyCardDetail` through the end of
`SavyReminderBandCard` now matches SAVY character for character (SHA-256
2c9e459f483d896a87c94909ab8d57a01a8026540b49743392618da4df92f4c4).
The complete carousel-details implementation after its import also matches
SAVY. CowboyAI's approved maroon palette remains in its own theme.

All three targeted UI tests passed in
`/tmp/CowboyAI-Savy-Cards-Final.xcresult` on simulator
D2BC1BBD-8375-4225-A9BE-F50C1D65E023. The simulator build also succeeded.

- Carousel: cream cards measure 282 × 182 points, all four saved metadata
  pills appear, and swiping opens the correct paired conversation.
- Unpin removes the pair from the carousel; pinning it again from Recent
  restores the same height and metadata.
- Reminders and Actions: the long leading pinned card expands above the
  186-point second pinned card; an unpinned card is under 60 points high.
  Saved pattern, priority, Lift and notes remain visible on the large card.

Inspected the exported simulator screenshots: white leading card, red second
card, sand compact card, and cream carousel with bottom-left metadata pills.
Screenshots use isolated synthetic test entries, never Adam's phone data:

- [Home carousel](carousel-metadata-simulator.png)
- [Reminders](reminders-card-sizes-simulator.png)
- [Actions](actions-card-sizes-simulator.png)

The first hierarchy-test attempt counted inherited text identifiers rather
than whole cards. Inspection showed the extra match was the second card's
metadata line; the test now measures SAVY's existing full-card gesture
surfaces. No assertion was removed to conceal a layout defect.

No engine, ontology, graph, endpoint, normal app data, or SAVY file was changed.
No physical phone was accessed. Adam retains the final physical-device build.
