import Foundation

/// Exact writing from the visible entry form, sent through the existing Ask API.
/// Empty template prompts alone are not a question or personal evidence.
struct EntryQuestion {
    let text: String
    let theme: AskResponse.Theme

    init(entry: Reminder, draft: PostEntryDraft, subtasks: [Subtask]) {
        var parts: [String] = []
        if !entry.title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            parts.append("What do I want?\n" + entry.title)
        }
        var fields: [AskResponse.Theme.Field] = []
        for (index, writing) in draft.answers.enumerated() {
            let original = draft.theme.questions.indices.contains(index) ? draft.theme.questions[index] : nil
            let prompt: String
            let answer: String
            if let original, writing == original.prompt || writing.hasPrefix(original.prompt + "\n") {
                prompt = original.prompt
                answer = writing == prompt ? "" : String(writing.dropFirst(prompt.count + 1))
            } else {
                let lines = writing.split(separator: "\n", maxSplits: 1, omittingEmptySubsequences: false)
                prompt = lines.first.map(String.init) ?? ""
                answer = lines.count > 1 ? String(lines[1]) : ""
            }
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
