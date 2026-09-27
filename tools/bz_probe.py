#!/usr/bin/env python3
"""Deep probe of the .bzXtMb full-bleed row (inner carousel geometry).

Usage: bz_probe.py PORT [out.png]
"""
import socket, json, sys, base64

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 2828
OUT = sys.argv[2] if len(sys.argv) > 2 else None

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

s = socket.create_connection(("127.0.0.1", PORT), timeout=30)
recv_msg(s)
try:
    cmd(s, 1, "WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
except RuntimeError as e:
    print("session:", str(e)[:200])

MEAS = r"""
window.__bzp = function () {
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width),
            t:Math.round(r.top), h:Math.round(r.height), c:Math.round(r.left+r.width/2)}; }
  var out={vw:document.documentElement.clientWidth};
  var bz=document.querySelector('.bzXtMb');
  if(!bz){ out.err='no .bzXtMb'; }
  else {
    out.bz=rr(bz);
    var cs=getComputedStyle(bz);
    out.bzCS={disp:cs.display, pad:cs.padding, mar:cs.margin, ovf:cs.overflowX, gcs:cs.gridColumnStart, gce:cs.gridColumnEnd};
    out.kids=[...bz.children].map(function(k){ var c=getComputedStyle(k);
      return {cls:String(k.className).slice(0,70), rect:rr(k), pad:c.padding, ovf:c.overflowX, w:c.width}; });
    var all=bz.querySelectorAll('*'); var scroller=null;
    for(var i=0;i<all.length;i++){ var e=all[i];
      if(e.scrollWidth>e.clientWidth+10){ scroller=e; break; } }
    if(scroller){ var sc=getComputedStyle(scroller);
      out.scroller={cls:String(scroller.className).slice(0,70), rect:rr(scroller),
        sw:scroller.scrollWidth, cw:scroller.clientWidth, sl:scroller.scrollLeft, pad:sc.padding, mar:sc.margin}; }
    var tiles=[]; var cand=bz.querySelectorAll('a, div[data-ved], img');
    for(var j=0;j<cand.length;j++){ var q=cand[j].getBoundingClientRect();
      if(q.width>40 && q.height>20) tiles.push({tag:cand[j].tagName, cls:String(cand[j].className||'').slice(0,40), rect:rr(cand[j])}); }
    out.firstTiles=tiles.slice(0,5);
    out.lastTiles=tiles.slice(-4);
  }
  out.slps=[...document.querySelectorAll('.SLPe5b')].map(function(e){
    return {rect:rr(e), text:(e.innerText||'').replace(/\s+/g,' ').slice(0,120)}; });
  return JSON.stringify(out);
}
"""
cmd(s, 2, "WebDriver:ExecuteScript", {"script": MEAS, "args": []})
r = cmd(s, 3, "WebDriver:ExecuteScript", {"script": "return window.__bzp()", "args": []})
d = r.get("value")
for _ in range(3):
    if isinstance(d, str):
        try: d = json.loads(d)
        except Exception: break
    else: break
print("== BZ DEEP PROBE ==")
if isinstance(d, dict):
    for k in ("vw","err","bz","bzCS","scroller"):
        print(f"  {k}: {d.get(k)}")
    print("  kids:")
    for kid in d.get("kids") or []: print(f"    {kid}")
    print("  firstTiles:")
    for t in d.get("firstTiles") or []: print(f"    {t}")
    print("  lastTiles:")
    for t in d.get("lastTiles") or []: print(f"    {t}")
    print("  slps:")
    for x in d.get("slps") or []: print(f"    {x}")
else:
    print("  raw:", str(d)[:600])

if OUT:
    try:
        r = cmd(s, 4, "WebDriver:TakeScreenshot", {"full": False})
        b64 = r.get("value")
        if isinstance(b64, str) and len(b64) > 100:
            open(OUT, "wb").write(base64.b64decode(b64)); print("screenshot:", OUT)
    except Exception as e:
        print("screenshot err:", e)
