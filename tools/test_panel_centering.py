#!/usr/bin/env python3
"""REGRESSION: the knowledge-panel ("About + photos") layout must still center.

Fixture replicates the en "banana" SERP captured live at 2327px:
  #rcnt = display:grid, tracks [210px, 36px x20, 1fr], column-gap 20px
  #center_col  = grid-column: 2 / span 12      -> 652px wide, left-hugging
  #rhs         = grid-column: span 7 / -2      -> 372px "About" knowledge panel
  photo strip  = grid-column: 1 / -1           -> full-bleed
Google dumps all leftover width into the LAST track, so on wide screens the
whole content block (column + panel) hugs the left edge; v1.0.3 bails out
entirely whenever #rhs is visible, so nothing centers at all.

Asserts after apply():
  - the col+panel block is centered on the viewport,
  - the search pill and the tabs row are centered,
  - the full-bleed photo strip still spans the whole viewport.
RED on 1.0.3, GREEN with the fix. Headless geckodriver, no network.
"""
import json, os, sys, time, subprocess, urllib.request, urllib.error

CONTENT_JS = "/home/agentuser/Projects/firefox-google-center/content.js"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 4494
WIN_W = 2327
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
      .entityhdr { grid-column: 2 / -2; height:60px; }
      .photos { grid-column: 1 / -1; height:80px; }
      #center_col { grid-column: 2 / span 12; }
      #rhs { grid-column: span 7 / -2; }
    </style>
    <div id="hdr" style="width:100%">
      <div id="searchform"><div class="RNNXgb" role="combobox" style="width:861px;height:44px" aria-label="Search"></div></div>
      <div class="tabrow" role="navigation" style="width:861px;display:flex">
        <span class="beZ0tf">All</span><span class="beZ0tf">Images</span><span class="beZ0tf">Videos</span><span class="beZ0tf">Shopping</span><span class="beZ0tf">News</span>
      </div>
    </div>
    <div id="rcnt">
      <div class="entityhdr">Banana &middot; Fruit</div>
      <div class="photos">photos</div>
      <div id="center_col">
        <div class="result" style="height:70px">result one</div>
        <div class="result" style="height:70px">result two</div>
        <div class="result" style="height:70px">result three</div>
      </div>
      <div id="rhs">
        <div style="height:120px">About</div>
        <div style="height:120px">Description</div>
      </div>
    </div>`;
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width)}; }
  return JSON.stringify({
    vw: document.documentElement.clientWidth,
    col: rr(document.getElementById('center_col')),
    rhs: rr(document.getElementById('rhs')),
    hdr: rr(document.querySelector('.entityhdr')),
    pill: rr(document.querySelector('#searchform .RNNXgb')),
    tabs: rr(document.querySelector('.tabrow')),
    photos: rr(document.querySelector('.photos')),
    rcntCols: getComputedStyle(document.getElementById('rcnt')).gridTemplateColumns.slice(0, 60),
  });
}"""
cmd("POST", "/execute/sync", {"script": FIXTURE, "args": []})
r = cmd("POST", "/execute/sync", {"script": "return window.__fixture()", "args": []})
print("BEFORE:", r.get("value"))

src = open(CONTENT_JS).read().replace('"use strict";\n', "", 1)
cmd("POST", "/execute/sync", {"script": "window.__full=" + json.dumps(src) + ";", "args": []})
RUN = r"""
window.__run = function () {
  try { (0, eval)(window.__full); } catch (e) { return JSON.stringify({evalErr: e.message}); }
  if (typeof apply !== 'function') return JSON.stringify({err: 'apply missing'});
  apply();
  return JSON.stringify({applied: true});
}"""
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
  var rhs = rr(document.getElementById('rhs'));
  var pill = rr(document.querySelector('#searchform .RNNXgb'));
  var tabs = rr(document.querySelector('.tabrow'));
  var photos = rr(document.querySelector('.photos'));
  var pair = null;
  if (col && rhs) {
    var l = Math.min(col.l, rhs.l), r = Math.max(col.r, rhs.r);
    pair = {l:l, r:r, w:r-l, c:Math.round((l+r)/2), off: Math.round((l+r)/2 - center)};
  }
  function off(b){ return b ? Math.round(b.c - center) : null; }
  var out = {vw: vw, center: center, col: col, rhs: rhs, pair: pair,
             pill: pill, tabs: tabs, photos: photos,
             colOff: off(col), pillOff: off(pill), tabsOff: off(tabs),
             pairOff: pair ? pair.off : null,
             photosSpans: photos ? (photos.l <= 1 && photos.r >= vw - 1) : null};
  out.pairOK = out.pairOff !== null && Math.abs(out.pairOff) <= 6;
  out.pillOK = out.pillOff !== null && Math.abs(out.pillOff) <= 6;
  out.tabsOK = out.tabsOff !== null && Math.abs(out.tabsOff) <= 6;
  out.photosOK = out.photosSpans === true;
  out.PASS = out.pairOK && out.pillOK && out.tabsOK && out.photosOK;
  return JSON.stringify(out);
}"""
cmd("POST", "/execute/sync", {"script": CHECK, "args": []})
r = cmd("POST", "/execute/sync", {"script": "return window.__check()", "args": []})
print("AFTER:", r.get("value"))
try:
    d = json.loads(r.get("value"))
    print("\nVERDICT:", "GREEN (PASS)" if d.get("PASS") else "RED (FAIL)")
    print("  pair offset:", d.get("pairOff"), "px | pill:", d.get("pillOff"),
          "px | tabs:", d.get("tabsOff"), "px | photos full-bleed:", d.get("photosSpans"))
except Exception as e:
    print("verdict parse err:", e)

cmd("DELETE", "")
proc.terminate()
time.sleep(1)