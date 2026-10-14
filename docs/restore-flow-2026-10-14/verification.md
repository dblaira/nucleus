# CowboyAI flow restoration — verified October 14, 2026

The original question flow and full history carousel are restored. The added Pin / Details / Create toolbar is removed. Approved SAVY styling, metadata, tabs, card hierarchy and linked entries remain.

## Source and running build

- Source baseline: `3437a012d550bc6174b5110ef6a4b3eb4ea63bdc`.
- Verified implementation: `f598d835a33edfb8782e8cf9ae1c83871747217f` on `codex/cowboyai-restore-flow` in `dblaira/nucleus`.
- Project: `/Users/adamblair/.codex/worktrees/cowboyai-restore-flow/ios/nucleus.xcodeproj`.
- A normal Debug build was installed and launched after committing the implementation. Later commits in this branch add evidence only.
- Simulator: `CowboyAI-Recovery`, `D2BC1BBD-8375-4225-A9BE-F50C1D65E023`; bundle `com.adamblair.nucleus`.
- The physical phone was not accessed or changed.

Both installed executable files match the final build byte for byte:

| Binary | SHA-256, built and installed |
| --- | --- |
| nucleus | `44fb5866ac8167ee1cffc26bbe828bd72248837645396dc22990c76fc1096af4` |
| nucleus.debug.dylib | `e1e6dbc7c29223fd3b8bde9b7265e8e69a9922af7630bfbaea36c29cb1c847a4` |

## Observable result

The running app was inspected visually with its normal saved conversations. The cream carousel occupies the original top position, includes unpinned history, and retains metadata. Pinned conversations come first. The Now lightning button opens the existing Theme / Decide / question / Ask composer directly. The same saved How-To used in the before comparison opens with the white question card followed by the maroon answer, without the added toolbar.

Touch and hold a conversation card for Pin/Unpin, Edit, Reminder, Action or Calendar event. The card supplies its own question/answer snapshot to linked entries. These entries retain their source and reopen it after relaunch. Other tabs retain the SAVY radial menu; its labels are now readable in white. The Reminders and Actions screens retain their large white first pin, smaller later pins and compact unpinned cards.

Actual simulator PNGs and the local gallery are at:

`/Users/adamblair/.codex/visualizations/2026/10/14/01a13b35-d823-7d12-8533-fc906c3ec11f/cowboyai-restoration/`

| Screenshot | Source |
| --- | --- |
| restored-home.png | Normal saved history, final installed build |
| restored-question-empty.png | Direct lightning tap, original composer, final installed build |
| restored-answer.png | Same saved How-To as the before comparison, final installed build |
| restored-form.png | Actual UI-test How-To form using Adam's original example; keyboard visible |
| verified-unpinned.png | Actual UI-test carousel with no pinned conversations |
| verified-reminders.png | Actual UI-test sample reminders and SAVY card hierarchy |
| verified-actions.png | Actual UI-test sample actions and SAVY card hierarchy |
| verified-menu.png | Actual UI-test radial menu on the Actions tab |
| verified-schedule.png | Actual UI-test native schedule editor |

The screenshots were inspected directly. Test screenshots use labelled Sample entries in the existing isolated UI-test storage. They are not normal saved user entries. None of the screenshots are mockups or image edits.

## Verification

**23 passed, 0 failed, 0 skipped:** 11 persistence unit tests and 12 UI tests.

The UI checks cover direct composition; the original How-To example and live FLOW evidence; dictionary retrieval and saving; horizontal carousel navigation; unpinned history; pinned-first order and unpin preservation; saved metadata; linked-action creation, persistence and source reopening; reminder/action card hierarchy; schedule/calendar; the SAVY radial menu; and preserving writing through connection failure and retry.

- Result bundle: `/Users/adamblair/Library/Developer/CowboyAI-RestoreFlow/restoration-verified.xcresult`.
- Test log: `/Users/adamblair/Library/Developer/XcodeBuildMCP/workspaces/Cowboyai-89a3407fd2e7/logs/test_sim_2026-10-14T16-48-16-497Z_pid34973_c7f9834e.log`.
- Final build log: `/Users/adamblair/Library/Developer/XcodeBuildMCP/workspaces/Cowboyai-89a3407fd2e7/logs/build_run_sim_2026-10-14T16-53-48-527Z_pid34973_87419364.log`.
- `git diff --check` passed.

An earlier UI run exposed a parent accessibility identifier overriding the question text identifier. That parent identifier was removed; the question assertions were retained. The complete suite then passed. Live Ask checks use the existing local engine and save their resulting conversations through its normal path.

## Preservation

The complete normal simulator data container was copied before installation; all 104 files matched SHA-256 hashes. The backup and manifest remain beside the gallery as `simulator-data-before/` and `backup-sha256.json`. There was no database replacement, reset, migration or deletion.

The engine, original ComposerView, Theme, ReminderStore, ConversationArchive and SAVY source were not changed. Existing unrelated work in nucleus main and the older recovery checkout was preserved. The exact authorization was appended to CowboyAI's instruction ledger separately.
