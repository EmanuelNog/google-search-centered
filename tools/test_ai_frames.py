#!/usr/bin/env python3
"""REGRESSION: the AI module's bottom controls must move AS A FRAME.

Both user-reported bugs (2026-11-09) share one cause: getAiMore()/getAiBar()
picked the first ancestor merely *wider* than the label/input, which is often an
INNER wrapper (the hover-fill box around the "Show more" label, or the group
holding the "+" button and the textarea).  Translating that wrapper leaves the
control's own frame (its border / rounded bar) in place, so:

  bug 1 - hovering "Show more" lights a rounded box shifted to the right, the
          pill border stays where Google put it ("hover region looks centered");
  bug 2 - the ask-anything "+" and placeholder float ~285px inside the bar
          ("as if the input field was centered").

The fix: from the seed climb to the OUTERMOST ancestor that is still the
control's own frame - never a container that also holds the module heading,
never the block itself.  Then the frame and everything inside it move together.

Scenarios (headless geckodriver, about:blank, no network):
  1. collapsed: label < hoverwrap(500) < pill(760) < row(762) < module(1100)
     -> today the transform lands on .hoverwrap (RED).  Assertions after fix:
        the transform is on an ancestor of the pill, and the label keeps its
        offset from the pill (hover paint stays glued to the label), and the
        module is centered.
  2. expanded: textarea < innergroup(400) < barframe(780) < module(1100)
     -> today the transform lands on .innergroup (RED).  Assertions: the
        transform is on .barframe (or an ancestor), and the "+"/textarea keep
        their offset from the frame's left edge.

Run: python3 tools/test_ai_frames.py [PORT]
"""
import json, os, sys, time, subprocess, urllib.request, urllib.error

CONTENT_JS = "/home/agentuser/Projects/firefox-google-center/content.js"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 4508
WIN_W = 2560
BASE = f"http://127.0.0.1:{PORT}"

# Only Firefox Developer Edition is installed on this host (no /usr/bin/firefox).
FIREFOX_BIN = "/usr/lib/firefox-developer-edition/firefox"

env = dict(os.environ)
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    env.pop(k, None)
proc = subprocess.Popen(["geckodriver", "--port", str(PORT), "--log", "error"], env=env,
                        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
time.sleep(2)


def req(method, path, body=None):
    r = urllib.request.Request(BASE + path, method=method,
                               headers={"Content-Type": "application/json"})
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


res = req("POST", "/session", {"capabilities": {"alwaysMatch": {
    "moz:firefoxOptions": {"binary": FIREFOX_BIN, "args": ["-headless", "-no-remote"]}}}})
sid = (res.get("value") or {}).get("sessionId") or res.get("sessionId")
if not sid:
    print("SESSION FAILED:", json.dumps(res)[:300])
    proc.terminate()
    sys.exit(1)


def cmd(m, p, b=None):
    return req(m, f"/session/{sid}{p}", b)


try:
    cmd("POST", "/window/rect", {"width": WIN_W, "height": 1400, "x": 0, "y": 0})
except Exception:
    pass

SRC = open(CONTENT_JS).read().replace('"use strict";\n', "", 1)

LOAD = r"""
window.__load = function (src) {
  window.__full = src;
  try { (0, eval)(src); } catch (e) { return 'evalErr: ' + e.message; }
  if (typeof apply !== 'function') return 'apply missing';
  return 'ok';
}
"""
MEASURE = r"""
window.__clear = function () {
  var all = document.querySelectorAll('#rcnt *');
  for (var i = 0; i < all.length; i++) {
    if (all[i].style && all[i].style.transform) all[i].style.transform = '';
  }
  void document.body.getBoundingClientRect();
  return 'cleared';
}
window.__measure = function () {
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width),
            c:Math.round(r.left + r.width/2)}; }
  function tfOf(e){ return (e && e.style && e.style.transform) || ''; }
  var out = {}, vw = document.documentElement.clientWidth;
  out.vw = vw; out.center = Math.round(vw / 2);
  out.block = rr(document.getElementById('aiblock'));
  out.blockOff = out.block ? Math.round(out.block.c - out.center) : null;
  var pill = document.querySelector('.pill'), bar = document.querySelector('.barframe');
  var label = document.querySelector('.morelabel'), ta = document.querySelector('.askinput');
  out.pill = rr(pill); out.bar = rr(bar); out.label = rr(label); out.textarea = rr(ta);
  // who carries the transform?
  var tf = [];
  var all = document.querySelectorAll('#rcnt *');
  for (var i = 0; i < all.length; i++) {
    var t = tfOf(all[i]);
    if (t && t !== 'none') tf.push({cls: all[i].className || all[i].tagName, tf: t,
                                    inPill: pill ? pill.contains(all[i]) : false,
                                    inBar: bar ? bar.contains(all[i]) : false,
                                    isPill: all[i] === pill, isBar: all[i] === bar,
                                    box: rr(all[i])});
  }
  out.transformed = tf;
  // invariants: the label holds its offset from the pill, the textarea from the bar
  if (pill && label) out.labelOffInPill = Math.round(out.label.c - out.pill.c);
  if (bar && ta) out.taOffFromBarLeft = Math.round(out.textarea.l - out.bar.l);
  return JSON.stringify(out);
}
"""


def run_scenario(name, fixture, checks):
    cmd("POST", "/url", {"url": "about:blank"})
    time.sleep(1)
    cmd("POST", "/execute/sync", {"script": LOAD, "args": []})
    cmd("POST", "/execute/sync",
        {"script": "return window.__load(" + json.dumps(SRC) + ")", "args": []})
    cmd("POST", "/execute/sync", {"script": fixture, "args": []})
    cmd("POST", "/execute/sync", {"script": "return window.__fixture()", "args": []})
    cmd("POST", "/execute/sync", {"script": MEASURE, "args": []})
    # NATIVE baseline: the fixture is installed after the script auto-applies, and
    # the mutation observer may already have transformed things — strip every
    # inline transform, force layout, then measure.
    cmd("POST", "/execute/sync", {"script": "return window.__clear()", "args": []})
    before = json.loads(cmd("POST", "/execute/sync",
                            {"script": "return window.__measure()", "args": []})["value"])
    cmd("POST", "/execute/sync", {"script": "apply(); apply();", "args": []})
    time.sleep(0.5)
    after = json.loads(cmd("POST", "/execute/sync",
                           {"script": "return window.__measure()", "args": []})["value"])
    print(f"\n--- {name}")
    print("  vw", after["vw"], "block", after["block"], "blockOff", after["blockOff"])
    print("  before:", {k: before.get(k) for k in
                        ("pill", "bar", "label", "textarea", "labelOffInPill", "taOffFromBarLeft")})
    print("  after :", {k: after.get(k) for k in
                        ("pill", "bar", "label", "textarea", "labelOffInPill", "taOffFromBarLeft")})
    print("  transformed:", after["transformed"])
    return after, checks(after, before)


HDR = """
    <div id="hdr" style="width:100%">
      <div id="searchform"><div class="RNNXgb" role="combobox" style="width:861px;height:44px"></div></div>
      <div class="tabrow" role="navigation" style="width:861px;display:flex">
        <span>All</span><span>Images</span><span>Videos</span>
      </div>
    </div>"""

FIX1 = r"""
window.__fixture = function () {
  document.body.style.margin = '0';
  document.body.innerHTML = `
    <div id="rcnt" style="width:100%">
    <div id="aiblock" style="width:1100px;margin-left:100px;">
      <div class="aihdr" style="height:24px">AI Overview</div>
      <div style="height:300px">answer body</div>
      <div class="controlrow" style="width:762px;height:50px;">
        <div class="pill" style="width:760px;height:48px;border:1px solid #888;border-radius:24px;position:relative;">
          <div class="hoverwrap" style="width:500px;height:40px;margin:4px auto 0 auto;border-radius:20px;">
            <span class="morelabel">Show more</span>
          </div>
        </div>
      </div>
    </div>
    </div>`;
  return 'ok';
}
"""


def checks1(after, before):
    tf = after["transformed"]
    ok = {}
    ok["blockCentered"] = after["blockOff"] is not None and abs(after["blockOff"]) <= 6
    # the moved element must be the pill or an ancestor of it, never inside it
    ok["movedFrame"] = bool(tf) and any(t["isPill"] or not t["inPill"] for t in tf)
    ok["notInnerWrapper"] = not any(t["inPill"] and not t["isPill"] for t in tf)
    # the hover fill (and label) hold their position inside the pill
    ok["labelGlued"] = (after.get("labelOffInPill") is not None
                        and before.get("labelOffInPill") is not None
                        and abs(after["labelOffInPill"] - before["labelOffInPill"]) <= 2)
    ok["pillInsideBlock"] = (after["pill"] is not None and after["block"] is not None
                             and after["pill"]["r"] <= after["block"]["r"] + 2
                             and after["pill"]["l"] >= after["block"]["l"] - 2)
    print("  checks:", ok)
    return all(ok.values())


FIX2 = r"""
window.__fixture = function () {
  document.body.innerHTML = `
    <div id="rcnt" style="width:100%">
    <div id="aiblock" style="width:1100px;margin-left:100px;">
      <div class="aihdr" style="height:24px">AI Overview</div>
      <div style="height:300px">answer body</div>
      <div class="controlrow" style="width:780px;">
        <div class="barframe" style="width:780px;height:120px;border:1px solid #888;border-radius:60px;">
          <div class="innergroup" style="width:400px;height:60px;display:flex;align-items:center;">
            <div class="plusbtn" style="width:40px;height:40px;border-radius:20px;"></div>
            <textarea class="askinput" style="width:300px;height:24px" placeholder="Ask anything"></textarea>
          </div>
        </div>
      </div>
    </div>
    </div>`;
  return 'ok';
}
"""


def checks2(after, before):
    tf = after["transformed"]
    ok = {}
    ok["blockCentered"] = after["blockOff"] is not None and abs(after["blockOff"]) <= 6
    ok["frameMoved"] = bool(tf) and any(t["isBar"] or not t["inBar"] for t in tf)
    ok["notInnerGroup"] = not any(t["inBar"] and not t["isBar"] for t in tf)
    # the + button / textarea must keep their native inset inside the bar
    ok["contentGlued"] = (after.get("taOffFromBarLeft") is not None
                          and before.get("taOffFromBarLeft") is not None
                          and abs(after["taOffFromBarLeft"] - before["taOffFromBarLeft"]) <= 2)
    print("  checks:", ok)
    return all(ok.values())


r1 = run_scenario("scenario 1: collapsed pill, label inside a hover wrapper", FIX1, checks1)
r2 = run_scenario("scenario 2: expanded ask bar, +/textarea inside an inner group", FIX2, checks2)

print("\nVERDICT:", "GREEN (PASS)" if (r1[1] and r2[1]) else "RED (FAIL)")
cmd("DELETE", "")
proc.terminate()
time.sleep(1)
sys.exit(0 if (r1[1] and r2[1]) else 1)
