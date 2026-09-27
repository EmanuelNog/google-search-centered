#!/usr/bin/env python3
"""A/B state test: original grid vs add-on-rebalanced grid, strip content position.

Usage: bz_shift_test.py PORT
"""
import socket, json, sys, time

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
    send_msg(sock, [0, mid, name, params])
    ans = recv_msg(sock)
    if ans[2]: raise RuntimeError(f"{name}: {json.dumps(ans[2])[:400]}")
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
    print("session:", str(e)[:200])

SETUP = r"""
window.__snap = function () {
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width), c:Math.round(r.left+r.width/2)}; }
  function node(e){ var cs=getComputedStyle(e);
    return {cls:String(e.className).slice(0,60), rect:rr(e), margin:cs.margin, padding:cs.padding,
            width:cs.width, maxW:cs.maxWidth, disp:cs.display, pos:cs.position, left:cs.left,
            tf:cs.transform, inline:(e.getAttribute('style')||'').slice(0,120)}; }
  var out={};
  var rcnt=document.getElementById('rcnt');
  var col=document.getElementById('center_col'), rhs=document.getElementById('rhs');
  out.rcntInline=rcnt?(rcnt.getAttribute('style')||'').slice(0,200):null;
  if(col&&rhs){ var a=col.getBoundingClientRect(), b=rhs.getBoundingClientRect();
    var l=Math.min(a.left,b.left), r=Math.max(a.right,b.right);
    out.zone={l:Math.round(l), r:Math.round(r), c:Math.round((l+r)/2)}; }
  var px=document.querySelector('.bzXtMb .pxiwBd') || document.querySelector('.pxiwBd');
  out.px=node(px);
  out.pxChain=[]; var n=px;
  for(var i=0;i<5&&n;i++,n=n.parentElement) out.pxChain.push(node(n));
  return JSON.stringify(out);
}
"""

print("setup:", run_js(S, 2, SETUP) is not None)
print("\n== S1: current (add-on applied) ==")
s1 = run_js(S, 3, "return window.__snap()")
print(json.dumps(s1, indent=1)[:1500])

run_js(S, 4, "document.getElementById('rcnt').style.gridTemplateColumns=''; return 'cleared'")
time.sleep(0.6)
print("\n== S2: inline cleared (original layout, add-on not yet re-applied) ==")
s2 = run_js(S, 5, "return window.__snap()")
print(json.dumps(s2, indent=1)[:1500])

time.sleep(1.5)
print("\n== S3: after re-apply wait ==")
s3 = run_js(S, 6, "return window.__snap()")
print(json.dumps(s3, indent=1)[:1500])
