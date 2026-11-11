#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Run this command on the MacBook. Xcode is required for iOS builds."
  exit 1
fi

if ! command -v xcodebuild >/dev/null 2>&1; then
  echo "Install and open Xcode once, then rerun npm run ios:setup."
  exit 1
fi

npm install @capacitor/core @capacitor/ios --save
npm install @capacitor/cli --save-dev

if [[ ! -d ios ]]; then
  npx cap add ios
fi

npm run build
npx cap sync ios

plist="ios/App/App/Info.plist"
/usr/libexec/PlistBuddy -c "Add :NSCameraUsageDescription string GroundsOps uses the camera to capture job site photos." "$plist" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :NSPhotoLibraryUsageDescription string GroundsOps uses your photo library for site photos, company logos, and documents." "$plist" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :NSPhotoLibraryAddUsageDescription string GroundsOps can save exported images and documents to your library." "$plist" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :NSLocationWhenInUseUsageDescription string GroundsOps uses your location for job routes and nearby properties." "$plist" 2>/dev/null || true

npx cap open ios
