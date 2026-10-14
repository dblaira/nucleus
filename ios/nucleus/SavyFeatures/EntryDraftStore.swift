import Foundation

/// Recovery is private to CowboyAI and never submits or schedules a draft.
struct EntryRecoveryDraft: Codable, Equatable, Identifiable {
    struct ReminderWriting: Codable, Equatable {
        var original: Reminder?
        var entry: Reminder
        var questions: PostEntryDraft
        var subtasks: [Subtask]
        var tagDraft: String
        var imageData: Data?
        var connectionMode: Bool
        var conversationID: String? = nil
    }
    enum Contents: Codable, Equatable { case reminder(ReminderWriting) }
    var id: String
    var editedAt: Date
    var contents: Contents

    static func reminderKey(existing: Reminder?, kind: ReminderKind, origin: ConversationOrigin?) -> String {
        if let existing { return "entry:" + existing.id.uuidString }
        return "new:" + kind.rawValue + ":" + (origin?.id ?? "standalone")
    }
}

@MainActor
final class EntryDraftStore {
    static let shared = EntryDraftStore(fileURL: CowboyStorage.file("entry-drafts.json"))
    private let fileURL: URL
    private var drafts: [String: EntryRecoveryDraft] = [:]
    private(set) var loadFailed = false

    init(fileURL: URL) {
        self.fileURL = fileURL
        guard FileManager.default.fileExists(atPath: fileURL.path) else { return }
        do { drafts = try JSONDecoder().decode([String: EntryRecoveryDraft].self, from: Data(contentsOf: fileURL)) }
        catch { loadFailed = true }
    }

    var latest: EntryRecoveryDraft? {
        drafts.values.filter {
            if case .reminder(let writing) = $0.contents { return writing.conversationID == nil }
            return false
        }.max { $0.editedAt < $1.editedAt }
    }
    func draft(for key: String) -> EntryRecoveryDraft? { drafts[key] }

    @discardableResult
    func save(id: String, contents: EntryRecoveryDraft.Contents) -> Bool {
        if drafts[id]?.contents == contents { return true }
        var next = drafts
        next[id] = EntryRecoveryDraft(id: id, editedAt: Date(), contents: contents)
        return persist(next)
    }

    @discardableResult
    func remove(_ id: String) -> Bool {
        guard drafts[id] != nil else { return !loadFailed }
        var next = drafts; next.removeValue(forKey: id)
        return persist(next)
    }

    private func persist(_ next: [String: EntryRecoveryDraft]) -> Bool {
        guard !loadFailed else { return false }
        do {
            try FileManager.default.createDirectory(at: fileURL.deletingLastPathComponent(), withIntermediateDirectories: true)
            try JSONEncoder().encode(next).write(to: fileURL, options: .atomic)
            drafts = next
            return true
        } catch { return false }
    }
}
