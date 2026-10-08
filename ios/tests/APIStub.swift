import Foundation

/// Only the transport is replaced. The test runner compiles the response types from API.swift.
/// Any attempted request is recorded and fails; choosing an example must never reach this door.
@MainActor
enum NucleusAPI {
    static var calls: [String] = []

    private struct UnexpectedRequest: Error {}
    private static func unexpected(_ name: String) throws -> Never {
        calls.append(name)
        throw UnexpectedRequest()
    }

    static func ask(_ question: String, themeData: Data? = nil) async throws -> String {
        try unexpected("ask")
    }

    static func status(_ id: String) async throws -> AskResponse { try unexpected("status") }
    static func recent() async throws -> [RecentItem] { try unexpected("recent") }
    static func more(questionID: String, text: String) async throws { try unexpected("more") }
    static func thumbExplanation(questionID: String, up: Bool) async throws { try unexpected("thumbExplanation") }
    static func thumb(word: String, record: String, quote: String, up: Bool) async throws { try unexpected("thumb") }
}
