# CowboyAI Trial history for Adam's phone

On October 14, 2026, Adam asked for his existing Nucleus and CowboyAI information in this app so he can review it while out on a run. His exact instruction is in Cowboyai's append-only ledger, task `01a13bf5-c35c-7e13-a7b7-18893fec27fc`.

`SAVY/Resources/CowboyAIHistory.json` contains 168 saved conversations from the existing engine's `web` and `cowboyai-iphone` surfaces, including repeated questions with their separate saved answers. All records in the two existing simulator client archives are included. Their available metadata and pins are retained. The 204 grading runs and other command-line runs are outside the app's personal history.

The existing `nucleus.recover` routine added two missing original CowboyAI records; 53 were already present. A SQLite backup passed `integrity_check` first. Comparing the before/after snapshots confirmed all 394 earlier questions and answers were unchanged. The export, original archives, database copies, and response hashes are in `/Users/adamblair/Documents/SAVY-preservation/cowboyai-offline-history-20261014-125930`.

The client imports missing identities on launch. It does not replace an existing device's answers, writing, metadata, or pins. Repeating the import is a no-op. Malformed imports do not partially write. The two existing loopback/private-network addresses identify this same engine; records are mapped to the address used by this client. Other configured servers do not receive this import.

Every imported response retains the full original service payload. Subsequent online captures also retain the raw payload, including fields the current screen does not render. Viewing a saved response uses the local copy immediately. Asking a new question still uses the existing service connection.

Verification: four focused simulator tests passed, covering all 168 responses after reload, existing writing and pins, damaged imports, and a real saved response opened and reopened with network loading disabled and no synthetic fixtures. Screenshots were inspected. An unsigned generic iPhone build passed and its bundled history matched the source SHA-256 `f9141d23d05e43d9010a88256271848839b2faebd005ac82fdb49575f4d7192f`.

The phone project is `CowboyAITrial.xcodeproj`, with iPhone support enabled. Adam performs the final Run/install himself; this work did not access the phone. Original SAVY remains separate.
