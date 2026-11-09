#!/bin/sh
# Builds the Linux package into linux/out/. Run from anywhere.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(dirname "$HERE")
OUT="$HERE/out"; STAGE="$OUT/stage"
rm -rf "$STAGE"; mkdir -p "$STAGE"
cp -a "$HERE/pkg/." "$STAGE/"
LIB="$STAGE/usr/lib/russian-study-tools"
cp "$ROOT"/app/*.html "$ROOT"/app/*.js "$ROOT"/app/*.svg "$LIB/"
cp "$HERE/launcher.py" "$LIB/"
VER=$(sed -n 's/^Version: //p' "$STAGE/DEBIAN/control")
dpkg-deb --root-owner-group --build "$STAGE" "$OUT/tetrad-studio_${VER}_all.deb"
echo "Built $OUT/tetrad-studio_${VER}_all.deb"
