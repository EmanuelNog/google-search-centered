#!/usr/bin/env python3
"""Map the nested grid structure inside full-bleed rows (why strip content stays at old zone-left).

Usage: bz_grid_probe.py PORT
"""
import socket, json, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 2828

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
    send_msg(sock, [mid and 0, mid, name, params] if False else [0, mid, name, params])
    ans = recv_msg(sock)
    if ans[2]: raise RuntimeError(f"{name}: {json.dumps(ans[2])[:400]}")
    return ans[3]

S = socket.create_connection(("127.0.0.1", PORT), timeout=30)
recv_msg(S)
try:
    cmd(S, 1, "WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
except RuntimeError as e:
    print("session:", str(e)[:200])

MEAS = r"""
window.__gp = function () {
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width), t:Math.round(r.top), h:Math.round(r.height)}; }
  function c60(e){ return String(e.className||'').slice(0,60); }
  var out={vw:document.documentElement.clientWidth};
  var rcnt=document.getElementById('rcnt');
  out.rcntKids=[...rcnt.children].map(function(k){ var cs=getComputedStyle(k);
    return {cls:c60(k), gcs:cs.gridColumnStart, gce:cs.gridColumnEnd, rect:rr(k)}; });
  var bz=document.querySelector('.bzXtMb');
  out.bzGrids=null; out.bzWalk=null;
  if(bz){
    var grids=[]; var all=bz.querySelectorAll('*');
    for(var i=0;i<all.length;i++){ var e=all[i]; var cs=getComputedStyle(e);
      if(cs.display==='grid'){ grids.push({cls:c60(e), rect:rr(e), gcs:cs.gridColumnStart, gce:cs.gridColumnEnd,
        gtc:cs.gridTemplateColumns.slice(0,160), inline:(e.getAttribute('style')||'').slice(0,160)}); } }
    out.bzGrids=grids.slice(0,8);
    // walk down: first 40 nodes breadth-first depth<=5, only wide ones
    var walk=[]; var q=[{e:bz,d:0}];
    while(q.length && walk.length<40){ var it=q.shift(); var e=it.e;
      var r=e.getBoundingClientRect(); var cs=getComputedStyle(e);
      if(r.width>800) walk.push({d:it.d, cls:c60(e), rect:rr(e), disp:cs.display, gtc:cs.gridTemplateColumns.slice(0,100)});
      if(it.d<5){ var kids=e.children; for(var k=0;k<kids.length && k<8;k++) q.push({e:kids[k],d:it.d+1}); } }
    out.bzWalk=walk;
  }
  out.slps=[...document.querySelectorAll('.SLPe5b')].map(function(e){
    return {rect:rr(e), text:(e.innerText||'').replace(/\s+/g,' ').slice(0,90)}; });
  return JSON.stringify(out);
}
"""
cmd(S, 2, "WebDriver:ExecuteScript", {"script": MEAS, "args": []})
r = cmd(S, 3, "WebDriver:ExecuteScript", {"script": "return window.__gp()", "args": []})
d = r.get("value")
for _ in range(3):
    if isinstance(d, str):
        try: d = json.loads(d)
        except Exception: break
    else: break
print("== GRID PROBE ==")
print("rcntKids:")
for k in (d.get("rcntKids") or []): print("  ", k)
print("bzGrids:")
for g in (d.get("bzGrids") or []): print("  ", g)
print("bzWalk (wide descendants):")
for w in (d.get("bzWalk") or []): print("  ", w)
print("slps:")
for x in (d.get("slps") or []): print("  ", x)
