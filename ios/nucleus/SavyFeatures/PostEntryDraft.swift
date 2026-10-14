import Foundation

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

