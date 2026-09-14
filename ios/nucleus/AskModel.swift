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
    var current: AskResponse?
    var recent: [RecentItem] = []
    var working = false
    var problem: String?
    var thumbs: [String: Int] = [:]      // "word|record" -> 1 up, 0 down

    static let stepNames = ["1 question in", "2 dictionary reads it", "3 your phrases found", "4 nucleus read whole",
                            "5 one model call", "6 the gate", "7 answer out"]

    init() { print("nucleus: model created") }

    func ask() async {
        let text = question.trimmingCharacters(in: .whitespacesAndNewlines)
        print("nucleus: ask() with \(text.count) chars, working=\(working)")
        guard !text.isEmpty, !working else { return }
        working = true; problem = nil; current = nil; thumbs = [:]; explanationThumb = nil
        do {
            let id = try await NucleusAPI.ask(text)
            while true {
                let status = try await NucleusAPI.status(id)
                current = status
                // the rows show as soon as they exist; keep polling until the meaning under the first line is written
                if status.answer != nil && (status.explanation?.status ?? "none") != "pending" { break }
                try await Task.sleep(nanoseconds: 700_000_000)
            }
            await loadRecent()
        } catch {
            problem = "The Mac did not answer. \(error.localizedDescription)"
        }
        working = false
    }

    func open(_ id: String) async {
        print("nucleus: open(\(id))")
        do {
            current = try await NucleusAPI.status(id)
            question = current?.question.question ?? question
            thumbs = [:]; explanationThumb = nil
        } catch {
            problem = "The Mac did not answer. \(error.localizedDescription)"
        }
    }

    func loadRecent() async {
        recent = (try? await NucleusAPI.recent()) ?? []
    }

    func thumb(_ row: AskResponse.Row, up: Bool) async {
        thumbs["\(row.word)|\(row.record)"] = up ? 1 : 0
        try? await NucleusAPI.thumb(word: row.word, record: row.record, quote: row.quote, up: up)
    }

    var explanationThumb: Int?

    func thumbExplanation(up: Bool) async {
        guard let id = current?.question.id else { return }
        explanationThumb = up ? 1 : 0
        try? await NucleusAPI.thumbExplanation(questionID: id, up: up)
    }

    func thumbState(_ row: AskResponse.Row) -> Int? {
        thumbs["\(row.word)|\(row.record)"] ?? row.thumb
    }
}
