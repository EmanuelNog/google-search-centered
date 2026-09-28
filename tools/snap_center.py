#!/usr/bin/env python3
"""One-shot snapshot of centering state (zone/strip/pill offsets + zoom markers).

Usage: snap_center.py PORT [label]
"""
import socket, json, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 2828
LABEL = sys.argv[2] if len(sys.argv) > 2 else "snap"

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

S = socket.create_connection(("127.0.0.1", PORT), timeout=30)
recv_msg(S)
try:
    cmd(S, 1, "WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
except RuntimeError as e:
    print("session:", str(e)[:200])

SETUP = r"""
window.__zs = function () {
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width), c:Math.round(r.left+r.width/2)}; }
  var vw = document.documentElement.clientWidth, center = Math.round(vw/2);
  var col=document.getElementById('center_col'), rhs=document.getElementById('rhs');
  var zone=null;
  if(col&&rhs){ var a=col.getBoundingClientRect(), b=rhs.getBoundingClientRect();
    var l=Math.min(a.left,b.left), r=Math.max(a.right,b.right);
    zone={c:Math.round((l+r)/2), off:Math.round((l+r)/2-center)}; }
  var sc=document.querySelector('.bzXtMb .Kevs9') || document.querySelector('.Kevs9');
  var scc=sc?rr(sc):null;
  var pill=document.querySelector('#searchform .A8SBwf, #searchform div[role="combobox"], #searchform .RNNXgb');
  var pillOff=null; if(pill){ var pr=pill.getBoundingClientRect(); pillOff=Math.round(pr.left+pr.width/2-center); }
  return JSON.stringify({vw:vw, center:center, dpr:Math.round(window.devicePixelRatio*1000)/1000,
    zone:zone, stripOff: scc?Math.round(scc.c-center):null, pillOff: pillOff,
    rcntInline:(document.getElementById('rcnt').getAttribute('style')||'').slice(0,60),
    ghostInline:(function(){ var g=document.querySelector('.bzXtMb .YNk70c'); return g?(g.getAttribute('style')||'').slice(0,60):null; })()});
}
"""
cmd(S, 2, "WebDriver:ExecuteScript", {"script": SETUP, "args": []})
r = cmd(S, 3, "WebDriver:ExecuteScript", {"script": "return window.__zs()", "args": []})
d = r.get("value")
for _ in range(3):
    if isinstance(d, str):
        try: d = json.loads(d)
        except Exception: break
    else: break
if isinstance(d, dict):
    zo = (d.get("zone") or {}).get("off")
    print(f"[{LABEL}] vw={d.get('vw')} center={d.get('center')} dpr={d.get('dpr')} zoneOff={zo} stripOff={d.get('stripOff')} pillOff={d.get('pillOff')}")
    print(f"    rcnt: {d.get('rcntInline')}")
    print(f"    ghost: {d.get('ghostInline')}")
else:
    print("raw:", str(d)[:400])
