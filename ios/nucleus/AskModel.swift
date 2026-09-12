import Foundation
import Observation

@MainActor
@Observable
final class AskModel {
    var question = ""
    var current: AskResponse?
    var recent: [RecentItem] = []
    var working = false
    var problem: String?
    var showAll = false
    var thumbs: [String: Int] = [:]      // "word|record" -> 1 up, 0 down

    static let stepNames = ["1 question in", "2 dictionary reads it", "3 your phrases found", "4 nucleus read whole",
                            "5 one model call", "6 the gate", "7 answer out"]

    func ask() async {
        let text = question.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !working else { return }
        working = true; problem = nil; current = nil; showAll = false; thumbs = [:]
        do {
            let id = try await NucleusAPI.ask(text)
            while true {
                let status = try await NucleusAPI.status(id)
                current = status
                if status.answer != nil { break }
                try await Task.sleep(nanoseconds: 700_000_000)
            }
            await loadRecent()
        } catch {
            problem = "The Mac did not answer. \(error.localizedDescription)"
        }
        working = false
    }

    func open(_ id: String) async {
        do {
            current = try await NucleusAPI.status(id)
            question = current?.question.question ?? question
            showAll = false; thumbs = [:]
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

    func thumbState(_ row: AskResponse.Row) -> Int? {
        thumbs["\(row.word)|\(row.record)"] ?? row.thumb
    }

    /// The answer text, split the way the page splits it: first line, then blocks separated by blank lines.
    var blocks: (first: String, rest: [String]) {
        guard let text = current?.answer?.text, !text.isEmpty else { return ("", []) }
        var lines = text.components(separatedBy: "\n")
        let first = lines.removeFirst()
        var blocks: [String] = []; var cur: [String] = []
        for line in lines {
            if line.isEmpty { if !cur.isEmpty { blocks.append(cur.joined(separator: "\n")) }; cur = [] } else { cur.append(line) }
        }
        if !cur.isEmpty { blocks.append(cur.joined(separator: "\n")) }
        return (first, blocks)
    }

    func row(for block: String) -> AskResponse.Row? {
        guard let rows = current?.rows else { return nil }
        return rows.first { row in
            let key = String(row.quote.replacingOccurrences(of: "\\\"", with: "\"").prefix(40))
            return !key.isEmpty && block.contains(key)
        }
    }
}
