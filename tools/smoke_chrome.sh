#!/usr/bin/env bash
# End-to-end smoke test of the PACKAGED Chrome extension.
#
# Headless Chromium gets Google's /sorry wall (no cookie jar) exactly like
# geckodriver-Firefox, so this maps www.google.com to a local TLS server that
# serves a realistic SERP fixture. google.com is on Chrome's HSTS preload list,
# hence TLS + --ignore-certificate-errors: a plain HTTP server is silently
# upgraded to https:// and the DOM dump comes back empty.
#
# What it proves (the parts a fixture-eval suite cannot):
#   * manifest.chrome.json is accepted by Chrome's extension loader,
#   * the content script injects at document_start on a matching URL,
#   * it writes the centering transforms on a real page load.
# The fixture is served as /search.html: a bare /search has no extension, so
# SimpleHTTPRequestHandler answers application/octet-stream and Chromium
# downloads it instead of rendering (dump-dom then prints nothing). The match
# pattern is a prefix ("…/search*"), so /search.html still injects.
#
# Usage: tools/smoke_chrome.sh [PORT]
set -euo pipefail

cd "$(dirname "$0")/.."
PORT="${1:-8731}"
WORK="$HOME/.hermes/cache/scratch/chrome-smoke"
PROF="$HOME/.hermes/cache/scratch/chrome-smoke-prof"

[ -d dist/chrome-unpacked ] || { echo "run tools/build.sh first"; exit 1; }

rm -rf "$WORK" "$PROF"; mkdir -p "$WORK" "$PROF"

cat > "$WORK/search.html" <<'HTML'
<!doctype html><html><head><meta charset="utf-8"><title>fixture SERP</title>
<style>
  body { margin:0; font-family:sans-serif; }
  #rcnt { display:grid; grid-template-columns:210px repeat(20,36px) minmax(0,1fr);
          column-gap:20px; width:100%; }
  #center_col { grid-column: 2 / span 12; height:900px; }
</style></head>
<body>
  <div id="hdr" style="width:100%">
    <div id="searchform"><div class="RNNXgb" role="combobox" style="width:861px;height:44px"></div></div>
    <div class="tabrow" role="navigation" style="width:861px;display:flex">
      <span>All</span><span>Images</span><span>Videos</span>
    </div>
  </div>
  <div id="rcnt"><div id="center_col">results</div></div>
</body></html>
HTML

python3 - "$WORK" <<'PY'
import sys, os
work = sys.argv[1]
open(os.path.join(work, "serve.py"), "w").write('''
import http.server, ssl, sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
srv = http.server.HTTPServer(("127.0.0.1", int(sys.argv[1])), http.server.SimpleHTTPRequestHandler)
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain("cert.pem", "key.pem")
srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
srv.serve_forever()
''')
PY

openssl req -x509 -newkey rsa:2048 -nodes -days 2 \
  -keyout "$WORK/key.pem" -out "$WORK/cert.pem" \
  -subj "/CN=www.google.com" -addext "subjectAltName=DNS:www.google.com" >/dev/null 2>&1

python3 "$WORK/serve.py" "$PORT" >/dev/null 2>&1 &
SRV=$!
trap 'kill -9 $SRV 2>/dev/null || true' EXIT
sleep 1

curl -sk -o /dev/null -w "local google fixture: %{http_code}\n" "https://127.0.0.1:$PORT/search.html" || true

DOM=/home/agentuser/.hermes/cache/scratch/chrome-smoke-dom.html
timeout 90 /usr/bin/chromium --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
  --window-size=2560,1400 --user-data-dir="$PROF" \
  --ignore-certificate-errors --host-resolver-rules="MAP www.google.com 127.0.0.1" \
  --load-extension="$PWD/dist/chrome-unpacked" \
  --virtual-time-budget=5000 \
  --dump-dom "https://www.google.com:$PORT/search.html?q=fixture" > "$DOM" 2>/dev/null || true

echo "dom bytes: $(wc -c < "$DOM")"
FAIL=0
check() { # name, pattern
  if grep -qF "$2" "$DOM"; then echo "  GREEN $1"; else echo "  RED   $1 (missing: $2)"; FAIL=1; fi
}
check "content script injected" 'translateX('
check "results column centred" 'id="center_col" style="grid-column: 1 / -1;'
check "search pill moved"      'class="RNNXgb" role="combobox" style="width: 861px; height: 44px; transform: translateX('
check "tabs row moved"         'class="tabrow" role="navigation" style="width: 861px; display: flex; transform: translateX('

echo "--- transforms seen:"
grep -oE 'transform: translateX\(-?[0-9]+px\)' "$DOM" | sort | uniq -c || true
[ "$FAIL" -eq 0 ] && echo "chrome package: GREEN" || { echo "chrome package: RED"; exit 1; }
