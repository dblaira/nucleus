import XCTest
@testable import nucleus

final class EntryPersistenceTests: XCTestCase {
    func testEntryQuestionPreservesWritingAndExcludesUntouchedPrompts() {
        var entry = Reminder()
        var draft = PostEntryDraft(entry: entry)
        XCTAssertTrue(EntryQuestion(entry: entry, draft: draft, subtasks: []).text.isEmpty)
        entry.title = "  What is FLOW?\nKeep this line.  "
        entry.whenIAm = "These are my words."
        draft.setAnswer("My edited prompt?\nMy exact answer.\nSecond line!", at: 0)
        let request = EntryQuestion(entry: entry, draft: draft, subtasks: [])
        XCTAssertEqual(request.theme.question, entry.title)
        XCTAssertEqual(request.theme.fields[0].prompt, "My edited prompt?")
        XCTAssertEqual(request.theme.fields[0].answer, "My exact answer.\nSecond line!")
        XCTAssertEqual(request.text, "  What is FLOW?\nKeep this line.  \n\nMy edited prompt?\nMy exact answer.\nSecond line!\n\nWhen I am...I like to\nThese are my words.")
    }

    @MainActor func testEntryAnswerModelCannotOverwriteQuestionComposerDraft() throws {
        let composer = AskModel(archive: ConversationArchive(fileURL: try directory().appendingPathComponent("archive.json")))
        composer.question = "My unfinished separate question."
        composer.selectTheme(PostThemeCatalog.defaultTheme.id)
        composer.setThemeField("Keep this unfinished answer.", at: 0)
        let key = CowboyStorage.preferenceKey("nucleus.themeAnswers")
        let before = UserDefaults.standard.data(forKey: key)
        let entry = AskModel(archive: composer.archive, keepsComposerDraft: false)
        entry.question = "An entry request."
        entry.selectTheme(PostThemeCatalog.defaultTheme.id)
        entry.setThemeField("Separate entry words.", at: 0)
        XCTAssertEqual(UserDefaults.standard.string(forKey: CowboyStorage.preferenceKey("nucleus.draft")), "My unfinished separate question.")
        XCTAssertEqual(UserDefaults.standard.data(forKey: key), before)
    }

    private func fixture(_ answer: String = "The response stays exact.") throws -> AskResponse {
        let object: [String: Any] = [
            "question": ["id": "source-1", "question": "  Adam’s exact words.\nSecond line!  "],
            "steps": [], "phrases": [], "rows": [],
            "answer": ["status": "answered", "text": answer, "answer": "aligned"]
        ]
        return try JSONDecoder().decode(AskResponse.self, from: JSONSerialization.data(withJSONObject: object))
    }
    private func directory() throws -> URL {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        addTeardownBlock { try? FileManager.default.removeItem(at: url) }
        return url
    }

    @MainActor func testOriginSurvivesEditKindCompletionAndReload() throws {
        let file = try directory().appendingPathComponent("entries.json")
        let origin = try ConversationOrigin.capture(fixture(), source: URL(string: "https://one.example")!)
        let store = ReminderStore(fileURL: file, notify: { _ in }, cancelNotification: { _ in })
        var entry = Reminder(); entry.origin = origin; entry.title = "Keep my words\nexactly."; entry.kind = .reminder
        XCTAssertTrue(store.save(entry))
        let originalDate = store.item(entry.id)!.createdAt
        entry = store.item(entry.id)!; entry.kind = .action
        entry.origin = try ConversationOrigin.capture(fixture("Changed"), source: URL(string: "https://two.example")!)
        XCTAssertTrue(store.save(entry))
        store.complete(store.item(entry.id)!)
        let restored = ReminderStore(fileURL: file, notify: { _ in }, cancelNotification: { _ in }).item(entry.id)!
        XCTAssertEqual(restored.origin, origin)
        XCTAssertEqual(restored.origin?.response?.question.question, "  Adam’s exact words.\nSecond line!  ")
        XCTAssertEqual(restored.title, "Keep my words\nexactly.")
        XCTAssertEqual(restored.createdAt, originalDate)
        XCTAssertEqual(restored.kind, .action)
        XCTAssertEqual(restored.status, .completed)
    }

    @MainActor func testPinRetainsOriginalWhileLatestResponseChanges() throws {
        let file = try directory().appendingPathComponent("conversations.json")
        let archive = ConversationArchive(fileURL: file)
        let url = URL(string: "https://one.example/")!
        let first = archive.capture(try fixture(), source: url)!
        XCTAssertTrue(archive.togglePin(first))
        let later = archive.capture(try fixture("A later response."), source: url)!
        XCTAssertNotEqual(first.id, later.id)
        let restored = ConversationArchive(fileURL: file).record(questionID: "source-1", source: url)!
        XCTAssertEqual(restored.pinned, first)
        XCTAssertEqual(restored.latest, later)
        _ = archive.capture(try fixture(), source: URL(string: "https://another.example")!)
        XCTAssertEqual(archive.records(for: url).count, 1)
        XCTAssertEqual(archive.conversations.count, 2)
    }

    @MainActor func testPhoneSizedArchiveLookupsStayResponsiveAndPreservePinOrder() throws {
        let file = try directory().appendingPathComponent("conversations.json")
        let source = URL(string: "https://one.example/")!
        let otherSource = URL(string: "https://two.example")!
        var saved: [ArchivedConversation] = []
        for index in 0..<91 {
            let object: [String: Any] = [
                "question": ["id": "source-\(index)", "question": "Saved question \(index)"],
                "steps": [], "phrases": [], "rows": [],
                "answer": ["status": "answered", "text": "Exact response \(index)"]
            ]
            let response = try JSONDecoder().decode(AskResponse.self, from: JSONSerialization.data(withJSONObject: object))
            let origin = try ConversationOrigin.capture(response, source: source, now: Date(timeIntervalSince1970: Double(index)))
            var metadata = ConversationMetadata.seed(from: origin)
            metadata.pinned = index < 2
            metadata.upNextOrder = 91 - index
            metadata.notes = "Exact saved metadata \(index)"
            saved.append(ArchivedConversation(latest: origin, pinned: index < 2 ? origin : nil,
                                              pinnedAt: index < 2 ? origin.capturedAt : nil, cardMetadata: metadata))
        }
        let otherOrigin = try ConversationOrigin.capture(fixture(), source: otherSource)
        saved.append(ArchivedConversation(latest: otherOrigin, cardMetadata: ConversationMetadata.seed(from: otherOrigin)))
        try JSONEncoder().encode(saved).write(to: file)
        let archive = ConversationArchive(fileURL: file)
        XCTAssertFalse(archive.loadFailed)
        let storedBytes = try Data(contentsOf: file)

        // Startup checks every recent ID. It must not sort and hash the whole archive for each lookup.
        let started = Date()
        for record in saved {
            let recordSource = try XCTUnwrap(URL(string: record.latest.source))
            XCTAssertEqual(archive.record(questionID: record.latest.questionID, source: recordSource), record)
        }
        XCTAssertNil(archive.record(questionID: "not-saved", source: source))
        XCTAssertLessThan(Date().timeIntervalSince(started), 2.0, "Recent-ID lookups must not block startup.")

        let ordered = archive.records(for: source)
        let expected = [saved[1], saved[0]] + Array(saved[2..<91].reversed())
        XCTAssertEqual(ordered, expected)
        for record in ordered {
            let metadata = archive.metadata(for: record.displayed)
            XCTAssertEqual(metadata, record.cardMetadata)
        }
        XCTAssertEqual(try Data(contentsOf: file), storedBytes, "Reading and sorting must never rewrite saved records.")
    }

    @MainActor func testDraftsKeepOriginAndCannotCrossConversations() throws {
        let file = try directory().appendingPathComponent("drafts.json")
        let first = try ConversationOrigin.capture(fixture(), source: URL(string: "https://one.example")!)
        let second = try ConversationOrigin.capture(fixture("Another"), source: URL(string: "https://two.example")!)
        let key = EntryRecoveryDraft.reminderKey(existing: nil, kind: .action, origin: first)
        XCTAssertNotEqual(key, EntryRecoveryDraft.reminderKey(existing: nil, kind: .action, origin: second))
        var entry = Reminder(); entry.origin = first; entry.title = "Unfinished words"
        let draft = EntryRecoveryDraft.Contents.reminder(.init(original: nil, entry: entry, questions: PostEntryDraft(entry: entry), subtasks: [], tagDraft: "", imageData: nil, connectionMode: false))
        XCTAssertTrue(EntryDraftStore(fileURL: file).save(id: key, contents: draft))
        XCTAssertEqual(EntryDraftStore(fileURL: file).draft(for: key)?.contents, draft)
    }

    @MainActor func testCorruptFilesCannotBeOverwrittenAsEmpty() throws {
        let dir = try directory(), bytes = Data("unreadable original".utf8)
        let file = dir.appendingPathComponent("entries.json")
        try bytes.write(to: file)
        let store = ReminderStore(fileURL: file, notify: { _ in }, cancelNotification: { _ in })
        XCTAssertFalse(store.save(Reminder()))
        XCTAssertEqual(try Data(contentsOf: file), bytes)
        let archive = ConversationArchive(fileURL: file)
        XCTAssertNil(archive.capture(try fixture(), source: URL(string: "https://one.example")!))
        XCTAssertEqual(try Data(contentsOf: file), bytes)
    }

    @MainActor func testReorderDoesNotMoveHiddenKindsOrEraseOrigin() throws {
        let file = try directory().appendingPathComponent("entries.json")
        let store = ReminderStore(fileURL: file, notify: { _ in }, cancelNotification: { _ in })
        let origin = try ConversationOrigin.capture(fixture(), source: URL(string: "https://one.example")!)
        var values = [Reminder(), Reminder(), Reminder()]
        for i in values.indices {
            values[i].kind = i == 1 ? .reminder : .action
            values[i].pinned = true; values[i].upNextOrder = i; values[i].origin = origin
            XCTAssertTrue(store.save(values[i]))
        }
        store.moveUpNext(values[2], direction: .up)
        XCTAssertEqual(store.item(values[1].id)?.upNextOrder, 1)
        XCTAssertEqual(store.item(values[0].id)?.upNextOrder, 2)
        XCTAssertEqual(store.item(values[2].id)?.upNextOrder, 0)
        XCTAssertTrue(store.reminders.allSatisfy { $0.origin == origin })
    }

    func testHourlyAndPortableScheduleRules() throws {
        let start = Date(timeIntervalSince1970: 2_000_000_000)
        var entry = Reminder()
        entry.schedule = ReminderSchedule(startDate: start, endDate: start.addingTimeInterval(10800), alert: .hourly)
        let plans = ReminderNotificationPlan.requests(for: entry, now: start.addingTimeInterval(-60))
        XCTAssertEqual(plans.count, 4)
        XCTAssertTrue(plans.allSatisfy { !$0.repeats && $0.identifier.hasPrefix("cowboyai.reminder.") })
        entry.schedule?.calendarIdentifier = "this-device-only"
        entry.schedule?.calendarEventIdentifier = "event-only"
        XCTAssertNil(entry.schedule?.portable.calendarIdentifier)
        XCTAssertNil(entry.schedule?.portable.calendarEventIdentifier)
        entry.status = .completed
        XCTAssertTrue(ReminderNotificationPlan.requests(for: entry, now: start.addingTimeInterval(-60)).isEmpty)
    }
    @MainActor func testDownloadedHistoryUsesCompletionDatesNotImportOrder() throws {
        let archive = ConversationArchive(fileURL: try directory().appendingPathComponent("history.json"))
        let source = URL(string: "https://one.example")!
        var recent: [RecentItem] = []
        // The server sends newest first. Each successive download used to jump ahead of it.
        for (id, finished) in [("newest", 300.0), ("middle", 200.0), ("oldest", 100.0)] {
            let object: [String: Any] = ["question": ["id": id, "question": id], "steps": [], "phrases": [],
                "answer": ["status": "answered", "text": "Exact response " + id]]
            let response = try JSONDecoder().decode(AskResponse.self, from: JSONSerialization.data(withJSONObject: object))
            XCTAssertNotNil(archive.capture(response, source: source))
            recent.append(RecentItem(id: id, question: id, status: "answered", answer: "aligned", finished: finished))
        }
        let oldest = try XCTUnwrap(archive.record(questionID: "oldest", source: source)?.latest)
        XCTAssertTrue(archive.togglePin(oldest))
        XCTAssertEqual(archive.records(for: source).first?.latest.questionID, "oldest")
        XCTAssertEqual(archive.recentRecords(for: source, recent: recent).map { $0.latest.questionID }, ["newest", "middle", "oldest"])
    }

    func testPreviewIncludesTheExplanationInsteadOfOnlyTheVerdict() throws {
        let object: [String: Any] = ["question": ["id": "preview", "question": "A question"], "steps": [], "phrases": [],
            "answer": ["status": "answered", "text": "aligned and why"],
            "explanation": ["status": "shown", "text": "An exact, meaningful explanation."],
            "form": ["answer": "aligned and why", "sections": []]]
        let response = try JSONDecoder().decode(AskResponse.self, from: JSONSerialization.data(withJSONObject: object))
        let origin = try ConversationOrigin.capture(response, source: URL(string: "https://one.example")!)
        XCTAssertEqual(origin.answerPreview, "An exact, meaningful explanation.")
        XCTAssertEqual(origin.response?.answer?.text, "aligned and why")
    }

}
