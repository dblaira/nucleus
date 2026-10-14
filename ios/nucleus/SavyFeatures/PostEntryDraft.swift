import Foundation

/// Exact writing from the visible entry form, sent through the existing Ask API.
/// Empty template prompts alone are not a question or personal evidence.
struct EntryQuestion {
    let text: String
    let theme: AskResponse.Theme

    init(entry: Reminder, draft: PostEntryDraft, subtasks: [Subtask]) {
        var parts: [String] = []
        if !entry.title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { parts.append(entry.title) }
        var fields: [AskResponse.Theme.Field] = []
        for (index, writing) in draft.answers.enumerated() {
            let original = draft.theme.questions.indices.contains(index) ? draft.theme.questions[index] : nil
            let lines = writing.split(separator: "\n", maxSplits: 1, omittingEmptySubsequences: false)
            let prompt = lines.first.map(String.init) ?? original?.prompt ?? ""
            let answer = lines.count > 1 ? String(lines[1]) : ""
            fields.append(.init(prompt: prompt, symbol: original?.symbol, answer: answer, night: nil))
            if !answer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || prompt != original?.prompt {
                if !writing.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { parts.append(writing) }
            }
        }
        let details = [("When I am...I like to", entry.whenIAm ?? ""), ("Done looks like...", entry.outcome),
                       ("Notes", entry.notes), ("Link", entry.url)]
            + subtasks.filter { !$0.title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }.map { ("Step", $0.title) }
        for (prompt, answer) in details where !answer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            fields.append(.init(prompt: prompt, symbol: "text.bubble", answer: answer, night: nil))
            parts.append(prompt + "\n" + answer)
        }
        text = parts.joined(separator: "\n\n")
        theme = .init(id: draft.theme.id, name: draft.theme.name, question: entry.title, fields: fields)
    }
}

struct PostEntryDraft: Codable, Equatable {
    private(set) var themeID: String
    private var answersByTheme: [String: [String]]
    private let fixedTheme: PostTheme?

    init(entry: Reminder, fixedTheme: PostTheme? = nil) {
        self.fixedTheme = fixedTheme
        let theme = fixedTheme ?? PostThemeCatalog.theme(id: entry.postThemeID) ?? PostThemeCatalog.defaultTheme
        themeID = theme.id
        answersByTheme = [theme.id: theme.questionAndAnswers(
            from: entry.postAnswers,
            containQuestions: entry.postAnswersContainQuestions == true
        )]
    }

    var theme: PostTheme {
        fixedTheme ?? PostThemeCatalog.theme(id: themeID) ?? PostThemeCatalog.defaultTheme
    }

    var answers: [String] { answersByTheme[themeID] ?? theme.prefilledAnswers }

    mutating func selectTheme(_ id: String) {
        guard fixedTheme == nil else { return }
        guard let selected = PostThemeCatalog.theme(id: id) else { return }
        themeID = selected.id
        if answersByTheme[id] == nil { answersByTheme[id] = selected.prefilledAnswers }
    }

    mutating func setAnswer(_ text: String, at index: Int) {
        guard index >= 0 else { return }
        var values = answers
        while values.count <= index { values.append("") }
        values[index] = text
        answersByTheme[themeID] = values
    }

    /// Explicit Save retains the untouched template as well as any entered answers.
    func apply(to entry: inout Reminder) {
        entry.postThemeID = theme.id
        entry.postThemeName = theme.name
        entry.postAnswers = answers
        entry.postAnswersContainQuestions = true
    }

    /// Opening a template or choosing another one does not create an autosaved post.
    /// A changed question is user content too; its original wording is only a starting point.
    var hasUserContent: Bool {
        answers.enumerated().contains { index, value in
            let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !trimmed.isEmpty else { return false }
            return !theme.questions.indices.contains(index) || trimmed != theme.questions[index].prompt
        }
    }
}

