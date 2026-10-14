import XCTest

final class SavyFlowTests: XCTestCase {
    @MainActor func testHomeAskReachesLiveDictionaryEvidenceAndSavedResponse() {
        let app = launchApp()
        let question = "What is FLOW?"
        let homeAsk = app.buttons["homeAskCowboyAI"]
        XCTAssertTrue(homeAsk.waitForExistence(timeout: 10))
        homeAsk.tap()
        let input = app.textViews["new-question-text"].firstMatch
        let fallback = app.descendants(matching: .any).matching(identifier: "new-question-text").firstMatch
        let field = input.exists ? input : fallback
        field.tap(); field.typeText(question)
        let ask = app.buttons["ask-nucleus"]
        reveal(ask, app: app)
        screenshot("Original question form ready to Ask", app: app)
        ask.tap()
        let explanation = app.staticTexts["form-explanation"]
        XCTAssertTrue(explanation.waitForExistence(timeout: 30), app.debugDescription)
        XCTAssertTrue(explanation.label.contains("FLOW"))
        XCTAssertEqual(app.staticTexts["live-answer-question"].label, question)
        screenshot("Real FLOW answer from visible Ask form", app: app)
        let word = app.buttons["live-meaning-FLOW"]
        reveal(word, app: app); word.tap()
        XCTAssertTrue(app.staticTexts["meaning-detail-words"].waitForExistence(timeout: 5))
        screenshot("Actual dictionary words opened from response", app: app)
        app.buttons["meaning-detail-close"].tap()
        let record = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "live-record-")).firstMatch
        reveal(record, app: app); record.tap()
        XCTAssertTrue(app.staticTexts["meaning-detail-words"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.staticTexts.matching(identifier: "meaning-detail-words").allElementsBoundByIndex.map(\.label).joined().isEmpty)
        screenshot("Accepted graph record opened from response", app: app)
        app.buttons["meaning-detail-close"].tap()
        for _ in 0..<8 { if app.buttons["pinConversation"].isHittable { break }; app.swipeDown() }
        app.buttons["pinConversation"].tap()
        app.buttons["Back"].firstMatch.tap()
        let card = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@ AND label CONTAINS %@", "latest-", question)).firstMatch
        XCTAssertTrue(card.waitForExistence(timeout: 5))
        print("LIVE_FLOW_QUESTION_ID=\(card.identifier)")
        app.terminate()
        app.launchArguments = ["COWBOYAI_UI_TEST", "COWBOYAI_UI_TEST_SEED"]
        app.launch()
        XCTAssertTrue(card.waitForExistence(timeout: 10))
        card.tap()
        XCTAssertEqual(app.staticTexts["live-answer-question"].label, question)
        XCTAssertTrue(app.staticTexts["form-explanation"].label.contains("FLOW"))
        screenshot("Real response reopened after app relaunch", app: app)
    }

    @MainActor func testEntryAsksLiveOntologyAndKeepsItsAnswer() {
        let app = launchApp()
        app.buttons["chargeFab"].tap(); app.buttons["Reminder"].tap()
        let ask = app.buttons["entryAskCowboyAI"]
        XCTAssertTrue(ask.waitForExistence(timeout: 5))
        XCTAssertFalse(ask.isEnabled, "Untouched template prompts must not be submitted as personal writing.")
        let question = "What are reasons I would avoid going to the doctor?"
        let title = app.descendants(matching: .any).matching(identifier: "Title").firstMatch
        reveal(title, app: app); title.tap(); title.typeText(question)
        XCTAssertTrue(ask.isHittable, "Ask must remain reachable with the keyboard open.")
        screenshot("Entry form with visible Ask and keyboard", app: app)
        ask.tap()
        let explanation = app.staticTexts["form-explanation"]
        XCTAssertTrue(explanation.waitForExistence(timeout: 30), app.debugDescription)
        XCTAssertTrue(explanation.label.contains("Health"))
        XCTAssertTrue(explanation.label.contains("Belief"))
        XCTAssertEqual(app.staticTexts["live-answer-question"].label, question)
        screenshot("Entry request answered using actual ontology and graph", app: app)
        app.buttons["Back"].firstMatch.tap()
        XCTAssertTrue(app.buttons["entryAskCowboyAI"].waitForExistence(timeout: 5))
        reveal(title, app: app)
        XCTAssertEqual(title.value as? String, question)
        app.buttons["entrySave"].tap()
        XCTAssertTrue(app.buttons["chargeFab"].waitForExistence(timeout: 5))
        app.terminate()
        app.launchArguments = ["COWBOYAI_UI_TEST", "COWBOYAI_UI_TEST_SEED"]
        app.launch()
        app.buttons["tab-reminders"].tap()
        let saved = app.staticTexts[question].firstMatch
        reveal(saved, app: app); saved.tap()
        let origin = app.buttons["entryOrigin"]
        XCTAssertTrue(origin.waitForExistence(timeout: 5))
        origin.tap()
        XCTAssertEqual(app.staticTexts["live-answer-question"].label, question)
        XCTAssertTrue(app.staticTexts["form-explanation"].label.contains("Health"))
        screenshot("Saved reminder reopens its actual answer", app: app)
    }

    @MainActor func testOriginalHowToFormWithAdamsExample() {
        let app = launchApp()
        app.buttons["homeAskCowboyAI"].tap()
        app.buttons["PostTheme"].tap()
        app.buttons["How-To"].tap()
        XCTAssertTrue(app.descendants(matching: .any).matching(identifier: "DecideAnswer3").firstMatch.exists)
        let question = "I have neutral moments many times per day that I don't have a plan for how to react.  I want a plan. Done, looks like me knowing what to do, and doing it because the alternative to getting myself back in flow is such a useless alternative."
        let field = app.descendants(matching: .any).matching(identifier: "new-question-text").firstMatch
        reveal(field, app: app); field.tap(); field.typeText(question)
        let ask = app.buttons["ask-nucleus"]
        reveal(ask, app: app)
        screenshot("Original How-To form with Adams example", app: app)
        ask.tap()
        let explanation = app.staticTexts["form-explanation"]
        XCTAssertTrue(explanation.waitForExistence(timeout: 30), app.debugDescription)
        XCTAssertFalse(explanation.label.isEmpty)
        XCTAssertTrue(explanation.label.contains("DELEGATION"))
        XCTAssertTrue(explanation.label.contains("FLOW"))
        XCTAssertFalse(explanation.label.contains("summarize what we did hear"))
        XCTAssertFalse(explanation.label.contains("Any future addition to Apple Notes"))
        XCTAssertEqual(app.staticTexts["live-answer-question"].label, question)
        screenshot("Actual answer to Adams How-To example", app: app)
        let word = app.buttons["live-meaning-FLOW"]
        reveal(word, app: app); word.tap()
        XCTAssertTrue(app.staticTexts["meaning-detail-words"].waitForExistence(timeout: 5))
        screenshot("Adams example reaches his FLOW meaning", app: app)
    }

    @MainActor func testEntryConnectionFailureKeepsWritingAndAllowsRetry() {
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launchArguments = ["COWBOYAI_UI_TEST", "COWBOYAI_UI_TEST_RESET", "COWBOYAI_UI_TEST_SEED"]
        app.launchEnvironment["COWBOYAI_UI_TEST_BASE_URL"] = "http://127.0.0.1:1"
        app.launch()
        app.buttons["chargeFab"].tap(); app.buttons["Action"].tap()
        let title = app.descendants(matching: .any).matching(identifier: "Title").firstMatch
        reveal(title, app: app); title.tap(); title.typeText("Keep my unfinished writing.")
        app.buttons["entryAskCowboyAI"].tap()
        XCTAssertTrue(app.staticTexts["live-answer-error"].firstMatch.waitForExistence(timeout: 20))
        XCTAssertFalse(app.staticTexts["form-explanation"].exists)
        screenshot("Connection failure is visible", app: app)
        app.buttons["Back"].firstMatch.tap()
        XCTAssertTrue(app.buttons["entryAskCowboyAI"].waitForExistence(timeout: 5))
        reveal(title, app: app)
        XCTAssertEqual(title.value as? String, "Keep my unfinished writing.")
        XCTAssertTrue(app.buttons["entryAskCowboyAI"].isEnabled)
        screenshot("Writing preserved after connection failure", app: app)
    }

    @MainActor private func launchApp(extraArguments: [String] = []) -> XCUIApplication {
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launchArguments = ["COWBOYAI_UI_TEST", "COWBOYAI_UI_TEST_RESET", "COWBOYAI_UI_TEST_SEED"] + extraArguments
        app.launch()
        return app
    }
    @MainActor private func screenshot(_ name: String, app: XCUIApplication) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }
    @MainActor private func reveal(_ element: XCUIElement, app: XCUIApplication) {
        for _ in 0..<8 {
            // UIKit may call a field hittable when a fixed footer covers it.
            // Scroll it into the actual writing area before tapping or typing.
            let bottom = app.keyboards.firstMatch.exists ? app.keyboards.firstMatch.frame.minY - 110 : app.frame.maxY - 210
            if element.exists, element.isHittable, element.frame.minY > 130, element.frame.midY < bottom { return }
            if element.exists, element.frame.minY < 130 { app.swipeDown() }
            else { app.swipeUp() }
        }
        XCTAssertTrue(element.isHittable)
    }

    @MainActor func testSavyFabOpensArcAndCloses() {
        let app = launchApp()
        let fab = app.buttons["chargeFab"]
        XCTAssertTrue(fab.waitForExistence(timeout: 10))
        fab.tap()
        XCTAssertTrue(app.buttons["Question"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.buttons["Reminder"].exists)
        XCTAssertTrue(app.buttons["Action"].exists)
        XCTAssertTrue(app.buttons["Calendar event"].exists)
        screenshot("SAVY quick entry arc", app: app)
        fab.tap()
        XCTAssertFalse(app.buttons["Question"].exists)
        fab.tap()
        app.buttons["Question"].tap()
        XCTAssertTrue(app.descendants(matching: .any).matching(identifier: "new-question-text").firstMatch.waitForExistence(timeout: 3))
        XCTAssertTrue(app.buttons["ask-nucleus"].exists)
    }

    @MainActor func testTabsAndOriginReopen() {
        let app = launchApp()
        XCTAssertTrue(app.buttons["latest-ui-source"].waitForExistence(timeout: 10))
        screenshot("CowboyAI header hat and photo body", app: app)
        app.buttons["tab-reminders"].tap()
        XCTAssertTrue(app.descendants(matching: .any).matching(identifier: "remindersHome").firstMatch.waitForExistence(timeout: 5))
        screenshot("Reminders", app: app)
        app.staticTexts["Sample reminder"].tap()
        XCTAssertTrue(app.buttons["entryOrigin"].waitForExistence(timeout: 5))
        app.buttons["entryOrigin"].tap()
        XCTAssertTrue(app.staticTexts["live-answer-question"].waitForExistence(timeout: 5))
        XCTAssertEqual(app.staticTexts["live-answer-question"].label, "A sample question for checking this screen.")
        screenshot("Original question and response", app: app)
    }

    @MainActor func testHomeCarouselScrollsBetweenSavedPairs() {
        let app = launchApp()
        let carousel = app.scrollViews["latestCarousel"]
        let first = app.buttons["latest-ui-source"]
        let third = app.buttons["latest-ui-source-3"]
        XCTAssertTrue(first.waitForExistence(timeout: 10))
        XCTAssertEqual(first.frame.height, 182, accuracy: 1)
        XCTAssertEqual(first.frame.width, 282, accuracy: 1)
        XCTAssertGreaterThan(carousel.frame.width, first.frame.width)
        for kind in ["theme", "pattern", "priority", "energy"] {
            XCTAssertTrue(first.otherElements["carouselDetail-\(kind)"].exists)
        }
        screenshot("SAVY cream carousel with saved metadata", app: app)
        carousel.swipeLeft()
        carousel.swipeLeft()
        XCTAssertTrue(third.isHittable)
        screenshot("Carousel after swiping to third pair", app: app)
        third.tap()
        XCTAssertTrue(app.staticTexts["live-answer-question"].waitForExistence(timeout: 5))
        XCTAssertEqual(app.staticTexts["live-answer-question"].label, "A third sample question to swipe to.")
    }

    @MainActor func testPinKeepsCarouselMetadataAndUnpinReturnsToRecent() {
        let app = launchApp()
        let card = app.buttons["latest-ui-source"]
        XCTAssertTrue(card.waitForExistence(timeout: 10))
        let pinnedHeight = card.frame.height
        XCTAssertEqual(pinnedHeight, 182, accuracy: 1)
        XCTAssertTrue(card.otherElements["carouselDetail-theme"].exists)
        card.press(forDuration: 1)
        app.buttons["Unpin"].tap()
        XCTAssertFalse(card.exists)
        let recent = app.buttons["recent-ui-source"]
        reveal(recent, app: app)
        recent.press(forDuration: 1)
        app.buttons["Pin"].tap()
        XCTAssertEqual(card.frame.height, pinnedHeight, accuracy: 1)
        for kind in ["theme", "pattern", "priority", "energy"] {
            XCTAssertTrue(card.otherElements["carouselDetail-\(kind)"].exists)
        }
        screenshot("Pinned carousel with all saved metadata", app: app)
    }

    @MainActor func testSavyPinnedCardHierarchyOnRemindersAndActions() {
        let app = launchApp(extraArguments: ["COWBOYAI_UI_TEST_CARD_REFERENCE"])
        for tab in ["reminders", "actions"] {
            app.buttons["tab-\(tab)"].tap()
            // SAVY's text identifiers are inherited by each metadata line. Its
            // gesture surfaces identify whole cards and expose their actual bounds.
            let cards = app.otherElements.matching(NSPredicate(format: "identifier BEGINSWITH %@", "reminderReorderGesture-"))
            let first = cards.element(boundBy: 0)
            XCTAssertTrue(first.waitForExistence(timeout: 5))
            XCTAssertEqual(cards.count, 3)
            XCTAssertGreaterThan(first.frame.height, cards.element(boundBy: 1).frame.height)
            XCTAssertEqual(cards.element(boundBy: 1).frame.height, 186, accuracy: 1)
            XCTAssertLessThan(cards.element(boundBy: 2).frame.height, 60)
            XCTAssertTrue(app.staticTexts["Code the Pattern   ·   !!!"].exists)
            XCTAssertTrue(app.staticTexts["Sample saved Lift"].exists)
            XCTAssertTrue(app.staticTexts["Sample saved notes stay visible under the title and metadata, using the full card from SAVY."].exists)
            screenshot("SAVY large white pin and smaller \(tab) cards", app: app)
        }
    }

    @MainActor func testCreateLinkedActionAndRetainAfterRelaunch() {
        let app = launchApp()
        app.buttons["latest-ui-source"].tap()
        let create = app.buttons["createFromConversation"]
        reveal(create, app: app); create.tap()
        app.buttons["Action"].tap()
        let title = app.descendants(matching: .any).matching(identifier: "Title").firstMatch
        reveal(title, app: app)
        XCTAssertTrue(title.waitForExistence(timeout: 5))
        title.tap(); title.typeText("A linked action to keep")
        app.buttons["entrySave"].tap()
        XCTAssertTrue(app.buttons.matching(identifier: "createFromConversation").firstMatch.waitForExistence(timeout: 5))
        app.terminate()
        app.launchArguments = ["COWBOYAI_UI_TEST", "COWBOYAI_UI_TEST_SEED"]
        app.launch()
        app.buttons["tab-actions"].tap()
        XCTAssertTrue(app.staticTexts["A linked action to keep"].waitForExistence(timeout: 5))
        app.staticTexts["A linked action to keep"].tap()
        XCTAssertTrue(app.buttons["entryOrigin"].waitForExistence(timeout: 5))
        app.buttons["entryOrigin"].tap()
        XCTAssertEqual(app.staticTexts["live-answer-question"].label, "A sample question for checking this screen.")
        screenshot("Persisted action with original conversation", app: app)
    }

    @MainActor func testScheduleEditorAndCalendar() {
        let app = launchApp()
        app.buttons["tab-calendar"].tap()
        XCTAssertTrue(app.staticTexts["Calendar"].firstMatch.waitForExistence(timeout: 5))
        screenshot("Native calendar", app: app)
        app.buttons["chargeFab"].tap()
        app.buttons["Calendar event"].tap()
        let title = app.descendants(matching: .any).matching(identifier: "Title").firstMatch
        reveal(title, app: app)
        XCTAssertTrue(title.waitForExistence(timeout: 5))
        title.tap(); title.typeText("A local calendar event")
        app.buttons["KeyboardRowDone"].tap()
        let schedule = app.buttons["openSchedule"]
        reveal(schedule, app: app); schedule.tap()
        XCTAssertTrue(app.descendants(matching: .any).matching(identifier: "scheduleForm").firstMatch.waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["scheduleCalendar"].exists)
        screenshot("Native schedule fields", app: app)
        app.buttons["scheduleDone"].tap()
        app.buttons["entrySave"].tap()
    }
}
