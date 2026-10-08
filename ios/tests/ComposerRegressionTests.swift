import Foundation

/// A portable Swift runner because this repository has no iOS unit-test target. Each case uses
/// its own preferences suite; it never reads or writes the installed Cowboyai app's draft.
@main
@MainActor
struct ComposerRegressionTests {
    private struct Failure: Error, CustomStringConvertible {
        let description: String
    }

    private static func expect(_ condition: @autoclosure () -> Bool, _ message: String) throws {
        if !condition() { throw Failure(description: message) }
    }

    static func main() async {
        let example = QuestionExampleCatalog.examples[0]
        let other = QuestionExampleCatalog.examples[1]
        let tests: [(String, @MainActor (AskModel, UserDefaults) throws -> Void)] = [
            ("catalog has complete, distinct questions tied to existing themes", { _, _ in
                let examples = QuestionExampleCatalog.examples
                try expect((4...8).contains(examples.count), "Keep the starter collection small and varied")
                try expect(Set(examples.map(\.id)).count == examples.count, "Example IDs must be distinct")
                try expect(Set(examples.map(\.question)).count == examples.count, "Questions must be distinct")
                for item in examples {
                    try expect(!item.title.isEmpty && item.question.hasSuffix("?"), "An example must be ready to ask")
                    try expect(item.theme != nil, "An example must reference a current SAVY theme")
                }
            }),
            ("every example fills an empty question and is saved immediately", { model, defaults in
                for item in QuestionExampleCatalog.examples {
                    model.question = ""
                    try expect(model.selectExample(item.id), "An empty question should accept the example")
                    try expect(model.question == item.question && model.canAsk, "Use the complete inquiry")
                    try expect(defaults.string(forKey: "nucleus.draft") == item.question, "Persist the selection")
                }
            }),
            ("existing Unicode, multiline text and trailing spaces stay verbatim", { model, defaults in
                let original = "  My question — café ☀️\nAnother line.  \n"
                model.question = original
                model.selectExample(example.id)
                try expect(model.question == original + "\n\n" + example.question, "Append without rewriting")
                try expect(defaults.string(forKey: "nucleus.draft") == model.question, "Save both pieces")
            }),
            ("whitespace-only writing is preserved too", { model, _ in
                model.question = " \n\t "
                model.selectExample(example.id)
                try expect(model.question == " \n\t \n\n" + example.question, "Do not trim an existing draft")
            }),
            ("selecting the same example twice does not duplicate it", { model, _ in
                model.selectExample(example.id)
                try expect(!model.selectExample(example.id) && model.question == example.question, "Do not duplicate")
                model.question = "My writing"
                model.selectExample(example.id)
                let once = model.question
                try expect(!model.selectExample(example.id) && model.question == once, "Do not duplicate an appended example")
            }),
            ("different examples retain the original writing and order", { model, _ in
                model.question = "My writing"
                model.selectExample(example.id)
                model.selectExample(other.id)
                try expect(model.question == "My writing\n\n" + example.question + "\n\n" + other.question,
                           "Retain the whole draft")
            }),
            ("selection preserves every SAVY theme and active and inactive answers", { model, defaults in
                model.selectTheme("story-arc")
                model.setThemeField("An edited prompt\nMy inactive answer.  ", at: 0)
                for theme in PostThemeCatalog.themes {
                    model.selectTheme(theme.id)
                    model.setThemeField("An edited prompt\nMy active answer.  ", at: 0)
                    let savedAnswers = model.themeAnswers
                    let savedData = defaults.data(forKey: "nucleus.themeAnswers")
                    let fields = model.themeFields
                    model.question = ""
                    model.selectExample(example.id)
                    try expect(model.themeID == theme.id && model.themeFields == fields, "Keep the selected theme")
                    try expect(model.themeAnswers == savedAnswers, "Keep all themes' answers")
                    try expect(defaults.data(forKey: "nucleus.themeAnswers") == savedData, "Do not rewrite saved answers")
                }
            }),
            ("a selected example and later edits survive a new model", { model, defaults in
                model.selectTheme("before-after")
                model.setThemeField("What changed?\nMy answer", at: 1)
                model.question = "My earlier draft"
                model.selectExample(example.id)
                model.question += "\nMy added detail."
                let reopened = AskModel(defaults: defaults)
                try expect(reopened.question == model.question, "Reopen the full draft and later edits")
                try expect(reopened.themeID == model.themeID && reopened.themeAnswers == model.themeAnswers,
                           "Reopen the theme and its answers")
            }),
            ("previously stored preferences load without resetting writing", { _, defaults in
                let answers = ["mental-model": ["Edited prompt\nSaved answer."]]
                defaults.set("  Existing draft\n", forKey: "nucleus.draft")
                defaults.set("mental-model", forKey: "nucleus.theme")
                defaults.set(try JSONEncoder().encode(answers), forKey: "nucleus.themeAnswers")
                let reopened = AskModel(defaults: defaults)
                _ = QuestionExampleCatalog.examples
                try expect(reopened.question == "  Existing draft\n", "Catalog availability must not change a draft")
                try expect(reopened.themeID == "mental-model" && reopened.themeAnswers == answers, "Load existing preferences")
            }),
            ("unknown example IDs leave the draft untouched", { model, defaults in
                model.question = "Keep me"
                try expect(!model.selectExample("missing-example"), "Ignore unknown IDs")
                try expect(model.question == "Keep me" && defaults.string(forKey: "nucleus.draft") == "Keep me",
                           "Do not change saved text")
            }),
            ("selection cannot change a question while an answer is in progress", { model, defaults in
                model.question = "In progress"
                model.working = true
                try expect(!model.selectExample(example.id), "Ignore selections while working")
                try expect(model.question == "In progress" && defaults.string(forKey: "nucleus.draft") == "In progress",
                           "Preserve the in-progress question")
                try expect(model.working, "Do not reset answer state")
            }),
            ("selection preserves results, feedback and more-information drafts", { model, _ in
                let json = #"{"question":{"id":"q1","question":"An earlier question"},"steps":[],"phrases":[]}"#
                model.current = try JSONDecoder().decode(AskResponse.self, from: Data(json.utf8))
                model.recent = [RecentItem(id: "q1", question: "An earlier question", status: "done", answer: "aligned", finished: 1)]
                model.problem = "Existing message"
                model.thumbs = ["FLOW|r1": 1]
                model.explanationThumb = 1
                model.moreDrafts = ["q1": "My unsent detail"]
                model.selectExample(example.id)
                try expect(!model.working && model.current?.question.id == "q1", "Keep results without asking")
                try expect(model.recent.count == 1 && model.recent[0].id == "q1", "Keep earlier answers")
                try expect(model.problem == "Existing message" && model.thumbs == ["FLOW|r1": 1]
                           && model.explanationThumb == 1, "Keep feedback and message state")
                try expect(model.moreDrafts == ["q1": "My unsent detail"], "Keep more-information writing")
            }),
        ]

        var passed = 0
        var failed = 0
        for (name, test) in tests {
            let suite = "nucleus.composer-tests." + UUID().uuidString
            let defaults = UserDefaults(suiteName: suite)!
            defaults.removePersistentDomain(forName: suite)
            NucleusAPI.calls = []
            do {
                try test(AskModel(defaults: defaults), defaults)
                // Give any mistakenly spawned request a chance to reach the transport double.
                await Task.yield()
                await Task.yield()
                try expect(NucleusAPI.calls.isEmpty, "Example selection made an API call: \(NucleusAPI.calls)")
                print("PASS: \(name)")
                passed += 1
            } catch {
                print("FAIL: \(name): \(error)")
                failed += 1
            }
            defaults.removePersistentDomain(forName: suite)
        }
        print("Composer regressions: \(passed) passed, \(failed) failed")
        exit(failed == 0 ? 0 : 1)
    }
}
