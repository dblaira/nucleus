import CryptoKit
import Foundation
import Observation

/// An immutable copy of the exact question and response used to create an item.
/// Pattern/context in Reminder is independent of this source link.
struct ConversationOrigin: Codable, Equatable, Hashable, Identifiable, Sendable {
    let source: String
    let questionID: String
    let question: String
    let responseJSON: Data
    let capturedAt: Date

    var conversationID: String { Self.digest(Data((source + "\n" + questionID).utf8)) }
    var id: String { conversationID + ":" + Self.digest(responseJSON) }
    var response: AskResponse? { try? JSONDecoder().decode(AskResponse.self, from: responseJSON) }
    var answerPreview: String {
        guard let value = response else { return "Saved response" }
        let candidates = [value.explanation?.text, value.form?.explanation,
                          value.answer?.text, value.form?.answer, value.answer?.gate_reason]
        return candidates.compactMap { $0 }.first { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
            ?? "Response in progress"
    }

    static func capture(_ response: AskResponse, source: URL, now: Date = Date()) throws -> Self {
        guard !response.question.id.isEmpty else { throw ArchiveError.invalidIdentity }
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        return Self(source: canonicalSource(source), questionID: response.question.id,
                    question: response.question.question, responseJSON: try response.originalJSON ?? encoder.encode(response), capturedAt: now)
    }

    static func canonicalSource(_ url: URL) -> String {
        var parts = URLComponents(url: url, resolvingAgainstBaseURL: false)
        parts?.user = nil; parts?.password = nil; parts?.query = nil; parts?.fragment = nil
        var value = parts?.string ?? url.absoluteString
        while value.hasSuffix("/") { value.removeLast() }
        return value
    }

    private static func digest(_ data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }
}

extension ConversationOrigin {
    private enum CodingKeys: String, CodingKey {
        case source, questionID, question, responseJSON, capturedAt
    }

    init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        source = try values.decode(String.self, forKey: .source)
        questionID = try values.decode(String.self, forKey: .questionID)
        question = try values.decode(String.self, forKey: .question)
        responseJSON = try values.decode(Data.self, forKey: .responseJSON)
        if let interval = try? values.decode(Double.self, forKey: .capturedAt) {
            capturedAt = Date(timeIntervalSinceReferenceDate: interval)
        } else {
            let text = try values.decode(String.self, forKey: .capturedAt)
            let formatter = ISO8601DateFormatter()
            formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            let fractional = formatter.date(from: text)
            formatter.formatOptions = [.withInternetDateTime]
            guard let date = fractional ?? formatter.date(from: text) else {
                throw DecodingError.dataCorruptedError(forKey: .capturedAt, in: values,
                                                       debugDescription: "Invalid saved response timestamp")
            }
            capturedAt = date
        }
    }

    func encode(to encoder: Encoder) throws {
        var values = encoder.container(keyedBy: CodingKeys.self)
        try values.encode(source, forKey: .source)
        try values.encode(questionID, forKey: .questionID)
        try values.encode(question, forKey: .question)
        try values.encode(responseJSON, forKey: .responseJSON)
        // Origin identity must survive both the archive and SAVY's ISO8601 entry encoder.
        try values.encode(capturedAt.timeIntervalSinceReferenceDate, forKey: .capturedAt)
    }
}

enum ArchiveError: LocalizedError {
    case invalidIdentity, damagedArchive
    var errorDescription: String? {
        switch self {
        case .invalidIdentity: "This response has no saved question identity."
        case .damagedArchive: "The saved conversations could not be read. They have been kept intact."
        }
    }
}

/// The complete SAVY model is stored, not a reduced list of display labels.
/// Optional so existing CowboyAI archives remain readable.
struct ArchivedConversation: Codable, Equatable, Identifiable {
    var id: String { latest.conversationID }
    var latest: ConversationOrigin
    var pinned: ConversationOrigin?
    var pinnedAt: Date?
    var cardMetadata: Reminder? = nil
    var displayed: ConversationOrigin { pinned ?? latest }
}

enum ConversationMetadata {
    static func seed(from origin: ConversationOrigin) -> Reminder {
        var value = Reminder()
        let hex = Array(origin.conversationID.prefix(32))
        let uuid = String(hex[0..<8]) + "-" + String(hex[8..<12]) + "-" + String(hex[12..<16])
            + "-" + String(hex[16..<20]) + "-" + String(hex[20..<32])
        value.id = UUID(uuidString: uuid)!
        value.origin = origin
        value.title = origin.question
        value.createdAt = origin.capturedAt
        value.updatedAt = origin.capturedAt
        value.needsSync = false
        if let theme = origin.response?.question.theme {
            value.postThemeID = theme.id
            value.postThemeName = theme.name
            value.postAnswers = theme.fields.map { $0.prompt + "\n" + $0.answer }
            value.postAnswersContainQuestions = true
        }
        // No inferred Pattern, Priority, Energy, Lift, tags, or dates.
        return value
    }
}

@Observable @MainActor
final class ConversationArchive {
    private(set) var conversations: [ArchivedConversation] = []
    private(set) var loadFailed = false
    var errorMessage: String?
    @ObservationIgnored private let fileURL: URL

    convenience init() {
        let importsHistory = !CowboyRuntime.isTesting || ProcessInfo.processInfo.arguments.contains("COWBOYAI_UI_TEST_IMPORTED_HISTORY")
        self.init(fileURL: CowboyStorage.file("conversations.json"),
                  historyURL: importsHistory ? Bundle.main.url(forResource: "CowboyAIHistory", withExtension: "json") : nil,
                  historySource: NucleusAPI.base)
    }

    init(fileURL: URL, historyURL: URL? = nil, historySource: URL? = nil) {
        self.fileURL = fileURL
        load()
        if let historyURL, !loadFailed {
            do { _ = importHistory(try Data(contentsOf: historyURL), source: historySource) }
            catch { errorMessage = "The earlier conversations could not be imported. Existing conversations are unchanged." }
        }
    }

    private func load() {
        guard FileManager.default.fileExists(atPath: fileURL.path) else { return }
        do {
            var values = try JSONDecoder().decode([ArchivedConversation].self, from: Data(contentsOf: fileURL))
            guard Set(values.map(\.id)).count == values.count,
                  values.allSatisfy({ $0.latest.response != nil && ($0.pinned == nil || $0.pinned?.response != nil) })
            else { throw ArchiveError.damagedArchive }
            // Seed older archives in memory. Reading the archive does not write it.
            let ordered = values.indices.sorted { values[$0].latest.capturedAt > values[$1].latest.capturedAt }
            let lastRank = values.compactMap { $0.cardMetadata?.upNextOrder }.max() ?? -1
            for (offset, index) in ordered.enumerated() where values[index].cardMetadata == nil {
                var metadata = ConversationMetadata.seed(from: values[index].displayed)
                metadata.pinned = values[index].pinned != nil
                metadata.upNextOrder = lastRank + offset + 1
                values[index].cardMetadata = metadata
            }
            guard values.allSatisfy({ $0.cardMetadata?.origin?.conversationID == $0.id })
            else { throw ArchiveError.damagedArchive }
            conversations = values
        } catch { loadFailed = true; errorMessage = ArchiveError.damagedArchive.localizedDescription }
    }

    /// Add the preserved history without replacing writing, pins, or newer answers already on this device.
    @discardableResult
    func importHistory(_ data: Data, source: URL? = nil) -> Bool {
        guard !loadFailed else { return false }
        do {
            var imported = try JSONDecoder().decode([ArchivedConversation].self, from: data)
            let aliases = ["http://127.0.0.1:8766", "http://100.111.154.126:8766"]
            let destination = source.map(ConversationOrigin.canonicalSource)
            // The export belongs to this existing engine, not an arbitrary configured server.
            if let destination, !aliases.contains(destination) { return true }
            func mapped(_ origin: ConversationOrigin) throws -> ConversationOrigin {
                guard let response = origin.response,
                      response.question.id == origin.questionID,
                      response.question.question == origin.question else { throw ArchiveError.damagedArchive }
                guard let destination, aliases.contains(origin.source) else { return origin }
                return ConversationOrigin(source: destination, questionID: origin.questionID,
                                          question: origin.question, responseJSON: origin.responseJSON,
                                          capturedAt: origin.capturedAt)
            }
            for index in imported.indices {
                imported[index].latest = try mapped(imported[index].latest)
                if let pinned = imported[index].pinned { imported[index].pinned = try mapped(pinned) }
                if let origin = imported[index].cardMetadata?.origin {
                    imported[index].cardMetadata?.origin = try mapped(origin)
                }
                guard imported[index].cardMetadata == nil || imported[index].cardMetadata?.origin?.conversationID == imported[index].id,
                      imported[index].pinned == nil || imported[index].pinned?.conversationID == imported[index].id
                else { throw ArchiveError.damagedArchive }
            }
            guard Set(imported.map(\.id)).count == imported.count else { throw ArchiveError.damagedArchive }
            let existing = Set(conversations.map(\.id))
            var additions = imported.filter { !existing.contains($0.id) }
            guard !additions.isEmpty else { return true }
            let lastRank = conversations.compactMap { $0.cardMetadata?.upNextOrder }.max() ?? -1
            for index in additions.indices where additions[index].cardMetadata == nil {
                var metadata = ConversationMetadata.seed(from: additions[index].displayed)
                metadata.pinned = additions[index].pinned != nil
                metadata.upNextOrder = lastRank + index + 1
                additions[index].cardMetadata = metadata
            }
            return persist(conversations + additions)
        } catch {
            errorMessage = "The earlier conversations could not be imported. Existing conversations are unchanged."
            return false
        }
    }

    func records(for source: URL, status: ReminderStatus = .active) -> [ArchivedConversation] {
        let source = ConversationOrigin.canonicalSource(source)
        return conversations.filter { $0.latest.source == source }
            .map { record in
                (record: record, metadata: metadata(for: record.displayed, in: record))
            }
            .filter { $0.metadata.status == status }
            .sorted {
                if status == .completed {
                    let left = $0.metadata.completedAt ?? .distantPast
                    let right = $1.metadata.completedAt ?? .distantPast
                    return left == right ? $0.record.id < $1.record.id : left > right
                }
                return compareUpNext($0.metadata, $1.metadata)
            }
            .map { $0.record }
    }

    /// Server completion dates govern recency; downloading an old answer does not make it new.
    func recentRecords(for source: URL, recent: [RecentItem]) -> [ArchivedConversation] {
        let dates = Dictionary(recent.map { ($0.id, $0.finished) }, uniquingKeysWith: max)
        return records(for: source).sorted {
            let left = dates[$0.latest.questionID] ?? $0.latest.capturedAt.timeIntervalSince1970
            let right = dates[$1.latest.questionID] ?? $1.latest.capturedAt.timeIntervalSince1970
            return left == right ? $0.latest.questionID < $1.latest.questionID : left > right
        }
    }

    func record(questionID: String, source: URL) -> ArchivedConversation? {
        let source = ConversationOrigin.canonicalSource(source)
        return conversations.first {
            $0.latest.source == source && $0.latest.questionID == questionID
        }
    }

    func metadata(for origin: ConversationOrigin) -> Reminder {
        let record = conversations.first {
            $0.latest.source == origin.source && $0.latest.questionID == origin.questionID
        }
        return metadata(for: origin, in: record)
    }

    private func metadata(for origin: ConversationOrigin, in record: ArchivedConversation?) -> Reminder {
        var value = record?.cardMetadata ?? ConversationMetadata.seed(from: origin)
        value.pinned = record?.pinned != nil
        value.origin = origin
        value.title = origin.question
        return value
    }

    @discardableResult
    func capture(_ response: AskResponse, source: URL) -> ConversationOrigin? {
        do {
            let origin = try ConversationOrigin.capture(response, source: source)
            var next = conversations
            if let index = next.firstIndex(where: { $0.id == origin.conversationID }) {
                // Keep the removed record intact when an already-running request returns.
                if next[index].cardMetadata?.status == .deleted { return next[index].latest }
                if next[index].latest.id == origin.id { return next[index].latest }
                next[index].latest = origin
            } else {
                var metadata = ConversationMetadata.seed(from: origin)
                // SAVY's ascending manual ranks; a new response goes ahead of older responses.
                metadata.upNextOrder = (next.compactMap { $0.cardMetadata?.upNextOrder }.min() ?? 0) - 1
                next.append(ArchivedConversation(latest: origin, cardMetadata: metadata))
            }
            return persist(next) ? origin : nil
        } catch { errorMessage = error.localizedDescription; return nil }
    }

    @discardableResult
    func saveMetadata(_ metadata: Reminder, for origin: ConversationOrigin) -> Bool {
        guard let index = conversations.firstIndex(where: { $0.id == origin.conversationID }) else {
            errorMessage = "Save the original conversation before editing its details."
            return false
        }
        var next = conversations
        let previous = self.metadata(for: origin)
        var value = metadata
        // Identity, pin state, ordering, and source words are not metadata edits.
        value.id = previous.id
        value.origin = origin
        value.title = origin.question
        value.createdAt = previous.createdAt
        value.status = previous.status
        value.completedAt = previous.completedAt
        value.pinned = previous.pinned
        value.upNextOrder = previous.upNextOrder
        value.updatedAt = Date()
        value.needsSync = false
        next[index].cardMetadata = value
        return persist(next)
    }

    // Re_Call's complete / uncomplete / soft-delete lifecycle. The original pair stays
    // under its existing identity so a history import or server refresh cannot revive it.
    @discardableResult
    func complete(_ origin: ConversationOrigin) -> Bool { setStatus(.completed, for: origin) }

    @discardableResult
    func uncomplete(_ origin: ConversationOrigin) -> Bool { setStatus(.active, for: origin) }

    @discardableResult
    func delete(_ origin: ConversationOrigin) -> Bool { setStatus(.deleted, for: origin) }

    private func setStatus(_ status: ReminderStatus, for origin: ConversationOrigin) -> Bool {
        guard let index = conversations.firstIndex(where: { $0.id == origin.conversationID }) else {
            errorMessage = "This response could not be found in the saved conversations."
            return false
        }
        let record = conversations[index]
        var value = metadata(for: record.displayed, in: record)
        guard value.status != status else { return true }
        // A stale open page cannot reopen a deleted entry.
        guard value.status != .deleted else { return false }
        let now = Date()
        value.status = status
        if status == .completed { value.completedAt = now }
        if status == .active { value.completedAt = nil }
        value.updatedAt = now
        value.needsSync = false
        var next = conversations
        next[index].cardMetadata = value
        return persist(next)
    }

    func isPinned(_ origin: ConversationOrigin) -> Bool {
        conversations.first { $0.id == origin.conversationID }?.pinned != nil
    }

    @discardableResult
    func togglePin(_ origin: ConversationOrigin) -> Bool {
        guard let index = conversations.firstIndex(where: { $0.id == origin.conversationID }) else {
            errorMessage = "Save the original conversation before pinning it."
            return false
        }
        var next = conversations
        var value = metadata(for: origin)
        guard value.status == .active else { return false }
        value.pinned.toggle()
        value.updatedAt = Date()
        value.needsSync = false
        next[index].cardMetadata = value
        next[index].pinned = value.pinned ? origin : nil
        next[index].pinnedAt = value.pinned ? Date() : nil

        // SAVY's togglePin ordering: insert at the front of the new pin group.
        var group = next.compactMap(\.cardMetadata).filter {
            $0.origin?.source == origin.source && $0.status == .active && $0.pinned == value.pinned
        }
            .sorted(by: compareUpNext)
        group.removeAll { $0.id == value.id }
        group.insert(value, at: 0)
        for (rank, entry) in group.enumerated() {
            if let i = next.firstIndex(where: { $0.cardMetadata?.id == entry.id }) {
                if next[i].cardMetadata?.upNextOrder != rank {
                    next[i].cardMetadata?.upNextOrder = rank
                    next[i].cardMetadata?.updatedAt = Date()
                }
            }
        }
        return persist(next)
    }

    @discardableResult
    func move(_ origin: ConversationOrigin, direction: ReminderStore.UpNextMoveDirection) -> Bool {
        let current = metadata(for: origin)
        guard let source = URL(string: origin.source) else { return false }
        var block = records(for: source).map { metadata(for: $0.displayed) }
            .filter { $0.pinned == current.pinned }
        let visibleIndices = block.indices.filter { block[$0].kind == current.kind }
        guard let visibleIndex = visibleIndices.firstIndex(where: { block[$0].id == current.id }) else { return false }
        let target = direction == .up ? visibleIndex - 1 : visibleIndex + 1
        guard visibleIndices.indices.contains(target) else { return false }
        let sourceIndex = visibleIndices[visibleIndex]
        let targetIndex = visibleIndices[target]
        let ranks = block.compactMap(\.upNextOrder)
        let order: [(UUID, Int)]
        if ranks.count == block.count, Set(ranks).count == block.count {
            order = [(block[sourceIndex].id, ranks[targetIndex]), (block[targetIndex].id, ranks[sourceIndex])]
        } else {
            block.swapAt(sourceIndex, targetIndex)
            order = block.enumerated().map { ($0.element.id, $0.offset) }
        }
        var next = conversations
        for (id, rank) in order {
            if let index = next.firstIndex(where: { $0.cardMetadata?.id == id }) {
                next[index].cardMetadata?.upNextOrder = rank
                next[index].cardMetadata?.updatedAt = Date()
            }
        }
        return persist(next)
    }

    // SAVY's pinned-block / manual-order / date comparator.
    private func compareUpNext(_ lhs: Reminder, _ rhs: Reminder) -> Bool {
        if lhs.pinned != rhs.pinned { return lhs.pinned }
        switch (lhs.upNextOrder, rhs.upNextOrder) {
        case let (l?, r?): return l < r
        case (nil, nil): return (lhs.fireDate ?? lhs.createdAt) < (rhs.fireDate ?? rhs.createdAt)
        case (_?, nil): return true
        case (nil, _?): return false
        }
    }

    private func persist(_ next: [ArchivedConversation]) -> Bool {
        guard !loadFailed else { errorMessage = ArchiveError.damagedArchive.localizedDescription; return false }
        do {
            let data = try JSONEncoder().encode(next)
            try FileManager.default.createDirectory(at: fileURL.deletingLastPathComponent(), withIntermediateDirectories: true)
            try data.write(to: fileURL, options: .atomic)
            conversations = next; errorMessage = nil
            return true
        } catch { errorMessage = "Could not save this conversation on the iPhone. \(error.localizedDescription)"; return false }
    }
}
