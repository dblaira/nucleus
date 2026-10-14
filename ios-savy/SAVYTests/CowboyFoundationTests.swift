import XCTest
import UIKit
@testable import SAVY

final class CowboyFoundationTests: XCTestCase {
    private func directory() throws -> URL {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        addTeardownBlock { try? FileManager.default.removeItem(at: url) }
        return url
    }

    @MainActor func testPageBackgroundsStaySeparateAndBadImportKeepsThePhoto() throws {
        let folder = try directory()
        let image = UIGraphicsImageRenderer(size: CGSize(width: 20, height: 20)).image { context in
            UIColor.systemBlue.setFill()
            context.fill(CGRect(x: 0, y: 0, width: 20, height: 20))
        }
        let photo = try XCTUnwrap(image.jpegData(compressionQuality: 1))
        let backgrounds = PageBackgroundStore(directory: folder)
        try backgrounds.save(photo, for: .now)
        try backgrounds.save(photo, for: .calendar)
        let homeFile = folder.appendingPathComponent("now.jpg")
        let original = try Data(contentsOf: homeFile)
        XCTAssertThrowsError(try backgrounds.save(Data("invalid image".utf8), for: .now))
        XCTAssertEqual(try Data(contentsOf: homeFile), original)
        try backgrounds.useNavy(for: .calendar)
        let reloaded = PageBackgroundStore(directory: folder)
        XCTAssertNotNil(reloaded.image(for: .now))
        XCTAssertNil(reloaded.image(for: .calendar))
        XCTAssertNil(reloaded.image(for: .actions))
        XCTAssertNil(reloaded.image(for: .reminders))
    }

    private func response(_ id: String = "one", text: String = "Exact response.\nSecond line!") throws -> AskResponse {
        let value: [String: Any] = [
            "question": ["id": id, "question": "  Exact question.\nSecond line!  "],
            "steps": [], "phrases": [], "rows": [],
            "answer": ["status": "answered", "text": text, "answer": "aligned"]
        ]
        return try JSONDecoder().decode(AskResponse.self, from: JSONSerialization.data(withJSONObject: value))
    }

    func testEveryUntouchedSavyThemeIsNotAnAsk() {
        for theme in PostThemeCatalog.themes {
            var entry = Reminder(); entry.postThemeID = theme.id
            let question = EntryQuestion(entry: entry, draft: PostEntryDraft(entry: entry), subtasks: [])
            XCTAssertTrue(question.text.isEmpty, "Untouched template submitted as writing: \(theme.name)")
            XCTAssertTrue(question.theme.fields.allSatisfy { $0.answer.isEmpty })
        }
    }

    @MainActor func testHistoryImportPreservesExistingWritingPinsAndExactResponseBytes() throws {
        let file = try directory().appendingPathComponent("archive.json")
        let source = URL(string: "http://100.111.154.126:8766")!
        let archive = ConversationArchive(fileURL: file)
        let original = try XCTUnwrap(archive.capture(response("one", text: "My newer saved answer."), source: source))
        XCTAssertTrue(archive.togglePin(original))
        var metadata = archive.metadata(for: original)
        metadata.notes = "Keep my exact writing.\nAnd this line."
        XCTAssertTrue(archive.saveMetadata(metadata, for: original))
        let before = try XCTUnwrap(archive.record(questionID: "one", source: source))
        let older = try ConversationOrigin.capture(response("one", text: "Earlier answer."), source: source)
        let raw = Data(#"{"question":{"id":"two","question":"Exact earlier question."},"steps":[],"phrases":[],"answer":{"status":"answered","text":"Complete earlier answer."},"original_trace":{"keep":"every byte"}}"#.utf8)
        var fetched = try JSONDecoder().decode(AskResponse.self, from: raw)
        fetched.originalJSON = raw
        XCTAssertEqual(try ConversationOrigin.capture(fetched, source: source).responseJSON, raw,
                       "Opening an online answer must retain fields the screen does not render")
        let second = ConversationOrigin(source: "http://127.0.0.1:8766", questionID: "two",
                                        question: "Exact earlier question.", responseJSON: raw,
                                        capturedAt: Date(timeIntervalSince1970: 1_700_000_000))
        let imported = try JSONEncoder().encode([ArchivedConversation(latest: older), ArchivedConversation(latest: second)])
        XCTAssertTrue(archive.importHistory(imported, source: source))
        XCTAssertEqual(archive.record(questionID: "one", source: source), before)
        XCTAssertEqual(archive.record(questionID: "two", source: source)?.latest.responseJSON, raw)
        let savedBytes = try Data(contentsOf: file)
        XCTAssertTrue(archive.importHistory(imported, source: source))
        XCTAssertEqual(try Data(contentsOf: file), savedBytes, "Repeating the import must not rewrite the archive")
        let reloaded = ConversationArchive(fileURL: file)
        XCTAssertEqual(reloaded.record(questionID: "one", source: source), before)
        XCTAssertEqual(reloaded.record(questionID: "two", source: source)?.latest.responseJSON, raw)
    }

    @MainActor func testDamagedHistoryCannotPartiallyImportOrReplaceExistingArchive() throws {
        let file = try directory().appendingPathComponent("archive.json")
        let source = URL(string: "http://100.111.154.126:8766")!
        let archive = ConversationArchive(fileURL: file)
        _ = archive.capture(try response("existing"), source: source)
        let before = try Data(contentsOf: file)
        let origin = try ConversationOrigin.capture(response("new"), source: source)
        let duplicate = try JSONEncoder().encode([ArchivedConversation(latest: origin), ArchivedConversation(latest: origin)])
        XCTAssertFalse(archive.importHistory(duplicate, source: source))
        XCTAssertEqual(try Data(contentsOf: file), before)
        XCTAssertFalse(archive.importHistory(Data("damaged".utf8), source: source))
        XCTAssertEqual(try Data(contentsOf: file), before)
        let damagedFile = try directory().appendingPathComponent("archive.json")
        try Data("original damaged archive".utf8).write(to: damagedFile)
        let damaged = ConversationArchive(fileURL: damagedFile)
        XCTAssertFalse(damaged.importHistory(try JSONEncoder().encode([ArchivedConversation(latest: origin)])))
        XCTAssertEqual(try Data(contentsOf: damagedFile), Data("original damaged archive".utf8))
    }

    @MainActor func testCompleteBundledHistoryIsReadableOfflineAndSurvivesRelaunch() throws {
        let history = try XCTUnwrap(Bundle.main.url(forResource: "CowboyAIHistory", withExtension: "json"))
        let expected = try JSONDecoder().decode([ArchivedConversation].self, from: Data(contentsOf: history))
        XCTAssertEqual(expected.count, 168)
        let file = try directory().appendingPathComponent("archive.json")
        let source = URL(string: "http://100.111.154.126:8766")!
        let archive = ConversationArchive(fileURL: file, historyURL: history, historySource: source)
        XCTAssertFalse(archive.loadFailed)
        XCTAssertNil(archive.errorMessage)
        XCTAssertEqual(archive.records(for: source).count, expected.count)
        let reloaded = ConversationArchive(fileURL: file)
        for record in expected {
            let actual = try XCTUnwrap(reloaded.record(questionID: record.latest.questionID, source: source))
            XCTAssertEqual(actual.latest.responseJSON, record.latest.responseJSON)
            XCTAssertEqual(actual.latest.question, record.latest.question)
            XCTAssertEqual(actual.latest.capturedAt, record.latest.capturedAt)
            let model = AskModel(archive: reloaded, keepsComposerDraft: false)
            model.showSnapshot(actual.displayed)
            XCTAssertNotNil(model.current)
            XCTAssertNil(model.problem)
        }
    }

    func testAskPreservesEditedPromptsLineBreaksAndAllEntryWriting() {
        var entry = Reminder(); entry.title = "  My question.\nExact line!  "
        entry.whenIAm = " My context. "; entry.outcome = "Keep this!"; entry.notes = "Two\nlines."
        var draft = PostEntryDraft(entry: entry)
        draft.setAnswer("Edited question?\n  My answer.\nSecond line!  ", at: 0)
        let ask = EntryQuestion(entry: entry, draft: draft, subtasks: [])
        XCTAssertEqual(ask.theme.question, entry.title)
        XCTAssertEqual(ask.theme.fields[0].prompt, "Edited question?")
        XCTAssertEqual(ask.theme.fields[0].answer, "  My answer.\nSecond line!  ")
        XCTAssertEqual(ask.text, "What do I want?\n  My question.\nExact line!  \n\nEdited question?\n  My answer.\nSecond line!  \n\nWhen I am...I like to\n My context. \n\nDone looks like...\nKeep this!\n\nNotes\nTwo\nlines.")
    }

    func testMultilineThemePromptIsKeptWholeAndDoesNotBecomeAnAnswer() throws {
        let theme = try XCTUnwrap(PostThemeCatalog.themes.first { $0.questions.first?.prompt.contains("\n") == true })
        var entry = Reminder(); entry.postThemeID = theme.id
        var draft = PostEntryDraft(entry: entry)
        let prompt = theme.questions[0].prompt
        draft.setAnswer(prompt + "\n  My answer.\nKeep spaces.  ", at: 0)
        let ask = EntryQuestion(entry: entry, draft: draft, subtasks: [])
        XCTAssertEqual(ask.theme.fields[0].prompt, prompt)
        XCTAssertEqual(ask.theme.fields[0].answer, "  My answer.\nKeep spaces.  ")
        XCTAssertEqual(ask.text, prompt + "\n  My answer.\nKeep spaces.  ")
    }

    @MainActor func testNewEntryAnswerCannotOverwriteUnfinishedOtherWriting() throws {
        let key = CowboyStorage.preferenceKey("nucleus.draft")
        let previous = UserDefaults.standard.object(forKey: key)
        defer { UserDefaults.standard.set(previous, forKey: key) }
        UserDefaults.standard.set("Keep my other writing.", forKey: key)
        let model = AskModel(archive: ConversationArchive(fileURL: try directory().appendingPathComponent("archive.json")), keepsComposerDraft: false)
        model.question = "Entry question."
        XCTAssertEqual(UserDefaults.standard.string(forKey: key), "Keep my other writing.")
    }

    @MainActor func testPinUnpinOrderAndOriginalSnapshotSurviveReload() throws {
        let file = try directory().appendingPathComponent("archive.json")
        let source = URL(string: "http://127.0.0.1:8766")!
        let archive = ConversationArchive(fileURL: file)
        let one = try XCTUnwrap(archive.capture(response("one"), source: source))
        let two = try XCTUnwrap(archive.capture(response("two"), source: source))
        let three = try XCTUnwrap(archive.capture(response("three"), source: source))
        XCTAssertTrue(archive.togglePin(one)); XCTAssertTrue(archive.togglePin(two))
        XCTAssertEqual(archive.records(for: source).map { $0.displayed.questionID }, ["two", "one", "three"])
        XCTAssertTrue(archive.move(one, direction: .up))
        XCTAssertEqual(archive.records(for: source).map { $0.displayed.questionID }, ["one", "two", "three"])
        _ = archive.capture(try response("one", text: "Later response."), source: source)
        XCTAssertEqual(archive.record(questionID: "one", source: source)?.displayed, one)
        XCTAssertTrue(archive.togglePin(two))
        let reloaded = ConversationArchive(fileURL: file)
        XCTAssertTrue(reloaded.isPinned(one)); XCTAssertFalse(reloaded.isPinned(two)); XCTAssertFalse(reloaded.isPinned(three))
        XCTAssertEqual(reloaded.records(for: source).map { $0.displayed.questionID }, ["one", "two", "three"])
        XCTAssertEqual(reloaded.record(questionID: "one", source: source)?.displayed.responseJSON, one.responseJSON)
    }

    @MainActor func testCompletedResponseSurvivesRefreshAndReopensWithItsPinnedAnswerAndNotes() throws {
        let file = try directory().appendingPathComponent("archive.json")
        let source = URL(string: "http://127.0.0.1:8766")!
        let archive = ConversationArchive(fileURL: file)
        let origin = try XCTUnwrap(archive.capture(response(), source: source))
        XCTAssertTrue(archive.togglePin(origin))
        var details = archive.metadata(for: origin)
        details.notes = "Keep my exact notes.\nAnd this line."
        XCTAssertTrue(archive.saveMetadata(details, for: origin))
        let before = try XCTUnwrap(archive.record(questionID: origin.questionID, source: source))

        XCTAssertTrue(archive.complete(origin))
        XCTAssertTrue(archive.records(for: source).isEmpty)
        XCTAssertEqual(archive.records(for: source, status: .completed).map(\.displayed), [origin])
        let completedAt = try XCTUnwrap(archive.metadata(for: origin).completedAt)
        // An already-open editor, reimport, and a newer server answer must all respect Done.
        XCTAssertTrue(archive.saveMetadata(details, for: origin))
        XCTAssertTrue(archive.importHistory(try JSONEncoder().encode([before]), source: source))
        let refreshed = try XCTUnwrap(archive.capture(response(text: "A later server answer."), source: source))
        XCTAssertEqual(archive.metadata(for: origin).completedAt, completedAt)
        XCTAssertTrue(archive.records(for: source).isEmpty)

        let reloaded = ConversationArchive(fileURL: file)
        XCTAssertEqual(reloaded.records(for: source, status: .completed).map(\.displayed), [origin])
        XCTAssertTrue(reloaded.uncomplete(origin))
        let reopened = try XCTUnwrap(reloaded.records(for: source).first)
        XCTAssertEqual(reopened.displayed, origin)
        XCTAssertEqual(reopened.latest, refreshed)
        XCTAssertEqual(reopened.pinnedAt, before.pinnedAt)
        XCTAssertEqual(reopened.cardMetadata?.notes, details.notes)
        XCTAssertNil(reopened.cardMetadata?.completedAt)
        XCTAssertTrue(reloaded.records(for: source, status: .completed).isEmpty)
        XCTAssertEqual(ConversationArchive(fileURL: file).records(for: source).first, reopened)
    }

    @MainActor func testDeletedResponsesStayHiddenWithoutChangingOtherSourcesOrLinkedWriting() throws {
        let folder = try directory()
        let file = folder.appendingPathComponent("archive.json")
        let source = URL(string: "http://127.0.0.1:8766")!
        let otherSource = URL(string: "http://localhost:9999")!
        let archive = ConversationArchive(fileURL: file)
        let active = try XCTUnwrap(archive.capture(response("active"), source: source))
        let completed = try XCTUnwrap(archive.capture(response("completed"), source: source))
        let other = try XCTUnwrap(archive.capture(response("active"), source: otherSource))
        XCTAssertTrue(archive.togglePin(active))
        var staleDetails = archive.metadata(for: active)
        staleDetails.notes = "My saved writing.\nKeep it intact."
        XCTAssertTrue(archive.saveMetadata(staleDetails, for: active))
        let originalRecords = archive.conversations
        let entryFile = folder.appendingPathComponent("entries.json")
        let entries = ReminderStore(cacheURL: entryFile)
        var linked = Reminder(); linked.title = "My linked action."; linked.origin = active
        XCTAssertTrue(entries.save(linked))
        let linkedBytes = try Data(contentsOf: entryFile)

        XCTAssertTrue(archive.complete(completed))
        XCTAssertTrue(archive.delete(active))
        XCTAssertTrue(archive.delete(completed))
        XCTAssertTrue(archive.records(for: source).isEmpty)
        XCTAssertTrue(archive.records(for: source, status: .completed).isEmpty)
        XCTAssertEqual(archive.records(for: otherSource).map(\.displayed), [other])
        XCTAssertTrue(archive.importHistory(try JSONEncoder().encode(originalRecords), source: source))
        XCTAssertNotNil(archive.capture(try response("active", text: "Refreshed server answer."), source: source))
        XCTAssertNotNil(archive.capture(try response("completed", text: "A different refreshed answer."), source: source))
        XCTAssertTrue(archive.saveMetadata(staleDetails, for: active))
        XCTAssertFalse(archive.uncomplete(active))
        XCTAssertFalse(archive.togglePin(active))

        let reloaded = ConversationArchive(fileURL: file)
        XCTAssertTrue(reloaded.records(for: source).isEmpty)
        XCTAssertTrue(reloaded.records(for: source, status: .completed).isEmpty)
        XCTAssertEqual(reloaded.records(for: source, status: .deleted).count, 2)
        XCTAssertEqual(reloaded.record(questionID: active.questionID, source: source)?.displayed, active)
        XCTAssertEqual(reloaded.record(questionID: active.questionID, source: source)?.latest, active)
        XCTAssertEqual(reloaded.record(questionID: completed.questionID, source: source)?.displayed, completed)
        XCTAssertEqual(reloaded.metadata(for: active).notes, staleDetails.notes)
        XCTAssertEqual(try Data(contentsOf: entryFile), linkedBytes)
        XCTAssertEqual(ReminderStore(cacheURL: entryFile).reminders.first?.origin, active)
    }

    @MainActor func testFailedDeleteKeepsTheVisibleResponseAndItsSavedRecord() throws {
        let folder = try directory()
        let file = folder.appendingPathComponent("archive.json")
        let source = URL(string: "http://127.0.0.1:8766")!
        let archive = ConversationArchive(fileURL: file)
        let origin = try XCTUnwrap(archive.capture(response(), source: source))
        let original = try Data(contentsOf: file)
        let backup = folder.appendingPathComponent("preserved.json")
        try FileManager.default.moveItem(at: file, to: backup)
        // Force an actual atomic-write failure, without changing the in-memory record.
        try FileManager.default.createDirectory(at: file, withIntermediateDirectories: false)
        XCTAssertFalse(archive.delete(origin))
        XCTAssertNotNil(archive.errorMessage)
        XCTAssertEqual(archive.records(for: source).map(\.displayed), [origin])
        XCTAssertEqual(try Data(contentsOf: backup), original)
    }

    @MainActor func testMetadataAndLinkedEntryRetainTheirExactOriginAndWriting() throws {
        let dir = try directory(); let source = URL(string: "http://127.0.0.1:8766")!
        let archive = ConversationArchive(fileURL: dir.appendingPathComponent("archive.json"))
        let origin = try XCTUnwrap(archive.capture(response(), source: source))
        var metadata = archive.metadata(for: origin)
        metadata.context = .codePattern; metadata.priority = .high; metadata.energy = .low
        metadata.title = "Cannot replace the question"; metadata.notes = "My notes.\nKeep them."
        XCTAssertTrue(archive.saveMetadata(metadata, for: origin))
        let saved = archive.metadata(for: origin)
        XCTAssertEqual(saved.title, origin.question); XCTAssertEqual(saved.notes, metadata.notes)
        XCTAssertEqual(SavyCarouselDetail.values(for: saved).map(\.kind), [.pattern, .priority, .energy])
        let file = dir.appendingPathComponent("entries.json")
        let store = ReminderStore(cacheURL: file)
        var entry = Reminder(); entry.origin = origin; entry.title = "My exact entry."; entry.kind = .post
        XCTAssertTrue(store.save(entry))
        entry.kind = .action; entry.origin = try ConversationOrigin.capture(response("different"), source: source)
        XCTAssertTrue(store.save(entry))
        let reloaded = ReminderStore(cacheURL: file)
        let value = try XCTUnwrap(reloaded.reminders.first)
        XCTAssertEqual(value.origin, origin); XCTAssertEqual(value.title, "My exact entry.")
        XCTAssertEqual(value.kind, .action)
        XCTAssertEqual(reloaded.items(from: origin).count, 1)
        XCTAssertTrue(reloaded.candidateOutboxItems.isEmpty)
    }

    @MainActor func testCorruptConversationArchiveIsPreserved() throws {
        let file = try directory().appendingPathComponent("archive.json")
        let original = Data("Do not replace this damaged source.".utf8)
        try original.write(to: file)
        let archive = ConversationArchive(fileURL: file)
        XCTAssertTrue(archive.loadFailed)
        XCTAssertNil(archive.capture(try response(), source: URL(string: "http://127.0.0.1:8766")!))
        XCTAssertEqual(try Data(contentsOf: file), original)
    }

    func testOriginTimestampSurvivesBothEntryAndArchiveEncodersAndReadsOlderDates() throws {
        let date = Date(timeIntervalSinceReferenceDate: 813_331_777.123456)
        let origin = try ConversationOrigin.capture(response(), source: URL(string: "http://127.0.0.1:8766")!, now: date)
        for encoder in [JSONEncoder(), JSONEncoder.recall] {
            let data = try encoder.encode(origin)
            XCTAssertEqual(try JSONDecoder().decode(ConversationOrigin.self, from: data), origin)
            XCTAssertEqual(try JSONDecoder.recall.decode(ConversationOrigin.self, from: data), origin)
        }
        var legacy = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(origin)) as? [String: Any])
        for timestamp in ["2026-10-14T17:30:00Z", "2026-10-14T17:30:00.123Z"] {
            legacy["capturedAt"] = timestamp
            let data = try JSONSerialization.data(withJSONObject: legacy)
            let restored = try JSONDecoder().decode(ConversationOrigin.self, from: data)
            XCTAssertEqual(restored.question, origin.question)
            XCTAssertEqual(restored.responseJSON, origin.responseJSON)
            let formatter = ISO8601DateFormatter()
            formatter.formatOptions = timestamp.contains(".") ? [.withInternetDateTime, .withFractionalSeconds] : [.withInternetDateTime]
            XCTAssertEqual(restored.capturedAt, formatter.date(from: timestamp))
        }
    }

    @MainActor func testTrialCannotUseSavyIdentityCloudOrHarness() {
        XCTAssertEqual(Bundle.main.bundleIdentifier, "com.adamblair.cowboyai.savytrial")
        XCTAssertFalse(TrialIsolation.connectsToSavyServices)
        XCTAssertNil(Bundle.main.object(forInfoDictionaryKey: "SAVY_CLOUDKIT_CONTAINER"))
        XCTAssertNil(Bundle.main.object(forInfoDictionaryKey: "AWS_API_KEY"))
        XCTAssertNil(HarnessDelegationWriter.delegationsDirectory())
        XCTAssertFalse(HarnessDelegationWriter.write(want: "Synthetic isolation check", think: "", done: ""))
        XCTAssertEqual(CowboyStorage.directory.lastPathComponent, "CowboyAI-UI-Tests")
    }
}
