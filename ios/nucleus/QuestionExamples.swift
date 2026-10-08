import Foundation

/// Static inquiries, not findings about anyone's records. Theme references describe the kind of
/// relationship being explored; selecting an example never selects or resets a SAVY theme.
struct QuestionExample: Identifiable, Equatable {
    let id: String
    let title: String
    let question: String
    let themeID: String

    var theme: PostTheme? { PostThemeCatalog.theme(id: themeID) }
}

/// Proposed wording grounded in Adam's finished meanings (adams-language/meanings.txt) and
/// existing SAVY themes. This catalog needs no model call, records, or network connection.
enum QuestionExampleCatalog {
    static let examples: [QuestionExample] = [
        // PULLED: interest without an obsessive desire to feel interested.
        QuestionExample(
            id: "follow-the-pull",
            title: "What draws me in?",
            question: "When did I feel pulled toward something, and what conditions kept repeating?",
            themeID: "pattern-recognition"
        ),
        // FLOW: full attention on one activity. PUSHED: borrowed motivation rather than interest.
        QuestionExample(
            id: "flow-or-push",
            title: "What changed?",
            question: "When have I found flow, and what changed between those times and the times I felt pushed?",
            themeID: "before-after"
        ),
        // VALUE: what naturally feels important, rather than an objective judgment.
        QuestionExample(
            id: "choices-and-value",
            title: "Do my choices match?",
            question: "Where do my choices match what I say has value, and where do they conflict?",
            themeID: "the-decision"
        ),
        // LEVERAGE: the small percentage or single idea that creates most of a result.
        QuestionExample(
            id: "small-change-big-result",
            title: "What made the biggest difference?",
            question: "Which small changes have created the most leverage for me, and what did those situations have in common?",
            themeID: "quick-hack-or-shortcut"
        ),
        // CREATIVITY: using a tool or term for its unintended original purpose.
        QuestionExample(
            id: "unexpected-use",
            title: "What connects different ideas?",
            question: "What examples of creativity in my records use something for an unintended purpose, and what connects them?",
            themeID: "alternative-approaches"
        ),
        // DISCERN: separating signal from noise and testing what has and has not worked.
        QuestionExample(
            id: "pattern-or-coincidence",
            title: "Pattern or coincidence?",
            question: "Which relationships repeat in my records, and what evidence would help me discern a dependable pattern from a coincidence?",
            themeID: "some-relationship"
        ),
    ]

    static func example(id: String) -> QuestionExample? {
        examples.first { $0.id == id }
    }
}
