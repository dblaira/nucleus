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
        if shouldSeedPin, let origin = model.currentOrigin { _ = model.archive.togglePin(origin) }
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
                _ = entries.save(entry)
            }
        }
        #endif
    }
}
