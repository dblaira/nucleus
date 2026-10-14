import XCTest

final class SavyFlowTests: XCTestCase {
    @MainActor private func launchApp() -> XCUIApplication {
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launchArguments = ["COWBOYAI_UI_TEST", "COWBOYAI_UI_TEST_RESET", "COWBOYAI_UI_TEST_SEED"]
        app.launch()
        return app
    }
    @MainActor private func screenshot(_ name: String, app: XCUIApplication) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }
    @MainActor private func reveal(_ element: XCUIElement, app: XCUIApplication) {
        for _ in 0..<8 {
            if element.isHittable { return }
            app.swipeUp()
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
        XCTAssertTrue(first.otherElements["carouselDetail-theme"].exists)
        screenshot("Compact carousel with next card visible", app: app)
        carousel.swipeLeft()
        carousel.swipeLeft()
        XCTAssertTrue(third.isHittable)
        screenshot("Carousel after swiping to third pair", app: app)
        third.tap()
        XCTAssertTrue(app.staticTexts["live-answer-question"].waitForExistence(timeout: 5))
        XCTAssertEqual(app.staticTexts["live-answer-question"].label, "A third sample question to swipe to.")
    }

    @MainActor func testPinExpandsAndUnpinCompactsTheOriginalCard() {
        let app = launchApp()
        let card = app.buttons["latest-ui-source"]
        XCTAssertTrue(card.waitForExistence(timeout: 10))
        let pinnedHeight = card.frame.height
        XCTAssertEqual(pinnedHeight, 182, accuracy: 1)
        XCTAssertTrue(card.otherElements["carouselDetail-theme"].exists)
        card.press(forDuration: 1)
        app.buttons["Unpin"].tap()
        XCTAssertLessThan(card.frame.height, pinnedHeight / 2)
        card.press(forDuration: 1)
        app.buttons["Pin"].tap()
        XCTAssertEqual(card.frame.height, pinnedHeight, accuracy: 1)
        XCTAssertTrue(card.otherElements["carouselDetail-theme"].exists)
        screenshot("Pinned card with saved metadata beside compact cards", app: app)
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
