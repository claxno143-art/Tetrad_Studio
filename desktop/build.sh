#!/bin/sh
# Builds the Windows installer and Mac zips into desktop/dist/.
# Needs Node 18+, and makensis (NSIS) for the Windows installer.
set -e
cd "$(dirname "$0")"
rm -rf app; mkdir app
cp ../app/*.html ../app/*.js ../app/*.svg app/
rm -f app/blank.html
npm install
npx electron-builder --win dir          # unpacked Windows app (icon set by afterPack.js)
(cd build && makensis -V1 installer.nsi) # Windows installer
npx electron-builder --mac              # Mac zips (arm64 and x64)
ls -la dist
