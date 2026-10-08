#!/usr/bin/env bash
set -euo pipefail

ios_dir="$(cd "$(dirname "$0")/.." && pwd)"
test_build_dir="$(mktemp -d "${TMPDIR:-/tmp}/nucleus-composer-tests.XXXXXX")"
trap 'rm -rf "$test_build_dir"' EXIT

# Compile the real response types, without UIKit or the live transport. This keeps the model
# tests offline and avoids copying API shapes into the test double.
sed '/^enum NucleusAPI/,$d' "$ios_dir/nucleus/API.swift" \
    | sed '/^import UIKit$/d' > "$test_build_dir/APIModels.swift"
# The category definition itself is Foundation-only; the surrounding SAVY shell uses SwiftUI.
sed -n '/^enum Category:/,/^}/p' "$ios_dir/nucleus/SavyShell.swift" >> "$test_build_dir/APIModels.swift"

"${SWIFTC:-swiftc}" -swift-version 6 -parse-as-library \
    "$ios_dir/nucleus/AskModel.swift" \
    "$ios_dir/nucleus/Themes.swift" \
    "$ios_dir/nucleus/QuestionExamples.swift" \
    "$test_build_dir/APIModels.swift" \
    "$ios_dir/tests/APIStub.swift" \
    "$ios_dir/tests/ComposerRegressionTests.swift" \
    -o "$test_build_dir/composer-tests"

"$test_build_dir/composer-tests"
