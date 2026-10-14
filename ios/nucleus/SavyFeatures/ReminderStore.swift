import Foundation
import Observation

/// SAVY's local-save, completion, pinning and reorder behavior, isolated from every
/// external repository, candidate queue, shared container, and delegation writer.
@Observable @MainActor
final class ReminderStore {
    private(set) var reminders: [Reminder] = []
    private(set) var loadFailed = false
    var errorMessage: String?
    @ObservationIgnored private let fileURL: URL
    @ObservationIgnored private let notify: @MainActor (Reminder) -> Void
    @ObservationIgnored private let cancelNotification: @MainActor (Reminder) -> Void

    init(fileURL: URL = CowboyStorage.file("entries.json"),
         notify: @escaping @MainActor (Reminder) -> Void = NotificationScheduler.schedule,
         cancelNotification: @escaping @MainActor (Reminder) -> Void = NotificationScheduler.cancel) {
        self.fileURL = fileURL; self.notify = notify; self.cancelNotification = cancelNotification
        guard FileManager.default.fileExists(atPath: fileURL.path) else { return }
        do {
            let data = try Data(contentsOf: fileURL)
            // New records keep the full timestamp precision. Also accept the imported
            // SAVY serializer used by early development builds of this feature.
            let values = try (try? JSONDecoder().decode([Reminder].self, from: data))
                ?? JSONDecoder.recall.decode([Reminder].self, from: data)
            guard Set(values.map(\.id)).count == values.count else { throw CocoaError(.fileReadCorruptFile) }
            reminders = values
        } catch { loadFailed = true; errorMessage = "The saved entries could not be read. They have been kept intact." }
    }

    var active: [Reminder] { reminders.filter { $0.status == .active }.sorted(by: compareUpNext) }
    var completed: [Reminder] {
        reminders.filter { $0.status == .completed }.sorted { ($0.completedAt ?? .distantPast) > ($1.completedAt ?? .distantPast) }
    }

    func bootstrap() async {
        for reminder in reminders { notify(reminder) }
        #if canImport(UIKit)
        await CalendarScheduleBridge.shared.retryPendingSync()
        #endif
    }

    func item(_ id: UUID) -> Reminder? { reminders.first { $0.id == id } }
    func items(from origin: ConversationOrigin) -> [Reminder] {
        let linked = reminders.filter { $0.status != .deleted && $0.origin?.conversationID == origin.conversationID }
        return linked.filter { $0.status == .active }.sorted(by: compareUpNext)
            + linked.filter { $0.status == .completed }.sorted {
                ($0.completedAt ?? .distantPast) > ($1.completedAt ?? .distantPast)
            }
    }

    @discardableResult
    func save(_ reminder: Reminder) -> Bool {
        var value = reminder
        let existing = item(value.id)
        // Origin and creation are identity, never reassigned by editing or changing kind.
        if let existing { value.origin = existing.origin; value.createdAt = existing.createdAt }
        if let problem = value.schedule?.validationMessage { errorMessage = problem; return false }
        value.updatedAt = Date(); value.needsSync = false
        var next = reminders
        if let index = next.firstIndex(where: { $0.id == value.id }) { next[index] = value }
        else { next.append(value) }
        guard persist(next) else { return false }
        notify(value)
        #if canImport(UIKit)
        if value.status != .active || (existing != nil && existing?.status != value.status) {
            Task { @MainActor in
                await CalendarScheduleBridge.shared.reconcileSynced(previous: existing ?? value, current: self.item(value.id))
            }
        }
        #endif
        return true
    }

    func complete(_ reminder: Reminder) {
        var value = reminder; value.status = .completed; value.completedAt = Date()
        if save(value) { cancelNotification(value) }
    }
    func uncomplete(_ reminder: Reminder) {
        var value = reminder; value.status = .active; value.completedAt = nil
        _ = save(value)
    }
    func delete(_ reminder: Reminder) {
        var value = reminder; value.status = .deleted
        if save(value) { cancelNotification(value) }
    }

    /// Same pin groups and newest-pin-first behavior as SAVY's ReminderStore.
    func togglePin(_ reminder: Reminder) {
        guard let index = reminders.firstIndex(where: { $0.id == reminder.id }) else { return }
        var next = reminders
        next[index].pinned.toggle(); next[index].updatedAt = Date()
        let value = next[index]
        var group = next.filter { $0.status == .active && $0.pinned == value.pinned }.sorted(by: compareUpNext)
        group.removeAll { $0.id == value.id }; group.insert(value, at: 0)
        for (rank, entry) in group.enumerated() {
            if let i = next.firstIndex(where: { $0.id == entry.id }) { next[i].upNextOrder = rank }
        }
        _ = persist(next)
    }

    enum UpNextMoveDirection { case up, down }
    func moveUpNext(_ reminder: Reminder, direction: UpNextMoveDirection) {
        guard let current = item(reminder.id), current.status == .active else { return }
        var block = active.filter { $0.pinned == current.pinned }
        let indices = block.indices.filter { block[$0].kind == current.kind }
        guard let visible = indices.firstIndex(where: { block[$0].id == current.id }) else { return }
        let target = direction == .up ? visible - 1 : visible + 1
        guard indices.indices.contains(target) else { return }
        let sourceIndex = indices[visible], targetIndex = indices[target]
        let ranks = block.compactMap(\.upNextOrder)
        if ranks.count == block.count, Set(ranks).count == block.count {
            applyOrder([(block[sourceIndex].id, ranks[targetIndex]), (block[targetIndex].id, ranks[sourceIndex])])
        } else {
            block.swapAt(sourceIndex, targetIndex)
            applyOrder(block.enumerated().map { ($0.element.id, $0.offset) })
        }
    }

    private func applyOrder(_ order: [(UUID, Int)]) {
        var next = reminders
        for (id, rank) in order {
            if let index = next.firstIndex(where: { $0.id == id }), next[index].upNextOrder != rank {
                next[index].upNextOrder = rank; next[index].updatedAt = Date()
            }
        }
        _ = persist(next)
    }

    private func compareUpNext(_ lhs: Reminder, _ rhs: Reminder) -> Bool {
        if lhs.pinned != rhs.pinned { return lhs.pinned }
        switch (lhs.upNextOrder, rhs.upNextOrder) {
        case let (l?, r?) where l != r: return l < r
        case (_?, nil): return true
        case (nil, _?): return false
        default:
            let l = lhs.fireDate ?? lhs.createdAt, r = rhs.fireDate ?? rhs.createdAt
            return l == r ? lhs.id.uuidString < rhs.id.uuidString : l < r
        }
    }

    private func persist(_ next: [Reminder]) -> Bool {
        guard !loadFailed else { return false }
        do {
            guard Set(next.map(\.id)).count == next.count else { throw CocoaError(.fileWriteUnknown) }
            try FileManager.default.createDirectory(at: fileURL.deletingLastPathComponent(), withIntermediateDirectories: true)
            try JSONEncoder().encode(next).write(to: fileURL, options: .atomic)
            reminders = next; errorMessage = nil
            return true
        } catch { errorMessage = "Could not save this entry on the iPhone. \(error.localizedDescription)"; return false }
    }
}
