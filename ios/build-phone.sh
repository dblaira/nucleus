#!/bin/zsh
# Build nucleus for Adam's iPhone, prove the binary is new, install only when he is not in the app, never launch.
set -e
export DEVELOPER_DIR="/Users/adamblair/Downloads/Xcode-beta 5.app/Contents/Developer"
DEV=B03CFB03-AA65-5941-BD82-8CBC60092BD9
DD=/Users/adamblair/Library/Developer/nucleus-build
cd "$(dirname "$0")"
STAMP="$(date '+%b %-d %H:%M') · $(git rev-parse --short HEAD)"
cat > nucleus/BuildStamp.swift <<SWIFT
// written by build-phone.sh; shows in the gear sheet so the phone can prove which build it runs
enum BuildStamp { static let text = "$STAMP" }
SWIFT
BEFORE=$(stat -f %m "$DD/Build/Products/Debug-iphoneos/nucleus.app/nucleus" 2>/dev/null || echo 0)
xcodebuild -project nucleus.xcodeproj -scheme nucleus -destination "platform=iOS,id=$DEV" -derivedDataPath "$DD" -configuration Debug -allowProvisioningUpdates build > /tmp/nucleus-device-build.log 2>&1 || { tail -20 /tmp/nucleus-device-build.log; exit 1; }
AFTER=$(stat -f %m "$DD/Build/Products/Debug-iphoneos/nucleus.app/nucleus")
[ "$AFTER" -gt "$BEFORE" ] || { echo "the binary did not change; not installing"; exit 1; }
echo "built $STAMP"
for i in $(seq 1 120); do
  running=$(xcrun devicectl device info processes --device $DEV 2>/dev/null | grep -c "nucleus.app/nucleus" || true)
  if [ "$running" = "0" ]; then
    xcrun devicectl device install app --device $DEV "$DD/Build/Products/Debug-iphoneos/nucleus.app" 2>&1 | grep -iE "installed|error" | head -1
    echo "installed $STAMP at $(date '+%H:%M:%S') while he was out of the app; not launched"
    exit 0
  fi
  sleep 30
done
echo "he stayed in the app for an hour; not installed"
