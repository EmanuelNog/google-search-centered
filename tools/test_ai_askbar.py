#!/usr/bin/env python3
"""REGRESSION: the AI Overview module's bottom control (Ask-anything input bar) must be
centered together with the module on wide screens.

Live capture 2026-09-27 (en "what is a banana", 2327px, add-on 1.0.6):
  The AI Overview lives in a full-bleed .bzXtMb row; the module (1100 wide, centered
  by the existing AI-block logic) contains a bottom input bar (684 wide) that stays
  flush-LEFT inside the module: measured bar center 935 vs module center 1163
  (~228px left of center). User report: "show more button / ask anything is not
  centered".

Fixture: wide viewport, no knowledge panel, AI block (1100) left-hugged with an
"AI Overview" heading and a bottom ask bar (684). After apply():
  - the AI block is centered (existing behavior),
  - the ask bar is centered WITHIN the block (new behavior).
RED on 1.0.6, GREEN with the fix. Headless geckodriver, no network.
"""
import json, os, sys, time, subprocess, urllib.request, urllib.error

CONTENT_JS = "/home/agentuser/Projects/firefox-google-center/content.js"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 4498
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
    <div id="hdr" style="width:100%">
      <div id="searchform"><div class="RNNXgb" role="combobox" style="width:861px;height:44px" aria-label="Search"></div></div>
      <div class="tabrow" role="navigation" style="width:861px;display:flex">
        <span class="beZ0tf">All</span><span class="beZ0tf">Images</span><span class="beZ0tf">Videos</span>
      </div>
    </div>
    <div id="rcnt">
      <div id="aiblock" style="width:1100px;margin-left:100px;">
        <div class="aihdr" style="height:24px">AI Overview</div>
        <div style="height:300px">answer body</div>
        <div class="askwrap" style="width:684px;height:108px;">
          <input class="askinput" style="width:584px;height:24px" placeholder="Ask anything">
        </div>
        <div style="height:80px">disclaimer</div>
      </div>
    </div>`;
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width), c:Math.round(r.left + r.width/2)}; }
  return JSON.stringify({
    vw: document.documentElement.clientWidth,
    block: rr(document.getElementById('aiblock')),
    bar: rr(document.querySelector('.askwrap')),
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
  var block = rr(document.getElementById('aiblock'));
  var bar = rr(document.querySelector('.askwrap'));
  var out = {vw: vw, center: center, block: block, bar: bar,
             blockOff: block ? Math.round(block.c - center) : null,
             barOffInBlock: (block && bar) ? Math.round(bar.c - block.c) : null};
  out.blockOK = out.blockOff !== null && Math.abs(out.blockOff) <= 6;
  out.barOK = out.barOffInBlock !== null && Math.abs(out.barOffInBlock) <= 6;
  out.PASS = out.blockOK && out.barOK;
  return JSON.stringify(out);
}
"""
cmd("POST", "/execute/sync", {"script": CHECK, "args": []})
r = cmd("POST", "/execute/sync", {"script": "return window.__check()", "args": []})
print("AFTER:", r.get("value"))
try:
    d = json.loads(r.get("value"))
    print("\nVERDICT:", "GREEN (PASS)" if d.get("PASS") else "RED (FAIL)")
    print("  block off:", d.get("blockOff"), "px | bar center inside block:", d.get("barOffInBlock"), "px")
except Exception as e:
    print("verdict parse err:", e)

# ---- scenario 2: collapsed variant ending with a "Mostrar mais" pill ----
FIXTURE2 = r"""
window.__fixture2 = function () {
  document.body.innerHTML = `
    <div id="hdr" style="width:100%">
      <div id="searchform"><div class="RNNXgb" role="combobox" style="width:861px;height:44px" aria-label="Search"></div></div>
      <div class="tabrow" role="navigation" style="width:861px;display:flex">
        <span class="beZ0tf">Tudo</span><span class="beZ0tf">Imagens</span><span class="beZ0tf">Vídeos</span>
      </div>
    </div>
    <div id="rcnt">
      <div id="aiblock" style="width:1100px;margin-left:100px;">
        <div class="aihdr" style="height:24px">Visão geral criada por IA</div>
        <div style="height:200px">resposta</div>
        <div class="morerow" style="width:100%">
          <div class="morepill" style="width:650px;height:48px;display:block">
            <span class="morelabel">Mostrar mais</span>
          </div>
        </div>
      </div>
    </div>`;
  return 'ok';
}
"""
cmd("POST", "/url", {"url": "about:blank"})
time.sleep(2)
cmd("POST", "/execute/sync", {"script": "window.__full=" + json.dumps(src) + ";", "args": []})
cmd("POST", "/execute/sync", {"script": FIXTURE2, "args": []})
cmd("POST", "/execute/sync", {"script": "return window.__fixture2()", "args": []})
cmd("POST", "/execute/sync", {"script": RUN, "args": []})
r = cmd("POST", "/execute/sync", {"script": "return window.__run()", "args": []})
print("APPLY2:", r.get("value"))
time.sleep(1)

CHECK2 = r"""
window.__check2 = function () {
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width), c:Math.round(r.left + r.width/2)}; }
  var vw = document.documentElement.clientWidth, center = Math.round(vw/2);
  var block = rr(document.getElementById('aiblock'));
  var pill = rr(document.querySelector('.morepill'));
  var out = {vw: vw, center: center, block: block, pill: pill,
             blockOff: block ? Math.round(block.c - center) : null,
             pillOffInBlock: (block && pill) ? Math.round(pill.c - block.c) : null};
  out.blockOK = out.blockOff !== null && Math.abs(out.blockOff) <= 6;
  out.pillOK = out.pillOffInBlock !== null && Math.abs(out.pillOffInBlock) <= 6;
  out.PASS = out.blockOK && out.pillOK;
  return JSON.stringify(out);
}
"""
cmd("POST", "/execute/sync", {"script": CHECK2, "args": []})
r = cmd("POST", "/execute/sync", {"script": "return window.__check2()", "args": []})
print("AFTER2:", r.get("value"))
try:
    d2 = json.loads(r.get("value"))
    print("SCENARIO2:", "GREEN (PASS)" if d2.get("PASS") else "RED (FAIL)",
          "| block off:", d2.get("blockOff"), "| more-pill center in block:", d2.get("pillOffInBlock"))
except Exception as e:
    print("scenario2 parse err:", e)

# ---- scenario 3: user's variant — picked block EXCLUDES the control rows ----
FIXTURE3 = r"""
window.__fixture3 = function () {
  document.body.innerHTML = `
    <div id="hdr" style="width:100%">
      <div id="searchform"><div class="RNNXgb" role="combobox" style="width:861px;height:44px" aria-label="Search"></div></div>
      <div class="tabrow" role="navigation" style="width:861px;display:flex">
        <span class="beZ0tf">All</span><span class="beZ0tf">Images</span><span class="beZ0tf">Videos</span>
      </div>
    </div>
    <div id="rcnt">
      <div class="bzXtMb" style="height:420px;">
        <div class="modwrap" style="width:100%;">
          <div id="aiblock" style="width:1100px;margin-left:100px;">
            <div class="aihdr" style="height:24px">AI Overview</div>
            <div style="height:200px">answer</div>
          </div>
          <div class="morerow" style="width:764px;margin-left:100px;">
            <div class="pillwrap" style="width:762px;height:48px;">
              <span class="morelabel">Show more</span>
            </div>
          </div>
          <div class="askrow" style="width:684px;height:108px;margin-left:100px;">
            <input class="askinput" style="width:584px;height:24px" placeholder="Ask anything">
          </div>
        </div>
      </div>
      <div id="center_col" style="height:400px">results</div>
    </div>`;
  return 'ok';
}
"""
cmd("POST", "/url", {"url": "about:blank"})
time.sleep(2)
cmd("POST", "/execute/sync", {"script": "window.__full=" + json.dumps(src) + ";", "args": []})
cmd("POST", "/execute/sync", {"script": FIXTURE3, "args": []})
cmd("POST", "/execute/sync", {"script": "return window.__fixture3()", "args": []})
cmd("POST", "/execute/sync", {"script": RUN, "args": []})
r = cmd("POST", "/execute/sync", {"script": "return window.__run()", "args": []})
print("APPLY3:", r.get("value"))
time.sleep(1)

CHECK3 = r"""
window.__check3 = function () {
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width), c:Math.round(r.left + r.width/2)}; }
  var vw = document.documentElement.clientWidth, center = Math.round(vw/2);
  var block = rr(document.getElementById('aiblock'));
  var pill = rr(document.querySelector('.pillwrap'));
  var ask = rr(document.querySelector('.askrow'));
  var out = {vw: vw, center: center, block: block, pill: pill, ask: ask,
             blockOff: block ? Math.round(block.c - center) : null,
             pillOffInBlock: (block && pill) ? Math.round(pill.c - block.c) : null,
             askOffInBlock: (block && ask) ? Math.round(ask.c - block.c) : null};
  out.blockOK = out.blockOff !== null && Math.abs(out.blockOff) <= 6;
  out.pillOK = out.pillOffInBlock !== null && Math.abs(out.pillOffInBlock) <= 6;
  out.askOK = out.askOffInBlock !== null && Math.abs(out.askOffInBlock) <= 6;
  out.PASS = out.blockOK && out.pillOK && out.askOK;
  return JSON.stringify(out);
}
"""
cmd("POST", "/execute/sync", {"script": CHECK3, "args": []})
r = cmd("POST", "/execute/sync", {"script": "return window.__check3()", "args": []})
print("AFTER3:", r.get("value"))
try:
    d3 = json.loads(r.get("value"))
    print("SCENARIO3:", "GREEN (PASS)" if d3.get("PASS") else "RED (FAIL)",
          "| block off:", d3.get("blockOff"), "| pill in block:", d3.get("pillOffInBlock"),
          "| ask bar in block:", d3.get("askOffInBlock"))
except Exception as e:
    print("scenario3 parse err:", e)

cmd("DELETE", "")
proc.terminate()
time.sleep(1)
