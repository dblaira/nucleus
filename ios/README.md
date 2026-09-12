# ios — the styling of CowboyAI, ported here for the nucleus app

Adam, 2026-09-12: "I want the styling only from Cowboyai to be ported over to this project repo. I want this so you
can build an ios app version of "nucleaus", that will eventually take over the name Cowboyai."

Copied as they are from `Cowboyai/authority-hub/ios/CowboyAI` (styling only, no screens, no logic):

- `Styling/Theme.swift` — `CowboyTheme`: navy, navyRaised, cream, tan, red, cardRed, bottomNavigationTan,
  navigationInactive, green, orange, muted; the editorial serif ("Bodoni 72 Oldstyle") and the carousel serif
  (Times New Roman); `BenDayDotBackground`.
- `Styling/Assets.xcassets` — AppIcon, CowboyHat.

The web page (`nucleus/serve.py`) uses the same palette. The app is not built yet.
