#!/usr/bin/env python3
"""A/B: published 1.0.2 vs signed 1.0.1 on en-US AI-era All tab — positions + screenshot."""
import json, os, sys, time, subprocess, urllib.request, urllib.error, base64

XPI = sys.argv[1]
URL = sys.argv[2] if len(sys.argv) > 2 else "https://www.google.com/search?q=firefox+extension&hl=en"
W = int(sys.argv[3]) if len(sys.argv) > 3 else 2560
PORT = int(sys.argv[4]) if len(sys.argv) > 4 else 4446
BASE = f"http://127.0.0.1:{PORT}"

env = dict(os.environ)
for k in ("HTTP_PROXY","HTTPS_PROXY","http_proxy","https_proxy","ALL_PROXY","all_proxy"): env.pop(k, None)
proc = subprocess.Popen(["geckodriver","--port",str(PORT),"--log","error"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
time.sleep(2)

def req(method, path, body=None):
    r = urllib.request.Request(BASE+path, method=method, headers={"Content-Type":"application/json"})
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(r, data=data, timeout=60) as resp:
            raw = resp.read(); return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read(); return json.loads(raw) if raw else {"error": e.code}

res = req("POST", "/session", {"capabilities":{"alwaysMatch":{"moz:firefoxOptions":{"args":["-headless","-profile","/home/agentuser/fx-profiles/tst6"]}}}})
sid = res.get("value",{}).get("sessionId") or res.get("sessionId")
print("sid:", sid, "| xpi:", os.path.basename(XPI))
def cmd(m, p, b=None): return req(m, f"/session/{sid}{p}", b)

cmd("POST","/moz/addon/install", {"path": XPI, "temporary": True})
try: cmd("POST","/window/rect", {"width": W, "height": 1440, "x":0, "y":0})
except Exception as e: print("rect fail:", e)
time.sleep(2)
cmd("POST","/url", {"url": URL})
time.sleep(12)

MEASURE = r"""
window.__m = function () {
  var vw = document.documentElement.clientWidth;
  var out = {clientW: vw, center: Math.round(vw/2), col:null, pill:null, rhs:null, ai:null, tabsRow:null};
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width), t:Math.round(r.top), tf:getComputedStyle(e).transform}; }
  out.col = rr(document.getElementById('center_col'));
  out.rhs = rr(document.getElementById('rhs'));
  out.pill = rr(document.querySelector('#searchform .A8SBwf, #searchform div[role="combobox"], #searchform .RNNXgb'));
  var AI=['Visão geral criada por IA','AI Overview'];
  var all=document.querySelectorAll('div,span,h1,h2,h3'), heading=null;
  for(var i=0;i<all.length;i++){ var e=all[i]; if(e.children.length>3) continue;
    var t=(e.textContent||'').trim();
    if(AI.indexOf(t)!==-1){ var r0=e.getBoundingClientRect(); if(r0.width>5&&r0.height>5){heading=e;break;} } }
  if(heading){ var el=heading,best=null;
    for(var i=0;i<16&&el&&el!==document.body;i++,el=el.parentElement){
      var w=el.getBoundingClientRect().width; if(w>=vw*0.9)break; if(w>500)best=el; }
    out.ai = best?{r:rr(best), id:best.id, cls:(typeof best.className==='string'?best.className:'').slice(0,60)}:null;
  }
  // tabs row, content.js logic
  var LABELS=["Modo IA","AI Mode","Tudo","All","Imagens","Images","Videos","Videos","Shopping","Notícias","News","Maps","Livros","Books","Web","Fórum","Forums","Vídeos curtos","Short videos","Mais","More","Ferramentas","Tools"];
  var seen={}; all=document.querySelectorAll('a,span,div,button');
  for(var i=0;i<all.length;i++){ var e=all[i]; if(e.children.length>2)continue;
    var t=(e.textContent||'').trim();
    if(t.length<=16&&LABELS.indexOf(t)!==-1){ var r=e.getBoundingClientRect();
      if(r.width>5&&r.height>5&&r.top<300){ var p=seen[t]; if(!p||r.width*r.height>p.area) seen[t]={el:e,area:r.width*r.height}; } } }
  var labels=[]; for(var k in seen) labels.push(seen[k].el);
  if(labels.length>=2){ var buckets={};
    for(var j=0;j<labels.length;j++){ var tp=Math.round(labels[j].getBoundingClientRect().top/20)*20; (buckets[tp]=buckets[tp]||[]).push(labels[j]); }
    var row=[],bt=null; for(var b in buckets) if(buckets[b].length>row.length){row=buckets[b];bt=b;}
    if(row.length>=2){ var minL=Infinity,maxR=-Infinity;
      for(var m=0;m<row.length;m++){ var r2=row[m].getBoundingClientRect(); minL=Math.min(minL,r2.left); maxR=Math.max(maxR,r2.right); }
      out.tabsRow={bucketTop:bt,rowLen:row.length,center:Math.round((minL+maxR)/2),bboxW:Math.round(maxR-minL)};
    }
  }
  return JSON.stringify(out);
}"""
cmd("POST","/execute/sync",{"script":MEASURE,"args":[]})
r = cmd("POST","/execute/sync",{"script":"return JSON.stringify(window.__m())","args":[]})
print("MEASURE:", r.get("value"))

# layout variant detection (en-US legacy vs AI-era)
VAR = r"""
window.__v = function () {
  var out = {};
  out.hdtb = !!document.querySelector('#hdtb [role="navigation"]');
  out.beZ0tf = document.querySelectorAll('.beZ0tf').length;
  out.HTOhZ = document.querySelectorAll('.HTOhZ').length;
  out.aiModeTab = !!document.querySelector('a[href*="udm=2"], a[aria-label*="AI Mode"], button[aria-label*="AI Mode"]');
  out.lang = document.documentElement.lang;
  return JSON.stringify(out);
}"""
cmd("POST","/execute/sync",{"script":VAR,"args":[]})
r = cmd("POST","/execute/sync",{"script":"return JSON.stringify(window.__v())","args":[]})
print("VARIANT:", r.get("value"))

# screenshot
r = cmd("POST","/screenshot",{})
b64 = (r.get("value") or "")
if b64:
    p = f"/tmp/gsc_{os.path.basename(XPI).split('-')[0]}_{W}.png"
    open(p,"wb").write(base64.b64decode(b64))
    print("SHOT:", p, len(base64.b64decode(b64)), "bytes")
else:
    print("SHOT: none")

cmd("DELETE","")
proc.terminate(); time.sleep(1)