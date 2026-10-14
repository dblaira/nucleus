# CowboyAI recovery — October 13, 2026

Objective: recover CowboyAI usability according to the existing CowboyAI SAVY plan, retaining Nucleus deterministic answers, the updated ontology and knowledge graph, and SAVY-style reminders/actions/calendar with independent storage.

Inputs: the complete HTML plan at Documents/Main/Cowboyai/CowboyAI SAVY Plan.html; original uncommitted integration at .codex/worktrees/cowboyai-savy-native; existing source and HANDOFF. Baseline 5d307ba7eb90dc7f4278e853087167032e8a0841. Imported source hashes are in import-manifest.json. The original worktree is unchanged.

Exclusive write scope: this recovery checkout's iOS app, simulator tests, recovery documentation. Forbidden: physical phone access, SAVY changes, ontology/dictionary/graph writes, engine replacement, data deletion, other worktrees' uncommitted changes. Dependency: existing Nucleus service. The final phone build belongs to Adam.

Acceptance: native simulator question/answer, ordered paired carousel, pins, origin-preserving reminder/action/calendar creation and reopening, local persistence, existing focused tests, and visible screenshots. Record actual results rather than inferring them from build success.

Adam, verbatim, in Codex chat 01a13833-cae9-7882-92fa-73cb7a1acc8b:

> at no time will you be allow to access my phone.  I need and don't want you fucking with it.  I will personally run the xcode build at the very, very end.  You can use the simulator.  It is 7:22pm.  You have until 7:45 to complete everything before we have to stop for the night.

> You have 20 minutes left
