# ios — the nucleus app in the CowboyAI app's styling

Adam, 2026-09-12: "I want the styling only from Cowboyai to be ported over to this project repo. I want this so you
can build an ios app version of "nucleaus", that will eventually take over the name Cowboyai."

Adam, 2026-09-14: "Replace the styling in the nucleus app with the styling of the cowboy AI app. I like the
functionality of this app, but I don't like the styling at all, so replace the entire go find the code for cowboy AI
and just use it here, but use the data pipeline whatever the fuck you call it here"

Adam, 2026-09-14: "refer to the savy app repo so you can see the type of navigation expect.  Adopt the homepage layout of
SAVY.  Below it, below the carousel, you can list the different answers under the three categories ... Those can have
their own pages ... all three options should be available to press on"

The shell and home are SAVY's (`/Users/adamblair/Developer/GitHub/SAVY-iOS/SAVY`); the answer panels are the CowboyAI
app's (`Cowboyai/authority-hub/ios/CowboyAI`); the data is nucleus's (`API.swift`, `AskModel.swift`, port 8766):

- `RootView.swift` — SAVY's shell: tabs Now and Route with the bolt, pages pushed over the home. From SAVY RootView.
- `SavyShell.swift` — SAVY's layout numbers, the round menu button, the back button, the bottom bar, and `Category`:
  his three lines. From SAVY RootView, SavyShellComponents, ConnectionView.
- `HomeView.swift` — SAVY's home: the wordmark hero, the latest answers carousel (no title band), then his three lines
  as compact rows, each with its count, all three on the first screen. From SAVY EditorialHomeView.
- `CategoryPage.swift` — one line's page: SAVY's section page (tan header, back, navy list of band cards). From
  SAVY ConnectionView.
- `AnswerPage.swift` — one question and its answer with the back button; the cream panels are CowboyAI's
  (`LiveAnswerView.swift`): YOUR QUESTION, YOUR ANSWER (first line, meaning, thumbs), HE SAID THE WORD ITSELF,
  HIS ROUTES SENT IT HERE, POSSIBILITY. Asking from the bolt opens this page while the answer is written.
- `AnswerParts.swift` — splits the Mac's answer text (gate.compose) into those pieces; the Mac's pipeline is unchanged.
- `RouteView.swift` — the seven steps and how long each took. From CowboyAI RouteView.
- `ComposerView.swift` — the question form behind the bolt. From CowboyAI CowboyQuestionComposerView.
- `SettingsView.swift` — the Connection sheet (menu button): the Mac's address, the build stamp. From CowboyAI.
- `Theme.swift`, `Assets.xcassets` — `CowboyTheme` (+ SAVY paper and ink), AppIcon, CowboyHat. `Header.imageset`
  (the red rock photo) stays in the catalog and is not shown.

Stopped, refused and saved-without-answer results are not under any of the three lines; they appear in the latest
carousel only.

## On the Mac too

Adam, 2026-09-14: "load this into xcode in mac os so I can run it there too."

The same target builds as a Mac app (Mac Catalyst). In Xcode the destination is `My Mac (Mac Catalyst)`. From the
Mac it is at `~/Applications/nucleus.app`, built with:

    DEVELOPER_DIR="/Users/adamblair/Downloads/Xcode-beta 5.app/Contents/Developer" \
    xcodebuild -project nucleus.xcodeproj -scheme nucleus -destination 'platform=macOS,variant=Mac Catalyst' \
      -derivedDataPath ~/Library/Developer/nucleus-mac -configuration Debug -allowProvisioningUpdates build
    cp -R ~/Library/Developer/nucleus-mac/Build/Products/Debug-maccatalyst/nucleus.app ~/Applications/nucleus.app

## Building for Adam's iPhone

Build with derived data OUTSIDE ~/Documents (that folder is iCloud-synced and its file-provider attributes make
codesign fail with "resource fork, Finder information, or similar detritus not allowed"):

    DEVELOPER_DIR="/Users/adamblair/Downloads/Xcode-beta 5.app/Contents/Developer" \
    xcodebuild -project nucleus.xcodeproj -scheme nucleus -destination 'platform=iOS,id=B03CFB03-AA65-5941-BD82-8CBC60092BD9' \
      -derivedDataPath ~/Library/Developer/nucleus-build -configuration Debug -allowProvisioningUpdates build
    xcrun devicectl device install app --device B03CFB03-AA65-5941-BD82-8CBC60092BD9 ~/Library/Developer/nucleus-build/Build/Products/Debug-iphoneos/nucleus.app
    xcrun devicectl device process launch --device B03CFB03-AA65-5941-BD82-8CBC60092BD9 com.adamblair.nucleus

The phone must be on the Mac's Wi-Fi or plugged in. First installed 2026-09-12.

Launching with `devicectl device process launch` ties the app to the Mac's command: a second launch kills the first
instance (signal 9), and `--console` holds it until it exits. For normal use Adam opens the app from the home screen.
