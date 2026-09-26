#!/usr/bin/env python3
"""E2E smoke: full content.js applied to a realistic en-US AI-era fixture.
Asserts after apply(): results column, pill and tabs are centered; the AI
panel is not double-shifted (no element containing #center_col/pill/tabs is
translated). Requires the real manifest/content — run headless, no network.
"""
import json, os, sys, time, subprocess, urllib.request, urllib.error

CONTENT_JS = "/home/agentuser/Projects/firefox-google-center/content.js"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 4493
BASE = f"http://127.0.0.1:{PORT}"

env = dict(os.environ)
for k in ("HTTP_PROXY","HTTPS_PROXY","http_proxy","https_proxy","ALL_PROXY","all_proxy"): env.pop(k, None)
proc = subprocess.Popen(["geckodriver","--port",str(PORT),"--log","error"], env=env,
                        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
time.sleep(2)

def req(method, path, body=None):
    r = urllib.request.Request(BASE+path, method=method, headers={"Content-Type":"application/json"})
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(r, data=data, timeout=60) as resp:
            raw = resp.read()
            try: return json.loads(raw) if raw else {}
            except Exception: return {"raw": raw[:200].decode(errors="replace")}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try: return json.loads(raw) if raw else {"error": e.code}
        except Exception: return {"error": e.code, "raw": raw[:200].decode(errors="replace")}

res = req("POST", "/session", {"capabilities":{"alwaysMatch":{"moz:firefoxOptions":{"args":["-headless"]}}}})
sid = res.get("value",{}).get("sessionId") or res.get("sessionId")
print("sid:", sid)
def cmd(m, p, b=None): return req(m, f"/session/{sid}{p}", b)

try: cmd("POST","/window/rect", {"width": 2560, "height": 1440, "x":0, "y":0})
except Exception: pass
cmd("POST","/url", {"url": "about:blank"})
time.sleep(2)

SHOT = r"""
window.__e2e = function () {
  var html = `
    <div id="hdr" style="position:relative;width:2560px">
      <div class="pillrow" id="pillrow" style="width:861px">
        <div id="searchform"><div class="RNNXgb" role="combobox" style="width:861px;height:44px" aria-label="Search"></div></div>
      </div>
      <div class="tabrow" role="navigation" style="width:861px;display:flex">
        <span class="beZ0tf">All</span><span class="beZ0tf">Images</span><span class="beZ0tf">Videos</span><span class="beZ0tf">Shopping</span><span class="beZ0tf">News</span>
      </div>
    </div>
    <div id="gridwrap" style="position:relative;display:grid;grid-template-columns:100px 652px 1fr">
      <div></div>
      <div id="center_col" style="width:652px">
        <div class="aipanel" style="width:652px"><h2 style="width:160px">AI Overview</h2><div style="height:90px;width:652px">AI summary</div></div>
        <div class="result" style="width:652px;height:70px">result one</div>
        <div class="result" style="width:652px;height:70px">result two</div>
      </div>
      <div></div>
    </div>`;
  document.body.innerHTML = html;
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width), t:Math.round(r.top)}; }
  var before = {col: rr(document.getElementById('center_col')), pill: rr(document.querySelector('#searchform .RNNXgb')), tabs: rr(document.querySelector('.tabrow'))};
  return JSON.stringify({before: before});
}"""
cmd("POST","/execute/sync",{"script":SHOT,"args":[]})
r = cmd("POST","/execute/sync",{"script":"return JSON.stringify(window.__e2e())","args":[]})
print("BEFORE:", r.get("value"))

# load full content.js (all of it, including apply + observers) — strip nothing
src = open(CONTENT_JS).read().replace('"use strict";\n', "", 1)
cmd("POST","/execute/sync",{"script":"window.__full="+json.dumps(src)+";","args":[]})
RUN = r"""
window.__run = function () {
  try { (0, eval)(window.__full); } catch(e) { return JSON.stringify({evalErr: e.message}); }
  if (typeof apply !== 'function') return JSON.stringify({err: 'apply missing'});
  apply();
  return JSON.stringify({applied: true});
}"""
cmd("POST","/execute/sync",{"script":RUN,"args":[]})
r = cmd("POST","/execute/sync",{"script":"return JSON.stringify(window.__run())","args":[]})
print("APPLY:", r.get("value"))
time.sleep(1)

HECK = r"""
window.__check = function () {
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width), t:Math.round(r.top)}; }
  var vw = document.documentElement.clientWidth;
  var col = document.getElementById('center_col');
  var pill = document.querySelector('#searchform .RNNXgb');
  var tabs = document.querySelector('.tabrow');
  var ai = null;
  var all = document.querySelectorAll('div,span,h1,h2,h3');
  for (var i=0;i<all.length;i++){ var e=all[i]; if(e.children.length>3) continue;
    if ((e.textContent||'').trim()==='AI Overview' && e.tagName==='H2'){ai=e.parentElement;break;} }
  out = {
    vw: vw, center: Math.round(vw/2),
    col: rr(col), pill: rr(pill), tabs: rr(tabs), ai: rr(ai),
    colTf: col?getComputedStyle(col).transform:null,
    pillTf: pill?getComputedStyle(pill).transform:null,
    aiTf: ai?getComputedStyle(ai).transform:null,
    colStyle: col?(col.getAttribute('style')||''):null,
  };
  out.colOK = out.col ? Math.abs(out.col.l + out.col.w/2 - out.center) <= 6 : null;
  out.pillOK = out.pill ? Math.abs(out.pill.l + out.pill.w/2 - out.center) <= 6 : null;
  out.tabsOK = out.tabs ? Math.abs(out.tabs.l + out.tabs.w/2 - out.center) <= 6 : null;
  out.aiOK = out.ai ? Math.abs(out.ai.l + out.ai.w/2 - out.center) <= 6 : null;
  return JSON.stringify(out);
}"""
cmd("POST","/execute/sync",{"script":HECK,"args":[]})
r = cmd("POST","/execute/sync",{"script":"return JSON.stringify(window.__check())","args":[]})
print("AFTER:", r.get("value"))

cmd("DELETE","")
proc.terminate(); time.sleep(1)