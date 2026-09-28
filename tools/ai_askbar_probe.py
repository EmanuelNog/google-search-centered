#!/usr/bin/env python3
"""Focused probe: AI-overview ask-bar centering — transforms, chains, native comparison.

Usage: ai_askbar_probe.py PORT URL
"""
import socket, json, sys, time

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 2828
URL = sys.argv[2] if len(sys.argv) > 2 else "https://www.google.com/search?q=what+is+a+banana&hl=en&gl=us"

def recv_msg(sock):
    buf = b""
    while b":" not in buf:
        c = sock.recv(1)
        if not c: raise ConnectionError("closed")
        buf += c
    n = int(buf.split(b":")[0]); data = b""
    while len(data) < n: data += sock.recv(n - len(data))
    return json.loads(data.decode())

def send_msg(sock, msg):
    data = json.dumps(msg).encode()
    sock.sendall(str(len(data)).encode() + b":" + data)

def cmd(sock, mid, name, params):
    send_msg(sock, [0, mid, name, params])
    ans = recv_msg(sock)
    if ans[2]: raise RuntimeError(f"{name}: {json.dumps(ans[2])[:300]}")
    return ans[3]

def run_js(s, mid, script):
    r = cmd(s, mid, "WebDriver:ExecuteScript", {"script": script, "args": []})
    d = r.get("value")
    for _ in range(3):
        if isinstance(d, str):
            try: d = json.loads(d)
            except Exception: break
        else: break
    return d

S = socket.create_connection(("127.0.0.1", PORT), timeout=30)
recv_msg(S)
try:
    cmd(S, 1, "WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
except RuntimeError as e:
    print("session:", str(e)[:150])

print("navigate:", json.dumps(cmd(S, 2, "WebDriver:Navigate", {"url": URL}))[:80])
time.sleep(15)

SETUP = r"""
window.__ab = function (mode) {
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width), t:Math.round(r.top), h:Math.round(r.height), c:Math.round(r.left+r.width/2)}; }
  function cls(e){ return String((e&&e.className)||'').slice(0,50); }
  function chain(e){ var a=[], n=e; for(var i=0;i<8&&n;i++,n=n.parentElement){
    a.push(n.tagName+(n.id?'#'+n.id:'')+'.'+cls(n)+(n.style&&n.style.transform?' [tf '+n.style.transform+']':'')); } return a; }
  var vw=document.documentElement.clientWidth, center=Math.round(vw/2);
  if (mode === 'native') {
    var all=document.querySelectorAll('*');
    for (var i=0;i<all.length;i++){ var e=all[i];
      if (e.style && e.style.transform) e.style.transform='';
      if (e.id==='center_col'){ e.style.gridColumn=''; e.style.width=''; e.style.marginLeft=''; e.style.marginRight=''; }
      if (e.id==='rcnt'){ e.style.gridTemplateColumns=''; }
    }
  }
  var out={vw:vw, center:center, mode:mode};
  // replicate getAiBlock's pick quickly: find 'AI Overview' heading, walk up
  var heading=null;
  var cands=document.querySelectorAll('div, span, h1, h2, h3');
  for (var j=0;j<cands.length;j++){ var e2=cands[j];
    if (e2.children.length>3) continue;
    var t=(e2.textContent||'').trim();
    if (t==='AI Overview'){ var r2=e2.getBoundingClientRect(); if(r2.width>5&&r2.height>5){ heading=e2; break; } } }
  out.heading = heading ? rr(heading) : null;
  var picked=null;
  if (heading) {
    var colEl=document.getElementById('center_col');
    var pillEl=document.querySelector('#searchform .A8SBwf, #searchform div[role="combobox"], #searchform .RNNXgb');
    var el=heading, best=null;
    for (var i2=0; i2<16 && el && el!==document.body; i2++, el=el.parentElement) {
      if (colEl && (el===colEl || el.contains(colEl))) break;
      if (pillEl && (el===pillEl || el.contains(pillEl))) break;
      var w=el.getBoundingClientRect().width;
      if (w >= vw*0.9) break;
      if (w > 500) best=el;
    }
    picked=best;
  }
  out.aiPicked = picked ? {cls:cls(picked), rect:rr(picked), tf:(picked.style.transform||'')} : null;
  var ek=document.getElementById('eKIzJc');
  out.eKIzJc = ek ? {rect:rr(ek), tf:(ek.style.transform||''), chain:chain(ek)} : null;
  // ask bar: textarea ITIRGe -> its container wPoHPd
  var ta=document.querySelector('textarea.ITIRGe') || document.querySelector('textarea');
  out.textarea = ta ? {rect:rr(ta), tf:(ta.style.transform||''), chain:chain(ta)} : null;
  var wpo=document.querySelector('.wPoHPd');
  out.wPoHPd = wpo ? {rect:rr(wpo), tf:(wpo.style.transform||''), chain:chain(wpo)} : null;
  // every element with an inline transform
  var tfs=[];
  var all2=document.querySelectorAll('*');
  for (var k=0;k<all2.length;k++){ var e3=all2[k];
    if (e3.style && e3.style.transform && tfs.length<25)
      tfs.push(cls(e3)+' | '+e3.style.transform); }
  out.transforms = tfs;
  return JSON.stringify(out);
}
"""
cmd(S, 3, "WebDriver:ExecuteScript", {"script": SETUP, "args": []})

d = run_js(S, 4, "return window.__ab('with-addon')")
print("\n== WITH ADD-ON ==")
print("heading:", d.get("heading")); print("aiPicked:", d.get("aiPicked"))
ek = d.get("eKIzJc") or {}
print("eKIzJc:", ek.get("rect"), "tf:", ek.get("tf"))
print("  chain:", (ek.get("chain") or [])[:6])
ta = d.get("textarea") or {}
print("textarea:", ta.get("rect"), "tf:", ta.get("tf"))
print("  chain:", (ta.get("chain") or [])[:6])
wp = d.get("wPoHPd") or {}
print("wPoHPd:", wp.get("rect"), "tf:", wp.get("tf"))
print("  chain:", (wp.get("chain") or [])[:6])
print("transforms:", d.get("transforms"))

time.sleep(0.5)
d2 = run_js(S, 5, "return window.__ab('native')")
print("\n== NATIVE (our transforms stripped) ==")
print("aiPicked:", d2.get("aiPicked"))
ek2 = d2.get("eKIzJc") or {}
print("eKIzJc:", ek2.get("rect"), "tf:", ek2.get("tf"))
ta2 = d2.get("textarea") or {}
print("textarea:", ta2.get("rect"), "tf:", ta2.get("tf"))
wp2 = d2.get("wPoHPd") or {}
print("wPoHPd:", wp2.get("rect"), "tf:", wp2.get("tf"))
print("transforms:", d2.get("transforms"))
