# Composer example-question regressions

Run from the repository root with Swift 6 on a Mac or Linux:

```sh
bash ios/tests/run-composer-tests.sh
```

`SWIFTC` may point to a particular Swift compiler. The runner builds the production
`AskModel.swift`, `Themes.swift`, and `QuestionExamples.swift`. It also uses the actual
response types from `API.swift` and the Foundation-only `Category` definition from
`SavyShell.swift`. Only the network transport is replaced: every attempted API call is
recorded and fails. No live service, AI call, or personal records are needed.

Each of the 12 cases has a fresh `UserDefaults` suite, removed afterward. Tests never
use the installed app's preferences. They cover all six selections, complete questions,
verbatim draft preservation, repeated selection, persistence after reopening, active
and inactive theme answers, unchanged answer/feedback state, unknown IDs, and selection
while an answer is in progress. Every case also checks that no API call occurred.

The production initializer still defaults to `UserDefaults.standard`, with the same
three saved keys. The injectable preferences store exists to test that behavior in isolation.

## Verification on October 8, 2026

Base: `f9e326dcfcf996c959f9ec65d169d0c246690696` on `main`.
Environment: Linux x86_64, Swift 6.0.3, Python 3.12.14.

| Check | Exact result |
| --- | --- |
| `bash ios/tests/run-composer-tests.sh` with Swift 6.0.3 | 12 passed, 0 failed; exit 0 |
| Swift parser on `ComposerView.swift` | Passed; exit 0. Syntax only; no SwiftUI type checking. |
| `plutil -lint -- ios/nucleus.xcodeproj/project.pbxproj` | OK; exit 0 |
| `bash -n ios/tests/run-composer-tests.sh` | Passed; exit 0 |
| `git diff --check` | Passed; exit 0 |
| `.venv/bin/python -m pytest tests/test_theme.py -q` | 3 passed, 0 failed; exit 0 |
| Full Python suite on unchanged base and after this change | Both: 66 passed, 23 failed, 22 errors, 5 skipped; exit 1 |
| Complete Xcode/iOS build, simulator UI, physical iPhone | Not run; no Xcode, iOS SDK, simulator, or physical device in this workspace |

The full Python suite depends on Mac-resident ontology and dictionary files, including
`/Users/adamblair/Documents/Main/Ontology/accepted/accepted-graph.ttl`, which are absent
here. Its non-passing baseline is not claimed as a green check. No Python engine,
night job, or morning-review code is changed.

## Example sources

The inquiries are proposed wording, not quotes from or conclusions about anyone's records.
The first inquiry preserves the wording proposed in this task. The rest use current SAVY
themes and the finished meanings in
[adams-language/meanings.txt](https://github.com/dblaira/adams-language/blob/518a3bb6570b3a45098f3c9728b266b9bb716deb/meanings.txt).

| Relationship to explore | Existing theme | Finished meaning |
| --- | --- | --- |
| Conditions that repeat when something draws me in | Pattern Recognition | PULLED |
| Differences between focused and forced activity | Before / After | FLOW, PUSHED |
| Agreement or conflict between choices and stated importance | The Decision | VALUE |
| Small changes associated with large results | Quick Hack or Shortcut | LEVERAGE |
| Connections across unexpected uses | Alternative Approaches | CREATIVITY |
| Repeated relationships and evidence still needed | There is some relationship, but not enough to justify causation. | DISCERN |

The September 6 request for general examples is in
[ledger.md](https://drive.google.com/file/d/1LjUB9ieHJiRQg5pr48SQ3CmRXAqqrrNr/view).
[Speed Store post #178](https://app.notion.com/p/3f11a92c1dd681c5b31ff32069403341)
describes the related vocabulary gap; its developed text is marked as a Codex proposal.
No dictionary, ledger, or Notion content is changed by this feature.

## What still needs an Apple platform

These are model tests, not rendered UI tests. A Mac with Xcode and an iOS 26 SDK is
needed to build the complete SwiftUI app and check the interface on a simulator or iPhone.
The composer should be checked with an empty question, a persisted multiline draft,
edited Decide prompts and answers, large Dynamic Type, and VoiceOver. Selecting an
example should collapse the list, leave the complete question editable, retain the theme
and its answers, and send no request until Ask is tapped. Opening and closing the
examples without choosing one should leave all writing untouched.

The API, request/polling path, immediate-response engine, overnight processing, and
morning review are outside this change.
