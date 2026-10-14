import Foundation

/// Explicit debug launch only. Never sends an Ask or touches normal app files/preferences.
@MainActor enum CowboyUITestFixtures {
    static func prepare(model: AskModel, entries: ReminderStore) {
        #if DEBUG
        guard CowboyRuntime.isTesting else { return }
        let shouldSeedPin = model.archive.conversations.isEmpty
        let text = #"{"question":{"id":"ui-source","question":"A sample question for checking this screen.","theme":{"id":"ui-sample-theme","name":"Sample theme","question":"A sample question for checking this screen.","fields":[]}},"steps":[],"phrases":[],"answer":{"status":"answered","answer":"aligned","text":"A sample response, saved exactly as it appeared."},"rows":[],"form":{"explanation":"This is synthetic UI test content.","answer":"A sample response, saved exactly as it appeared.","sections":[]}}"#
        guard let response = try? JSONDecoder().decode(AskResponse.self, from: Data(text.utf8)) else { return }
        model.current = response
        model.currentOrigin = model.archive.capture(response, source: NucleusAPI.base)
        model.recent = [RecentItem(id: "ui-source", question: response.question.question,
                                   status: "answered", answer: "aligned", finished: 1_792_000_000)]
        for (index, question) in ["Another sample question in the carousel.", "A third sample question to swipe to."].enumerated() {
            guard let data = try? JSONSerialization.data(withJSONObject: [
                "question": ["id": "ui-source-\(index + 2)", "question": question],
                "steps": [], "phrases": [], "rows": [],
                "answer": ["status": "answered", "answer": "aligned", "text": "The response belonging to this question."]
            ]), let sample = try? JSONDecoder().decode(AskResponse.self, from: data) else { continue }
            _ = model.archive.capture(sample, source: NucleusAPI.base)
            model.recent.append(RecentItem(id: sample.question.id, question: question, status: "answered", answer: "aligned", finished: 1_792_000_000 - Double(index + 1) * 3600))
        }
        if shouldSeedPin {
            for record in model.archive.conversations.reversed() {
                let origin = record.latest
                var metadata = model.archive.metadata(for: origin)
                metadata.context = .codePattern
                metadata.priority = .high
                metadata.energy = .low
                if metadata.postThemeName == nil { metadata.postThemeName = "Sample theme" }
                _ = model.archive.saveMetadata(metadata, for: origin)
                if !ProcessInfo.processInfo.arguments.contains("COWBOYAI_UI_TEST_UNPINNED") {
                    _ = model.archive.togglePin(origin)
                }
            }
        }
        if ProcessInfo.processInfo.arguments.contains("COWBOYAI_UI_TEST_SEED"), entries.reminders.isEmpty {
            for (index, kind) in [ReminderKind.reminder, .action, .event].enumerated() {
                var entry = Reminder()
                entry.id = UUID(uuidString: String(format: "22222222-1111-4444-8888-%012d", index + 1))!
                entry.kind = kind
                entry.title = "Sample " + kind.label.lowercased()
                entry.origin = model.currentOrigin
                if kind == .event {
                    var calendar = Calendar.current
                    calendar.timeZone = .current
                    let start = calendar.date(bySettingHour: 11, minute: 0, second: 0, of: Date())!
                    entry.schedule = ReminderSchedule(startDate: start, endDate: start.addingTimeInterval(3600), alert: .none)
                    entry.dueDate = start; entry.dueTime = start; entry.endTime = start.addingTimeInterval(3600)
                }
                if ProcessInfo.processInfo.arguments.contains("COWBOYAI_UI_TEST_CARD_REFERENCE"), kind != .event {
                    entry.title = "Sample pinned " + kind.label.lowercased() + ": keep the complete thought visible while reviewing the information connected to this conversation."
                    entry.pinned = true
                    entry.upNextOrder = 0
                    entry.context = .codePattern
                    entry.priority = .high
                    entry.listName = "Sample saved Lift"
                    entry.notes = "Sample saved notes stay visible under the title and metadata, using the full card from SAVY."
                    for offset in 1...2 {
                        var other = Reminder()
                        other.kind = kind
                        other.title = (offset == 1 ? "Another pinned " : "A compact ") + kind.label.lowercased()
                        other.pinned = offset == 1
                        other.upNextOrder = offset
                        other.context = .clearSign
                        other.priority = .medium
                        _ = entries.save(other)
                    }
                }
                _ = entries.save(entry)
            }
        }
        #endif
    }
}
