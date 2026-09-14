# ios — the nucleus app in the CowboyAI app's styling

Adam, 2026-09-12: "I want the styling only from Cowboyai to be ported over to this project repo. I want this so you
can build an ios app version of "nucleaus", that will eventually take over the name Cowboyai."

Adam, 2026-09-14: "Replace the styling in the nucleus app with the styling of the cowboy AI app. I like the
functionality of this app, but I don't like the styling at all, so replace the entire go find the code for cowboy AI
and just use it here, but use the data pipeline whatever the fuck you call it here"

The screens are copied from `Cowboyai/authority-hub/ios/CowboyAI`; the data is nucleus's (`API.swift`, `AskModel.swift`,
port 8766):

- `RootView.swift` — the shell: navy hat header with the connection button, tan bottom bar with Decide, Route and the
  red bolt, the hat button. From `RootView.swift`.
- `DecideView.swift` — the home: the live answer, then PAST RESULTS as the horizontal carousel. From `SavedResultsView.swift`.
- `LiveAnswerView.swift` — the cream YOUR QUESTION panel, the cream YOUR ANSWER panel (first line, then the meaning,
  thumbs), then HE SAID THE WORD ITSELF (his word's meanings) and HIS ROUTES SENT IT HERE (the records his links reach,
  thumbs on each card), then POSSIBILITY. Tapping a card opens the complete words. From `LiveAnswerView.swift`.
- `AnswerParts.swift` — splits the Mac's answer text (gate.compose) into those pieces; the Mac's pipeline is unchanged.
- `RouteView.swift` — the seven steps and how long each took. From `RouteView.swift`.
- `ComposerView.swift` — the question form behind the bolt: the question, Ask. From `CowboyQuestionComposerView.swift`.
- `SettingsView.swift` — the Connection sheet: the Mac's address, the build stamp. From `SettingsView.swift`.
- `Theme.swift`, `Assets.xcassets` — `CowboyTheme`, AppIcon, CowboyHat. `Header.imageset` (the red rock photo) stays
  in the catalog and is not shown.

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
