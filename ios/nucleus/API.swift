import Foundation

/// The Mac's nucleus service. The phone reaches it over Tailscale.
struct AskResponse: Decodable {
    struct Question: Decodable { let id: String; let question: String }
    struct Step: Decodable { let name: String; let started: Double; let finished: Double?; let note: String? }
    struct Phrase: Decodable { let phrase: String; let name: String; let text: String }
    struct Answer: Decodable { let status: String; let answer: String?; let text: String?; let gate_reason: String? }
    struct Row: Decodable {
        let word: String; let record: String; let quote: String; let kind: String?; let thumb: Int?; let saved: Bool
    }
    struct Explanation: Decodable { let status: String; let text: String?; let thumb: Int? }
    let question: Question
    let steps: [Step]
    let phrases: [Phrase]
    let answer: Answer?
    let asked_before: Int?
    let rows: [Row]?
    let explanation: Explanation?
}

struct RecentItem: Decodable, Identifiable {
    let id: String; let question: String; let status: String; let answer: String?; let finished: Double
}

enum NucleusAPI {
    static var base: URL {
        let saved = UserDefaults.standard.string(forKey: "nucleus.base") ?? "http://100.111.154.126:8766"
        return URL(string: saved) ?? URL(string: "http://100.111.154.126:8766")!
    }

    static func ask(_ question: String) async throws -> String {
        var request = URLRequest(url: base.appendingPathComponent("ask"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "content-type")
        request.httpBody = try JSONEncoder().encode(["question": question])
        let (data, _) = try await URLSession.shared.data(for: request)
        struct Reply: Decodable { let question_id: String }
        return try JSONDecoder().decode(Reply.self, from: data).question_id
    }

    static func status(_ id: String) async throws -> AskResponse {
        let (data, _) = try await URLSession.shared.data(from: base.appendingPathComponent("ask/\(id)"))
        return try JSONDecoder().decode(AskResponse.self, from: data)
    }

    static func recent() async throws -> [RecentItem] {
        let (data, _) = try await URLSession.shared.data(from: base.appendingPathComponent("recent"))
        return try JSONDecoder().decode([RecentItem].self, from: data)
    }

    static func thumbExplanation(questionID: String, up: Bool) async throws {
        var request = URLRequest(url: base.appendingPathComponent("thumb-explanation"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "content-type")
        request.httpBody = try JSONSerialization.data(withJSONObject: ["question_id": questionID, "up": up])
        _ = try await URLSession.shared.data(for: request)
    }

    static func thumb(word: String, record: String, quote: String, up: Bool) async throws {
        var request = URLRequest(url: base.appendingPathComponent("thumb"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "content-type")
        let body: [String: Any] = ["word": word, "record": record, "quote": quote, "up": up]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        _ = try await URLSession.shared.data(for: request)
    }
}
