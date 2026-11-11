#!/usr/bin/env bash
# Build both packages from the SAME content.js.
#
#   Firefox  -> web-ext-artifacts/google_search_centered-<v>.zip  (manifest.json)
#   Chrome   -> dist/chrome/google_search_centered-<v>-chrome.zip  (manifest.chrome.json)
#   Unpacked -> dist/chrome-unpacked/  (for --load-extension / "Load unpacked")
#
# The two manifests differ only in packaging: Firefox needs the gecko id and the
# data-collection declaration, Chrome rejects nothing but warns on gecko keys.
# content.js is byte-identical in both, which is what makes the fixture suite
# meaningful across engines.
set -euo pipefail

cd "$(dirname "$0")/.."
V=$(python3 -c 'import json;print(json.load(open("manifest.json"))["version"])')
echo "building v$V"

mkdir -p web-ext-artifacts dist/chrome dist/chrome-unpacked
rm -rf dist/chrome-unpacked/* dist/chrome/*.zip

# --- Firefox (AMO / drag-and-drop) ---
rm -f "web-ext-artifacts/google_search_centered-$V.zip"
zip -q -r "web-ext-artifacts/google_search_centered-$V.zip" manifest.json content.js icons
echo "firefox: web-ext-artifacts/google_search_centered-$V.zip"

# --- Chrome (unpacked dir + store zip) ---
cp content.js dist/chrome-unpacked/
cp -r icons dist/chrome-unpacked/
cp manifest.chrome.json dist/chrome-unpacked/manifest.json
(cd dist/chrome-unpacked && zip -q -r "../chrome/google_search_centered-$V-chrome.zip" . -x '.*')
echo "chrome : dist/chrome/google_search_centered-$V-chrome.zip"
echo "unpacked: dist/chrome-unpacked/"

# --- sanity: the same content.js in both packages ---
python3 - "$V" <<'PY'
import hashlib, sys, zipfile
v = sys.argv[1]
fx = zipfile.ZipFile(f"web-ext-artifacts/google_search_centered-{v}.zip")
cr = zipfile.ZipFile(f"dist/chrome/google_search_centered-{v}-chrome.zip")
a = hashlib.sha256(fx.read("content.js")).hexdigest()
b = hashlib.sha256(cr.read("content.js")).hexdigest()
print("content.js identical in both packages:", a == b, a[:16])
if a != b:
    sys.exit("MISMATCH: packages carry different content.js")
PY
