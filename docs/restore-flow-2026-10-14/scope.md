# Restore CowboyAI's existing flow

Adam, verbatim, Codex chat `01a13b35-d823-7d12-8533-fc906c3ec11f`, October 14, 2026:

> Then fix it. Restore the original flow and carousel, remove those Pin / Details / Create buttons, and keep the SAVY styling and features I asked for. Verify the actual visuals in the simulator. Don't touch my phone.

Objective: restore the original Now → lightning → Theme / Decide / question / Ask flow and a populated history carousel with pinned pairs first. Remove the answer toolbar while preserving native card-menu access to pinning, editing and linked reminders, actions and events. Preserve the approved SAVY colours, metadata, card hierarchy, tabs and separate stores.

Authoritative inputs: this instruction; the preserved app and same-question screenshots inspected October 14; Adam's original form screenshots; `CowboyAI SAVY Plan.html`; `docs/adam-savy-decisions.md`; the actual SAVY source as a read-only reference.

Clean source baseline: `3437a012d550bc6174b5110ef6a4b3eb4ea63bdc`. Exclusive write scope: iOS presentation and its directly relevant regression tests, this evidence folder, and the CowboyAI instruction ledger on a separate branch. The older recovery checkout's Xcode state and nucleus main's existing work remain untouched.

Forbidden: physical-device access, engine or answer changes, ontology/dictionary edits, SAVY changes, database replacement/migration/deletion, unrelated architecture or deployments.

Dependencies: existing local Nucleus service; existing recovery simulator and its preserved normal app data. UI test fixtures use the existing isolated UI-test storage.

Acceptance: build for iOS Simulator; test ordinary unpinned history, pinned-first ordering, swipe/open/back, direct question composition, absence of the toolbar, linked entry persistence and origin navigation, SAVY tabs/card hierarchy, and connection-failure draft preservation. Inspect actual running home, question, answer, card menu and SAVY feature screens and save screenshots. Record the exact tested commit and result in verification.md.
