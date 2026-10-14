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
The simulator checks use isolated fixtures for repeatable UI tests. Physical-device behavior and actual notification/calendar delivery were not tested. Drag selection code matches SAVY, but only tap selection was exercised automatically. The final live question request was not exercised on this new build before the time limit.

## Adam, verbatim, this chat
“that does not look like the SAVY app carousel.  You have 8 minutes”
“better.  fix the FAB.  The animation is wrong. Check SAVY.  you have 5 minutes”

## Open for final build
/Users/adamblair/.codex/worktrees/cowboyai-recovery-20261013/ios/nucleus.xcodeproj
Scheme: nucleus (display name Cowboyai).
