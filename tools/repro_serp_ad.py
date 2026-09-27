#!/usr/bin/env python3
"""Anti-detection SERP capture: geckodriver Firefox with the webdriver flag
hidden (dom.webdriver.enabled=false) and a REAL window on Xvfb instead of
-headless. Everything else identical to repro_serp.py.

Usage: repro_serp_ad.py <url> [width] [port] [profile]
"""
import json, os, sys, time, subprocess, urllib.request, urllib.error

URL = sys.argv[1]
W = int(sys.argv[2]) if len(sys.argv) > 2 else 2315
PORT = int(sys.argv[3]) if len(sys.argv) > 3 else 4481
PROFILE = sys.argv[4] if len(sys.argv) > 4 else "/home/agentuser/fx-profiles/wdfix"
XPI = "/home/agentuser/Projects/firefox-google-center/web-ext-artifacts/google_search_centered-1.0.3.zip"
BASE = f"http://127.0.0.1:{PORT}"

env = dict(os.environ)
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    env.pop(k, None)
env["DISPLAY"] = ":99"  # Xvfb — real (non-headless) Firefox
opts = ["-no-remote"]
if os.path.isdir(PROFILE):
    opts += ["-profile", PROFILE]
proc = subprocess.Popen(["geckodriver", "--port", str(PORT), "--log", "error"], env=env,
                        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

def req(method, path, body=None):
    r = urllib.request.Request(BASE + path, method=method, headers={"Content-Type": "application/json"})
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(r, data=data, timeout=120) as resp:
            raw = resp.read()
            try:
                return json.loads(raw) if raw else {}
            except Exception:
                return {"raw": raw[:200].decode(errors="replace")}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return json.loads(raw) if raw else {"error": e.code}
        except Exception:
            return {"error": e.code, "raw": raw[:300].decode(errors="replace")}

for _ in range(40):
    try:
        with urllib.request.urlopen(BASE + "/status", timeout=3) as r:
            if r.status == 200:
                break
    except Exception:
        time.sleep(0.5)

res = req("POST", "/session", {"capabilities": {"alwaysMatch": {"moz:firefoxOptions": {"args": opts}}}})
sid = (res.get("value") or {}).get("sessionId") or res.get("sessionId")
if not sid:
    print("SESSION FAILED:", json.dumps(res)[:400]); proc.terminate(); sys.exit(1)
print("sid:", sid, "| profile:", os.path.basename(PROFILE), "| width:", W, "| DISPLAY=:99 (windowed)")

def cmd(m, p, b=None):
    return req(m, f"/session/{sid}{p}", b)

try:
    addon = cmd("POST", "/moz/addon/install", {"path": XPI, "temporary": True})
    print("addon:", json.dumps(addon)[:200])
except Exception as e:
    print("addon install err:", e)

try:
    cmd("POST", "/window/rect", {"width": W, "height": 1500, "x": 0, "y": 0})
except Exception as e:
    print("rect err:", e)

time.sleep(2)
cmd("POST", "/url", {"url": URL})
time.sleep(14)

MEASURE = r"""
window.__m = function () {
  var vw = document.documentElement.clientWidth;
  var out = {clientW: vw, center: Math.round(vw/2), url: location.href.slice(0,120),
             title: document.title.slice(0,60), wd: navigator.webdriver,
             isSorry: /\/sorry/.test(location.href) || /unusual traffic/i.test(document.body.innerText||'')};
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width), t:Math.round(r.top),
            h:Math.round(r.height), tf:getComputedStyle(e).transform}; }
  var col = document.getElementById('center_col');
  out.col = rr(col);
  if (col) {
    out.colInline = {gridColumn: col.style.gridColumn, width: col.style.width,
                     ml: col.style.marginLeft, mr: col.style.marginRight};
    out.colComputed = {gridColumn: getComputedStyle(col).gridColumn,
                       ml: getComputedStyle(col).marginLeft, mr: getComputedStyle(col).marginRight};
  }
  var rhs = document.getElementById('rhs');
  if (rhs) {
    var cs = getComputedStyle(rhs);
    out.rhs = rr(rhs);
    out.rhsVisible = (cs.display !== 'none' && cs.visibility !== 'hidden' && rhs.getBoundingClientRect().width > 0);
  } else { out.rhs = null; out.rhsVisible = false; }
  out.rcnt = rr(document.getElementById('rcnt'));
  out.pill = rr(document.querySelector('#searchform .A8SBwf, #searchform div[role="combobox"], #searchform .RNNXgb'));
  out.hdtb = rr(document.getElementById('hdtb'));
  var LABELS=["Modo IA","AI Mode","Tudo","All","Imagens","Images","Vídeos","Videos","Shopping","Notícias","News","Maps","Livros","Books","Web","Fórum","Forums","Mais","More","Ferramentas","Tools"];
  var hits=[], all=document.querySelectorAll('a,span,div,button');
  for (var i=0;i<all.length;i++){ var e=all[i]; if(e.children.length>2) continue;
    var t=(e.textContent||'').trim();
    if(t.length<=16 && LABELS.indexOf(t)!==-1){ var r=e.getBoundingClientRect();
      if(r.width>5&&r.height>5&&r.top<320) hits.push([t,Math.round(r.left),Math.round(r.top),Math.round(r.width)]); } }
  out.tabHits = hits.slice(0,14);
  out.aiText = !!(document.body.innerText||'').match(/AI Overview|Visão geral criada por IA/);
  var blocks=[];
  if (col) {
    for (var j=0;j<col.children.length;j++){
      var c=col.children[j]; var r=c.getBoundingClientRect();
      blocks.push({tag:c.tagName, id:c.id||'', cls:(typeof c.className==='string'?c.className:'').slice(0,40),
                   l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width), t:Math.round(r.top), h:Math.round(r.height)});
    }
  }
  out.colBlocks = blocks.slice(0,14);
  var about=[];
  for (var k=0;k<all.length;k++){ var e=all[k]; if(e.children.length>1) continue;
    var t=(e.textContent||'').trim();
    if(/^(About|Sobre)\b/.test(t) && t.length<60){ var r=e.getBoundingClientRect();
      if(r.top<2000 && r.width>10) about.push([t.slice(0,40),Math.round(r.left),Math.round(r.top),Math.round(r.width)]); } }
  out.aboutHits = about.slice(0,10);
  var imgs=document.querySelectorAll('img');
  var topImgs=[];
  for (var m=0;m<imgs.length;m++){ var r=imgs[m].getBoundingClientRect();
    if(r.top<1600 && r.width>60 && r.height>60) topImgs.push([Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)]); }
  out.topImages = {count: topImgs.length, sample: topImgs.slice(0,10)};
  return JSON.stringify(out);
}"""
cmd("POST", "/execute/sync", {"script": MEASURE, "args": []})
r = cmd("POST", "/execute/sync", {"script": "return JSON.stringify(window.__m())", "args": []})
print("MEASURE:", r.get("value"))
try:
    cmd("DELETE", "")
except Exception:
    pass
proc.terminate()
time.sleep(1)