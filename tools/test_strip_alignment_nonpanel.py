#!/usr/bin/env python3
"""REGRESSION: full-bleed rows' nested zone-grids must center on NO-PANEL pages too.

Live capture 2026-09-28 (pt "banana marrom", 2290px, add-on 1.0.8):
  #rhs absent -> the colSpan mode centers #center_col (grid-column 1/-1 +
  width + auto margins) but never touches #rcnt's tracks. The images strip
  lives in a full-bleed .bzXtMb row whose NESTED ghost grid keeps the native
  template: its content (.Kevs9 stripped at 2/-2) sits at [230..1330] (c=780)
  while the viewport center is 1145 -> off by -365. Same for the footer row.

Fixture: wide viewport, no knowledge panel, native 22-track grid, a
full-bleed row with a nested ghost grid + 2/-2 content.

Asserts after apply():
  - #center_col centered (colSpan mode),
  - the strip CONTENT centered on the viewport.
RED on 1.0.8, GREEN with the fix. Headless geckodriver, no network.
"""
import json, os, sys, time, subprocess, urllib.request, urllib.error

CONTENT_JS = "/home/agentuser/Projects/firefox-google-center/content.js"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 4499
WIN_W = 2560
BASE = f"http://127.0.0.1:{PORT}"

env = dict(os.environ)
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    env.pop(k, None)
proc = subprocess.Popen(["geckodriver", "--port", str(PORT), "--log", "error"], env=env,
                        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
time.sleep(2)

def req(method, path, body=None):
    r = urllib.request.Request(BASE + path, method=method, headers={"Content-Type": "application/json"})
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(r, data=data, timeout=60) as resp:
            raw = resp.read()
            try:
                return json.loads(raw) if raw else {}
            except Exception:
                return {"raw": raw[:300].decode(errors="replace")}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return json.loads(raw) if raw else {"error": e.code}
        except Exception:
            return {"error": e.code, "raw": raw[:300].decode(errors="replace")}

res = req("POST", "/session", {"capabilities": {"alwaysMatch": {"moz:firefoxOptions": {"args": ["-headless", "-no-remote"]}}}})
sid = (res.get("value") or {}).get("sessionId") or res.get("sessionId")
if not sid:
    print("SESSION FAILED:", json.dumps(res)[:300]); proc.terminate(); sys.exit(1)
print("sid:", sid)
def cmd(m, p, b=None):
    return req(m, f"/session/{sid}{p}", b)

try:
    cmd("POST", "/window/rect", {"width": WIN_W, "height": 1400, "x": 0, "y": 0})
except Exception:
    pass
cmd("POST", "/url", {"url": "about:blank"})
time.sleep(2)

FIXTURE = r"""
window.__fixture = function () {
  document.body.style.margin = '0';
  document.body.innerHTML = `
    <style>
      #rcnt { display:grid; grid-template-columns:210px repeat(20,36px) minmax(0,1fr); column-gap:20px; width:100%; }
      .bzXtMb { grid-column: 1 / -1; height:400px; }
      .ghostgrid { display:grid; grid-template-columns:210px repeat(20,36px) minmax(0,1fr); column-gap:20px; }
      .stripcontent { grid-column: 2 / -2; height:360px; }
      #center_col { grid-column: 1 / -1; height:600px; }
    </style>
    <div id="hdr" style="width:100%">
      <div id="searchform"><div class="RNNXgb" role="combobox" style="width:861px;height:44px" aria-label="Search"></div></div>
      <div class="tabrow" role="navigation" style="width:861px;display:flex">
        <span class="beZ0tf">Tudo</span><span class="beZ0tf">Imagens</span><span class="beZ0tf">Vídeos</span>
      </div>
    </div>
    <div id="rcnt">
      <div class="bzXtMb"><div class="YNk70c EjQTId ghostgrid"><div class="Kevs9 stripcontent">Imagens banana marrom</div></div></div>
      <div id="center_col">
        <div class="result" style="height:70px">result one</div>
        <div class="result" style="height:70px">result two</div>
      </div>
    </div>`;
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width), c:Math.round(r.left + r.width/2)}; }
  return JSON.stringify({
    vw: document.documentElement.clientWidth,
    col: rr(document.getElementById('center_col')),
    strip: rr(document.querySelector('.bzXtMb')),
    stripContent: rr(document.querySelector('.stripcontent')),
  });
}
"""
cmd("POST", "/execute/sync", {"script": FIXTURE, "args": []})
r = cmd("POST", "/execute/sync", {"script": "return window.__fixture()", "args": []})
print("BEFORE:", r.get("value"))

src = open(CONTENT_JS).read().replace('"use strict";\n', "", 1)
cmd("POST", "/execute/sync", {"script": "window.__full=" + json.dumps(src) + ";", "args": []})
RUN = r"""
window.__run = function () {
  try { (0, eval)(window.__full); } catch (e) { return JSON.stringify({evalErr: e.message}); }
  if (typeof apply !== 'function') return JSON.stringify({err: 'apply missing'});
  apply(); apply();
  return JSON.stringify({applied: true});
}
"""
cmd("POST", "/execute/sync", {"script": RUN, "args": []})
r = cmd("POST", "/execute/sync", {"script": "return window.__run()", "args": []})
print("APPLY:", r.get("value"))
time.sleep(1)

CHECK = r"""
window.__check = function () {
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width), c:Math.round(r.left + r.width/2)}; }
  var vw = document.documentElement.clientWidth, center = Math.round(vw/2);
  var col = rr(document.getElementById('center_col'));
  var strip = rr(document.querySelector('.bzXtMb'));
  var sc = rr(document.querySelector('.stripcontent'));
  var out = {vw: vw, center: center, col: col, strip: strip, stripContent: sc,
             colOff: col ? Math.round(col.c - center) : null,
             stripContentOff: sc ? Math.round(sc.c - center) : null,
             stripSpans: strip ? (strip.l <= 1 && strip.r >= vw - 1) : null};
  out.colOK = out.colOff !== null && Math.abs(out.colOff) <= 6;
  out.stripSpansOK = out.stripSpans === true;
  out.stripContentOK = out.stripContentOff !== null && Math.abs(out.stripContentOff) <= 6;
  out.PASS = out.colOK && out.stripSpansOK && out.stripContentOK;
  return JSON.stringify(out);
}
"""
cmd("POST", "/execute/sync", {"script": CHECK, "args": []})
r = cmd("POST", "/execute/sync", {"script": "return window.__check()", "args": []})
print("AFTER:", r.get("value"))
try:
    d = json.loads(r.get("value"))
    print("\nVERDICT:", "GREEN (PASS)" if d.get("PASS") else "RED (FAIL)")
    print("  col off:", d.get("colOff"), "px | strip full-bleed:", d.get("stripSpans"),
          "| strip CONTENT off:", d.get("stripContentOff"), "px")
except Exception as e:
    print("verdict parse err:", e)

cmd("DELETE", "")
proc.terminate()
time.sleep(1)
