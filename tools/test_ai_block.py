#!/usr/bin/env python3
"""Regression test: getAiBlock must NEVER pick an element that contains (or is)
the search pill / tabs row / #center_col — translating such a container is the
double-transform that breaks the All tab (published 1.0.2 bug).

Cases (from live en-US + en-BR captures of the AI-era All tab):
  A. header chip: the FIRST exact-text "AI Overview" match is a small chip in
     an ancestor that also contains the search pill + tabs row.
  B. panel inside column: heading inside a 600px AI panel nested in #center_col.
  C. sibling panel: AI panel is a sibling of #center_col under a shared wrapper.
  D. no AI overview anywhere: must return null, no throw.
  E. stray label (footer link "AI Overview", no panel): must not be picked.
Invariants: result, when non-null, must not contain/or-be the pill, the tabs
row, or #center_col (otherwise apply() double-transforms them).
"""
import json, os, sys, time, subprocess, urllib.request, urllib.error

CONTENT_JS = "/home/agentuser/Projects/firefox-google-center/content.js"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 4488
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

src = open(CONTENT_JS).read()
cut = src.index("let colWidth = null")
funcs = src[:cut].replace('"use strict";\n', "", 1)
cmd("POST","/execute/sync",{"script":"window.__src="+json.dumps(funcs)+";","args":[]})

CASES = r"""
window.__cases = function () {
  (0, eval)(window.__src);
  var getAi = (typeof getAiBlock === 'function') ? getAiBlock : null;
  if (!getAi) return JSON.stringify({err: 'getAiBlock missing', hasOnWin: typeof window.getAiBlock});
  var results = [];

  function run(name, html) {
    document.body.innerHTML = html;
    var ai = getAi();
    var pill = document.querySelector('#searchform');
    var col = document.getElementById('center_col');
    var tabs = document.querySelector('.tabrow');
    var bad = false, why = [];
    if (ai) {
      if (ai.contains(pill) || ai === pill) { bad = true; why.push('pill'); }
      if (ai.contains(col) || ai === col) { bad = true; why.push('col'); }
      if (ai.contains(tabs) || ai === tabs) { bad = true; why.push('tabs'); }
    }
    results.push({case: name,
      picked: ai ? ((ai.id||'')+'|'+(typeof ai.className === 'string' ? ai.className : '').slice(0,24)+'|w'+Math.round(ai.getBoundingClientRect().width)) : null,
      bad: bad, why: why});
  }

  // A. header chip inside the pill+tabs container (first exact-text match)
  run('A.header-chip-in-pillrow',
    '<div id="pillrow"><div id="searchform"><div class="RNNXgb" style="width:800px;height:40px"></div></div>' +
    '<div class="chip" style="width:79px;height:18px">AI Overview</div>' +
    '<div class="tabrow" role="navigation" style="width:861px"><span>All</span><span>Images</span><span>Videos</span></div></div>' +
    '<div id="colwrap" style="width:652px"><div id="center_col" style="width:600px"><div class="result">r1</div></div></div>');

  // B. panel inside the centered column
  run('B.panel-inside-column',
    '<div id="pillrow"><div id="searchform" style="width:800px;height:40px"></div></div>' +
    '<div id="colwrap" style="width:600px"><div id="center_col" style="width:600px">' +
    '<div class="aipanel" style="width:600px"><h2 style="width:140px">AI Overview</h2><div style="height:60px">summary</div></div>' +
    '<div class="result">r1</div></div></div>');

  // C. sibling panel + column under a shared wrapper
  run('C.sibling-panel',
    '<div id="pillrow"><div id="searchform" style="width:800px;height:40px"></div></div>' +
    '<div id="sharedwrap" style="width:1200px">' +
    '<div class="aipanel" style="width:652px"><h2 style="width:140px">AI Overview</h2><div style="height:60px">summary</div></div>' +
    '<div id="center_col" style="width:652px"><div class="result">r1</div></div></div>');

  // D. no AI overview anywhere (plain All tab without it): must return null, no throw
  run('D.no-ai-overview',
    '<div id="pillrow"><div id="searchform" style="width:800px;height:40px"></div></div>' +
    '<div id="colwrap"><div id="center_col"><div class="result">r1</div></div></div>');

  // E. AI label elsewhere (footer link, NOT a panel)
  run('E.stray-label',
    '<div id="pillrow"><div id="searchform" style="width:800px;height:40px"></div></div>' +
    '<div id="colwrap"><div id="center_col"><div class="result">r1</div></div></div>' +
    '<div id="footer"><a>AI Overview</a></div>');

  return JSON.stringify(results);
}"""
r = cmd("POST","/execute/sync",{"script":CASES,"args":[]})
r = cmd("POST","/execute/sync",{"script":"return JSON.stringify(window.__cases())","args":[]})
print("VERDICT:", r.get("value"))

cmd("DELETE","")
proc.terminate(); time.sleep(1)