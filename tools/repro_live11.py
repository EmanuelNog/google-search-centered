#!/usr/bin/env python3
"""Live measure: query with AI overview vs without (banana). Reports every
centering target + #rhs + overlap guard, with the published-git content.js
loaded as the real add-on."""
import json, os, sys, time, subprocess, urllib.request, urllib.error

URL = sys.argv[1]
W = int(sys.argv[2]) if len(sys.argv) > 2 else 2315
PORT = int(sys.argv[3]) if len(sys.argv) > 3 else 4495
BASE = f"http://127.0.0.1:{PORT}"
PROFILE = "/home/agentuser/fx-profiles/tst11"

env = dict(os.environ)
for k in ("HTTP_PROXY","HTTPS_PROXY","http_proxy","https_proxy","ALL_PROXY","all_proxy"): env.pop(k, None)
proc = subprocess.Popen(["geckodriver","--port",str(PORT),"--log","error"], env=env,
                        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
time.sleep(2)

def req(method, path, body=None):
    r = urllib.request.Request(BASE+path, method=method, headers={"Content-Type":"application/json"})
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(r, data=data, timeout=90) as resp:
            raw = resp.read()
            try: return json.loads(raw) if raw else {}
            except Exception: return {"raw": raw[:200].decode(errors="replace")}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try: return json.loads(raw) if raw else {"error": e.code}
        except Exception: return {"error": e.code, "raw": raw[:200].decode(errors="replace")}

res = req("POST", "/session", {"capabilities":{"alwaysMatch":{"moz:firefoxOptions":{"args":["-headless","-profile",PROFILE,"-no-remote"]}}}})
sid = res.get("value",{}).get("sessionId") or res.get("sessionId")
print("sid:", sid, "|", os.path.basename(URL))
def cmd(m, p, b=None): return req(m, f"/session/{sid}{p}", b)

cmd("POST","/moz/addon/install", {"path": "/home/agentuser/Projects/firefox-google-center/web-ext-artifacts/google_search_centered-1.0.3.zip", "temporary": True})
try: cmd("POST","/window/rect", {"width": W, "height": 1400, "x":0, "y":0})
except Exception as e: print("rect fail:", e)
time.sleep(2)
cmd("POST","/url", {"url": URL})
time.sleep(13)

MEASURE = r"""
window.__m = function () {
  var vw = document.documentElement.clientWidth;
  var out = {clientW: vw, center: Math.round(vw/2), url: location.href.slice(0,90), isCap: /sorry|captcha/i.test(document.title)};
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width), t:Math.round(r.top), tf:getComputedStyle(e).transform}; }
  out.col = rr(document.getElementById('center_col'));
  out.rhs = rr(document.getElementById('rhs'));
  out.pill = rr(document.querySelector('#searchform .A8SBwf, #searchform div[role="combobox"], #searchform .RNNXgb'));
  var AI=['Visão geral criada por IA','AI Overview'];
  var ah=[], all=document.querySelectorAll('div,span,h1,h2,h3');
  for(var i=0;i<all.length;i++){ var e=all[i]; if(e.children.length>3) continue;
    var t=(e.textContent||'').trim();
    if(AI.indexOf(t)!==-1){ var r0=e.getBoundingClientRect(); if(r0.width>5&&r0.height>5) ah.push({tag:e.tagName,w:Math.round(r0.width),cls:(typeof e.className==='string'?e.className:'').slice(0,30)}); } }
  out.aiHits = ah;
  // tabs row via content.js logic
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
      out.tabsRow={bucketTop:bt,rowLen:row.length,center:Math.round((minL+maxR)/2),bboxW:Math.round(maxR-minL),
        tabs:row.map(function(e){return (e.textContent||'').trim().slice(0,10);})};
    }
  }
  // overlap guard inputs: right-side header controls
  var g = Infinity, gEl=null;
  ['Settings','Google apps','Sign in'].forEach(function(l){
    var el=document.querySelector('[aria-label="'+l+'"]');
    if(el){ var g0=el.getBoundingClientRect().left; if(g0<g){g=g0;gEl=l;} }
  });
  if(!isFinite(g)){ var side=document.querySelector('#searchform .Q3DXx, #searchform .uZkjhb')||document.querySelector('#searchform > div > div:last-child');
    if(side) { g = side.getBoundingClientRect().left; gEl='fallback'; } }
  out.guard = isFinite(g)?{left:Math.round(g),el:gEl}:null;
  return JSON.stringify(out);
}"""
cmd("POST","/execute/sync",{"script":MEASURE,"args":[]})
r = cmd("POST","/execute/sync",{"script":"return JSON.stringify(window.__m())","args":[]})
print("MEASURE:", r.get("value"))
cmd("DELETE","")
proc.terminate(); time.sleep(1)