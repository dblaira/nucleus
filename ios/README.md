# ios — the styling of CowboyAI, ported here for the nucleus app

Adam, 2026-09-12: "I want the styling only from Cowboyai to be ported over to this project repo. I want this so you
can build an ios app version of "nucleaus", that will eventually take over the name Cowboyai."

Copied as they are from `Cowboyai/authority-hub/ios/CowboyAI` (styling only, no screens, no logic):

- `Styling/Theme.swift` — `CowboyTheme`: navy, navyRaised, cream, tan, red, cardRed, bottomNavigationTan,
  navigationInactive, green, orange, muted; the editorial serif ("Bodoni 72 Oldstyle") and the carousel serif
  (Times New Roman); `BenDayDotBackground`.
- `Styling/Assets.xcassets` — AppIcon, CowboyHat.

The web page (`nucleus/serve.py`) uses the same palette. The app is not built yet.

## Building for Adam's iPhone

Build with derived data OUTSIDE ~/Documents (that folder is iCloud-synced and its file-provider attributes make
codesign fail with "resource fork, Finder information, or similar detritus not allowed"):

    DEVELOPER_DIR="/Users/adamblair/Downloads/Xcode-beta 5.app/Contents/Developer" \
    xcodebuild -project nucleus.xcodeproj -scheme nucleus -destination 'platform=iOS,id=B03CFB03-AA65-5941-BD82-8CBC60092BD9' \
      -derivedDataPath ~/Library/Developer/nucleus-build -configuration Debug -allowProvisioningUpdates build
    xcrun devicectl device install app --device B03CFB03-AA65-5941-BD82-8CBC60092BD9 ~/Library/Developer/nucleus-build/Build/Products/Debug-iphoneos/nucleus.app
    xcrun devicectl device process launch --device B03CFB03-AA65-5941-BD82-8CBC60092BD9 com.adamblair.nucleus

The phone must be on the Mac's Wi-Fi or plugged in. First installed 2026-09-12.
