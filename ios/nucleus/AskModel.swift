import Foundation
import Observation

@MainActor
@Observable
final class AskModel {
    var question = UserDefaults.standard.string(forKey: "nucleus.draft") ?? "" {
        didSet {
            // the draft is kept the moment it is typed, so nothing he wrote is ever lost to a reload
            UserDefaults.standard.set(question, forKey: "nucleus.draft")
            print("nucleus: question now \(question.count) chars")
        }
    }
    /// The form he picked, from his SAVY themes (Themes.swift), and what he wrote in it. Kept the moment it is
    /// typed, like the question. Adam, 2026-10-07: "there can be choices of the questions that I have."
    var themeID: String? = UserDefaults.standard.string(forKey: "nucleus.theme") {
        didSet { UserDefaults.standard.set(themeID, forKey: "nucleus.theme") }
    }
    var themeAnswers: [String: [String]] = {
        guard let data = UserDefaults.standard.data(forKey: "nucleus.themeAnswers") else { return [:] }
        return (try? JSONDecoder().decode([String: [String]].self, from: data)) ?? [:]
    }() {
        didSet { UserDefaults.standard.set(try? JSONEncoder().encode(themeAnswers), forKey: "nucleus.themeAnswers") }
    }
    var theme: PostTheme? { PostThemeCatalog.theme(id: themeID) }

    func selectTheme(_ id: String?) {
        themeID = id
        if let id, themeAnswers[id] == nil, let picked = PostThemeCatalog.theme(id: id) {
            themeAnswers[id] = picked.prefilledAnswers
        }
    }

    /// The fields of the picked theme: the question on the first line, his answer under it (SAVY's Decide boxes).
    var themeFields: [String] {
        guard let theme else { return [] }
        return themeAnswers[theme.id] ?? theme.prefilledAnswers
    }

    func setThemeField(_ text: String, at index: Int) {
        guard let theme else { return }
        var values = themeFields
        while values.count <= index { values.append("") }
        values[index] = text
        themeAnswers[theme.id] = values
    }

    /// His answers inside the fields, prompts stripped, in field order.
    var themeAnswerTexts: [String] {
        guard let theme else { return [] }
        return themeFields.enumerated().map { index, field in
            PostTheme.answerText(in: field, originalPrompt: theme.questions.indices.contains(index) ? theme.questions[index].prompt : nil)
        }
    }

    /// What the Mac reads: his question, then each field he answered, the prompt on the first line as he saw it.
    var entryText: String {
        var parts = [question.trimmingCharacters(in: .whitespacesAndNewlines)].filter { !$0.isEmpty }
        if let theme {
            for (index, answer) in themeAnswerTexts.enumerated() where !answer.isEmpty {
                let prompt = theme.questions.indices.contains(index) ? theme.questions[index].prompt : ""
                parts.append(prompt.isEmpty ? answer : prompt + "\n" + answer)
            }
        }
        return parts.joined(separator: "\n\n")
    }

    var canAsk: Bool { !entryText.isEmpty }

    private var themePayload: [String: Any]? {
        guard let theme else { return nil }
        let fields: [[String: Any]] = themeAnswerTexts.enumerated().map { index, answer in
            let q = theme.questions.indices.contains(index) ? theme.questions[index] : nil
            return ["prompt": q?.prompt ?? "", "symbol": q?.symbol ?? "text.bubble", "answer": answer]
        }
        return ["id": theme.id, "name": theme.name, "question": question.trimmingCharacters(in: .whitespacesAndNewlines), "fields": fields]
    }

    var current: AskResponse?
    var recent: [RecentItem] = []
    var working = false
    var problem: String?
    var thumbs: [String: Int] = [:]      // "word|record" -> 1 up, 0 down

    static let stepNames = ["1 question in", "2 dictionary reads it", "3 your phrases found", "4 nucleus read whole",
                            "5 one model call", "6 the gate", "7 answer out"]

    init() { print("nucleus: model created") }

    func ask() async {
        let text = entryText
        print("nucleus: ask() with \(text.count) chars, theme=\(themeID ?? "none"), working=\(working)")
        guard !text.isEmpty, !working else { return }
        working = true; problem = nil; current = nil; thumbs = [:]; explanationThumb = nil
        do {
            let payload = themePayload.map { try? JSONSerialization.data(withJSONObject: $0) } ?? nil
            let id = try await NucleusAPI.ask(text, themeData: payload)
            while true {
                let status = try await NucleusAPI.status(id)
                current = status
                // the rows show as soon as they exist; keep polling until the meaning under the first line is written
                if status.answer != nil && (status.explanation?.status ?? "none") != "pending" { break }
                try await Task.sleep(nanoseconds: 700_000_000)
            }
            await loadRecent()
            // Adam, 2026-10-07: "The last answer sits in entry blank for some reason. make sure that doesn't happen
            // again." What was sent is the Mac's now; the entry page starts blank for the next one.
            question = ""
            if let theme { themeAnswers[theme.id] = nil }
        } catch {
            problem = "The Mac did not answer. \(error.localizedDescription)"
        }
        working = false
    }

    func open(_ id: String) async {
        print("nucleus: open(\(id))")
        do {
            current = try await NucleusAPI.status(id)
            thumbs = [:]; explanationThumb = nil
        } catch {
            problem = "The Mac did not answer. \(error.localizedDescription)"
        }
    }

    /// The past answers under one of his three lines.
    func recent(in category: Category) -> [RecentItem] {
        recent.filter { $0.answer == category.rawValue }
    }

    func loadRecent() async {
        recent = (try? await NucleusAPI.recent()) ?? []
        // A draft that is word for word a question already in his Earlier list is not unsent writing; it is the
        // last question, left in the entry by the build before 430b30a. Adam, 2026-10-07: "It's still there."
        let draft = question.trimmingCharacters(in: .whitespacesAndNewlines)
        if !draft.isEmpty, recent.contains(where: { $0.question.trimmingCharacters(in: .whitespacesAndNewlines) == draft }) {
            question = ""
        }
    }

    func thumb(_ row: AskResponse.Row, up: Bool) async {
        thumbs["\(row.word)|\(row.record)"] = up ? 1 : 0
        try? await NucleusAPI.thumb(word: row.word, record: row.record, quote: row.quote, up: up)
    }

    var explanationThumb: Int?

    /// Adam, 2026-10-03: the middle response "will be followed by requesting more information, which will be logged
    /// and then analyzed by the LLM during the night run." What he is typing, kept by question until it is logged.
    var moreDrafts: [String: String] = [:]
    var loggingMore = false

    func logMore() async {
        guard let id = current?.question.id, !loggingMore else { return }
        let text = (moreDrafts[id] ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        loggingMore = true
        do {
            try await NucleusAPI.more(questionID: id, text: text)
            current = try await NucleusAPI.status(id)
            moreDrafts[id] = nil
        } catch {
            problem = "The Mac did not answer. \(error.localizedDescription)"
        }
        loggingMore = false
    }

    func thumbExplanation(up: Bool) async {
        guard let id = current?.question.id else { return }
        explanationThumb = up ? 1 : 0
        try? await NucleusAPI.thumbExplanation(questionID: id, up: up)
    }

    func thumbState(_ row: AskResponse.Row) -> Int? {
        thumbs["\(row.word)|\(row.record)"] ?? row.thumb
    }
}
