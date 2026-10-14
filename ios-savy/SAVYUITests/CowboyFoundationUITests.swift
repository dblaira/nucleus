import XCTest

@MainActor
final class CowboyFoundationUITests: XCTestCase {
    private var app: XCUIApplication!

    private func launch(reset: Bool = true, failedConnection: Bool = false) {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchArguments = ["SAVY_UI_TEST_UNLOCKED", "COWBOYAI_UI_TEST", "COWBOYAI_UI_TEST_UNPINNED"]
        if reset { app.launchArguments += ["SAVY_UI_TEST_RESET_REMINDERS", "COWBOYAI_UI_TEST_RESET"] }
        app.launchEnvironment["COWBOYAI_UI_TEST_BASE_URL"] = failedConnection ? "http://127.0.0.1:1" : "http://127.0.0.1:8766"
        app.launch()
        XCTAssertTrue(element("chargeFab").waitForExistence(timeout: 10) || element("sharedEntryForm").waitForExistence(timeout: 5))
    }

    func testFabRetainsAllFourSavyChoicesAndTheSameEntryForm() {
        launch()
        for kind in ["Reminder", "Action", "Post", "Calendar"] {
            element("chargeFab").tap()
            for choice in ["Reminder", "Action", "Post", "Calendar"] {
                XCTAssertTrue(app.buttons[choice].firstMatch.waitForExistence(timeout: 3), "Missing FAB choice: \(choice)")
            }
            attach("SAVY fan with all four choices")
            app.buttons[kind].firstMatch.tap()
            XCTAssertTrue(element("sharedEntryForm").waitForExistence(timeout: 5))
            XCTAssertTrue(element("PostTheme").exists)
            XCTAssertTrue(element("DecideAnswer0").exists)
            XCTAssertTrue(app.buttons["entryAskCowboyAI"].isEnabled)
            for segment in ["Reminder", "Action", "Calendar", "Post"] {
                XCTAssertTrue(app.segmentedControls.buttons[segment].exists)
            }
            attach("Original \(kind) form with added Ask")
            app.buttons["entryCancel"].tap()
            XCTAssertTrue(element("chargeFab").waitForExistence(timeout: 5))
        }
    }

    func testRightSwipePinsMultipleResponsesAndUnpinKeepsTheOthersAfterRelaunch() {
        launch()
        XCTAssertFalse(app.staticTexts["Recent responses"].exists)
        let firstCarousel = app.buttons["latest-ui-source"].firstMatch
        XCTAssertTrue(firstCarousel.waitForExistence(timeout: 5))
        XCTAssertEqual(firstCarousel.frame.height, 182, accuracy: 1)
        let first = element("recent-ui-source")
        reveal(element("responseSwipe-ui-source"))
        let compactHeight = first.frame.height
        setPinned("ui-source", true)
        XCTAssertGreaterThan(first.frame.height, compactHeight + 80)
        setPinned("ui-source-2", true)
        XCTAssertLessThan(element("recent-ui-source-2").frame.minY, first.frame.minY)
        attach("Two independently pinned responses with SAVY colors")
        setPinned("ui-source-2", false)
        XCTAssertEqual(first.value as? String, "Pinned")
        XCTAssertEqual(element("recent-ui-source-2").value as? String, "Unpinned")
        app.terminate(); launch(reset: false)
        reveal(element("responseSwipe-ui-source"))
        XCTAssertEqual(element("recent-ui-source").value as? String, "Pinned")
        XCTAssertEqual(element("recent-ui-source-2").value as? String, "Unpinned")
        element("responseSwipe-ui-source").tap()
        XCTAssertTrue(app.staticTexts["live-answer-question"].waitForExistence(timeout: 5))
        XCTAssertEqual(app.staticTexts["live-answer-question"].label, "A sample question for checking this screen.")
        XCTAssertFalse(app.buttons["pinConversation"].exists)
        XCTAssertFalse(app.buttons["conversationDetails"].exists)
        XCTAssertFalse(app.buttons["createFromConversation"].exists)
        attach("Pinned response reopens after relaunch")
    }

    func testSharedEntryAsksLiveCowboyAIAndReopensItsExactSavedAnswer() {
        launch()
        openEntry("Reminder")
        let title = element("Title")
        let ask = app.buttons["entryAskCowboyAI"]
        XCTAssertTrue(ask.isEnabled)
        ask.tap()
        XCTAssertTrue(app.keyboards.firstMatch.waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["entryAskWritingHint"].exists)
        XCTAssertTrue(title.isHittable, "Empty Ask must reveal and focus the existing writing field")
        XCTAssertFalse(app.staticTexts["live-answer-question"].exists, "An empty entry must not submit the template prompts")
        attach("Empty Ask focuses the original writing field")
        app.typeText("What is FLOW?")
        XCTAssertEqual(title.value as? String, "What is FLOW?", "Typing after Ask must go into the existing field")
        XCTAssertFalse(app.staticTexts["entryAskWritingHint"].exists)
        XCTAssertTrue(ask.isHittable, "Ask must remain reachable above the keyboard")
        attach("Original SAVY entry with writing and Ask")
        ask.tap()
        let explanation = app.staticTexts["form-explanation"]
        XCTAssertTrue(explanation.waitForExistence(timeout: 45), app.debugDescription)
        XCTAssertTrue(explanation.label.contains("FLOW"))
        XCTAssertEqual(app.staticTexts["live-answer-question"].label, "What is FLOW?")
        attach("Live FLOW response from the normal SAVY entry")
        let word = app.buttons["live-meaning-FLOW"]
        reveal(word); word.tap()
        let words = app.staticTexts.matching(identifier: "meaning-detail-words")
        XCTAssertTrue(words.firstMatch.waitForExistence(timeout: 5))
        let evidence = words.allElementsBoundByIndex.map(\.label).joined(separator: "\n")
        XCTAssertTrue(evidence.contains("If a process becomes a worry or burden kill it, and think BIGGER!"))
        attach("Actual dictionary evidence from the live response")
        app.buttons["meaning-detail-close"].tap()
        reveal(app.buttons["Back"].firstMatch, up: false)
        app.buttons["Back"].firstMatch.tap()
        XCTAssertTrue(app.buttons["entryAskCowboyAI"].waitForExistence(timeout: 5))
        reveal(title)
        XCTAssertEqual(title.value as? String, "What is FLOW?")
        app.buttons["entrySave"].tap()
        XCTAssertTrue(element("chargeFab").waitForExistence(timeout: 5))
        app.terminate(); launch(reset: false)
        app.buttons["Reminders"].firstMatch.tap()
        let saved = app.staticTexts["What is FLOW?"].firstMatch
        reveal(saved); saved.tap()
        let origin = app.buttons["entryOrigin"]
        XCTAssertTrue(origin.waitForExistence(timeout: 5))
        origin.tap()
        XCTAssertEqual(app.staticTexts["live-answer-question"].label, "What is FLOW?")
        XCTAssertTrue(app.staticTexts["form-explanation"].label.contains("FLOW"))
        attach("Saved entry reopens its exact response after relaunch")
    }

    func testConnectionFailureRetainsTheWholeEntryForRetry() {
        launch(failedConnection: true)
        openEntry("Action")
        let first = element("DecideAnswer0")
        first.coordinate(withNormalizedOffset: CGVector(dx: 0.15, dy: 0.9)).tap()
        first.typeText("My unfinished answer.\nKeep every line.")
        app.buttons["entryAskCowboyAI"].tap()
        XCTAssertTrue(app.staticTexts["live-answer-error"].waitForExistence(timeout: 20))
        attach("Connection failure leaves a return to the original writing")
        app.buttons["Back"].firstMatch.tap()
        XCTAssertTrue(element("DecideAnswer0").waitForExistence(timeout: 5))
        XCTAssertEqual(element("DecideAnswer0").value as? String, "What happened?\nMy unfinished answer.\nKeep every line.")
        XCTAssertTrue(app.buttons["entryAskCowboyAI"].isEnabled)
        app.terminate(); launch(reset: false, failedConnection: true)
        XCTAssertTrue(element("sharedEntryForm").waitForExistence(timeout: 5))
        XCTAssertEqual(element("DecideAnswer0").value as? String, "What happened?\nMy unfinished answer.\nKeep every line.")
        XCTAssertTrue(app.buttons["entryAskCowboyAI"].isEnabled)
        attach("Unsent writing recovered after relaunch")
        app.buttons["entryCancel"].tap()
    }

    private func openEntry(_ kind: String) {
        element("chargeFab").tap()
        XCTAssertTrue(app.buttons[kind].firstMatch.waitForExistence(timeout: 5))
        app.buttons[kind].firstMatch.tap()
        XCTAssertTrue(element("sharedEntryForm").waitForExistence(timeout: 5))
    }

    private func setPinned(_ id: String, _ pin: Bool) {
        let gesture = element("responseSwipe-\(id)")
        reveal(gesture)
        gesture.swipeRight()
        let button = element("recent-\(id)").buttons[pin ? "swipePin" : "swipeUnpin"].firstMatch
        XCTAssertTrue(button.waitForExistence(timeout: 3))
        XCTAssertTrue(button.isHittable, "Pin must be exposed by right swipe")
        attach(pin ? "Right swipe exposes Pin" : "Right swipe exposes Unpin")
        button.tap()
        let changed = XCTNSPredicateExpectation(predicate: NSPredicate(format: "value == %@", pin ? "Pinned" : "Unpinned"), object: element("recent-\(id)"))
        XCTAssertEqual(XCTWaiter.wait(for: [changed], timeout: 5), .completed)
    }

    private func element(_ id: String) -> XCUIElement {
        app.descendants(matching: .any).matching(identifier: id).firstMatch
    }

    private func reveal(_ target: XCUIElement, up: Bool = true) {
        for _ in 0..<12 {
            if target.exists, target.isHittable, target.frame.minY > 90, target.frame.maxY < app.frame.maxY - 170 { return }
            if up { app.swipeUp(velocity: .slow) } else { app.swipeDown(velocity: .slow) }
        }
        XCTAssertTrue(target.exists && target.isHittable, "Could not reveal \(target.identifier)")
    }

    private func attach(_ name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }
}
