#!/usr/bin/env python3
"""Deep structure probe for the knowledge-panel ("About + photos") layout.

Usage: marionette_grid_probe.py PORT
"""
import socket, json, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 2828

def recv_msg(sock):
    buf = b""
    while b":" not in buf:
        c = sock.recv(1)
        if not c:
            raise ConnectionError("closed")
        buf += c
    n = int(buf.split(b":")[0])
    data = b""
    while len(data) < n:
        data += sock.recv(n - len(data))
    return json.loads(data.decode())

def send_msg(sock, msg):
    data = json.dumps(msg).encode()
    sock.sendall(str(len(data)).encode() + b":" + data)

def cmd(sock, mid, name, params):
    send_msg(sock, [0, mid, name, params])
    ans = recv_msg(sock)
    if ans[2]:
        raise RuntimeError(f"{name}: {json.dumps(ans[2])[:400]}")
    return ans[3]

s = socket.create_connection(("127.0.0.1", PORT), timeout=25)
recv_msg(s)
try:
    cmd(s, 1, "WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
except RuntimeError as e:
    print("session:", str(e)[:200])

SCRIPT = r"""
window.__grid = function () {
  var vw = document.documentElement.clientWidth;
  var out = {vw: vw, center: Math.round(vw/2)};
  function rr(e){ var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width),
            t:Math.round(r.top), h:Math.round(r.height)}; }
  function desc(e){ return e.tagName + (e.id?('#'+e.id):'') +
    (typeof e.className==='string' && e.className ? ('.'+e.className.trim().split(/\s+/).slice(0,2).join('.')) : ''); }
  function txt(e, n){ return (e.innerText||'').replace(/\s+/g,' ').trim().slice(0,n||50); }

  var rcnt = document.getElementById('rcnt');
  var rcs = rcnt ? getComputedStyle(rcnt) : null;
  out.rcnt = {rect: rcnt?rr(rcnt):null, display: rcs?rcs.display:null,
              justify: rcs?rcs.justifyContent:null, cols: rcs?rcs.gridTemplateColumns:null,
              overflow: rcs?rcs.overflow:null, tf: rcs?rcs.transform:null};
  // children of rcnt (grid items)
  out.rcntKids = [];
  if (rcnt) {
    for (var i=0;i<rcnt.children.length;i++){
      var c = rcnt.children[i]; var cs = getComputedStyle(c);
      out.rcntKids.push({d:desc(c), rect:rr(c), display:cs.display,
        gc:cs.gridColumn, gcStart:cs.gridColumnStart, gcEnd:cs.gridColumnEnd,
        tf:cs.transform, txt:txt(c,44)});
    }
  }
  // siblings of center_col
  var col = document.getElementById('center_col');
  out.col = col?rr(col):null;
  out.colKids = [];
  if (col) {
    for (var j=0;j<col.children.length;j++){
      var k = col.children[j]; if (k.tagName==='STYLE') continue;
      out.colKids.push({d:desc(k), rect:rr(k), tf:getComputedStyle(k).transform, txt:txt(k,44)});
    }
  }
  // photo strip: find the widest image near top and report its ancestor chain
  var imgs = document.querySelectorAll('img'), best=null, bestArea=0;
  for (var m=0;m<imgs.length;m++){
    var r = imgs[m].getBoundingClientRect();
    if (r.top>250 && r.top<800 && r.width*r.height>bestArea){ bestArea=r.width*r.height; best=imgs[m]; }
  }
  out.photoChain = [];
  if (best) {
    var el = best;
    for (var n=0; n<7 && el && el!==document.body; n++, el=el.parentElement){
      var cs2 = getComputedStyle(el);
      out.photoChain.push({d:desc(el), rect:rr(el), display:cs2.display, gc:cs2.gridColumn, tf:cs2.transform});
    }
  }
  // rhs detail
  var rhs = document.getElementById('rhs');
  out.rhs = rhs?rr(rhs):null;
  out.rhsKids = [];
  if (rhs) {
    for (var p=0;p<rhs.children.length;p++){
      var q=rhs.children[p]; if (q.tagName==='STYLE') continue;
      out.rhsKids.push({d:desc(q), rect:rr(q), txt:txt(q,40)});
    }
  }
  // what's the union box of the visible content?
  function union(els){
    var l=Infinity,r=-Infinity;
    for (var i=0;i<els.length;i++){ if(!els[i]) continue; var b=els[i].getBoundingClientRect();
      if (b.width<5) continue; l=Math.min(l,b.left); r=Math.max(r,b.right); }
    return {l:Math.round(l), r:Math.round(r), w:Math.round(r-l), center:Math.round((l+r)/2)};
  }
  var contentEls = [col, rhs, document.getElementById('rcnt')];
  out.unionColRhs = union([col, rhs]);
  out.unionAll = union(contentEls);
  return JSON.stringify(out);
}"""
cmd(s, 2, "WebDriver:ExecuteScript", {"script": SCRIPT, "args": []})
r = cmd(s, 3, "WebDriver:ExecuteScript", {"script": "return JSON.stringify(window.__grid())", "args": []})
val = r.get("value")
d = val
for _ in range(3):
    if isinstance(d, str):
        try:
            d = json.loads(d)
        except Exception:
            break
    else:
        break
if not isinstance(d, dict):
    print("RAW:", str(val)[:400]); sys.exit(1)
print("vw:", d["vw"], "center:", d["center"])
print("rcnt:", d["rcnt"])
print("union col+rhs:", d["unionColRhs"])
print("\n-- rcnt children (grid items) --")
for k in d["rcntKids"]:
    print("  ", k)
print("\n-- center_col children --")
for k in d["colKids"]:
    print("  ", k)
print("\n-- photo strip ancestor chain --")
for k in d["photoChain"]:
    print("  ", k)
print("\n-- rhs children --")
for k in d["rhsKids"]:
    print("  ", k)