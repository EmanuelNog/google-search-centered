#!/usr/bin/env python3
"""Experiment C on the LIVE banana SERP: shift the grid TRACKS (first +delta,
last -delta) so the content block centers while full-bleed rows stay
full-bleed. Measures + screenshots for visual comparison.

Usage: exp_panel_fix_c.py PORT [out.png]
"""
import socket, json, sys, base64

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 2828
OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/panel_C.png"

def recv_msg(sock):
    buf = b""
    while b":" not in buf:
        c = sock.recv(1)
        if not c: raise ConnectionError("closed")
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
    if ans[2]: raise RuntimeError(f"{name}: {json.dumps(ans[2])[:400]}")
    return ans[3]

s = socket.create_connection(("127.0.0.1", PORT), timeout=25)
recv_msg(s)
try:
    cmd(s, 1, "WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
except RuntimeError as e:
    print("session:", str(e)[:150])

MEAS = r"""
window.__mc = function () {
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width), c:Math.round(r.left+r.width/2)}; }
  var vw = document.documentElement.clientWidth;
  var col=document.getElementById('center_col'), rhs=document.getElementById('rhs'), rcnt=document.getElementById('rcnt');
  var ent=document.querySelector('#rcnt > .SLPe5b');
  var strip=null, kids=rcnt?rcnt.children:[];
  for (var i=0;i<kids.length;i++){ var cs=getComputedStyle(kids[i]);
    if (cs.gridColumnStart==='1' && cs.gridColumnEnd==='-1'){ strip=kids[i]; break; } }
  var imgs=document.querySelectorAll('img'), firstImg=null, minL=Infinity;
  for (var m=0;m<imgs.length;m++){ var r=imgs[m].getBoundingClientRect();
    if(r.top>250&&r.top<800&&r.width>100&&r.left<minL){minL=r.left;firstImg=imgs[m];} }
  var boxes=[col,rhs,ent].filter(Boolean).map(function(e){var r=e.getBoundingClientRect();return {l:r.left,r:r.right};});
  var l=Math.min.apply(null,boxes.map(function(b){return b.l;})), r2=Math.max.apply(null,boxes.map(function(b){return b.r;}));
  return JSON.stringify({vw:vw, center:Math.round(vw/2),
    col:rr(col), rhs:rr(rhs), ent:rr(ent), strip:rr(strip), firstImg: rr(firstImg),
    union:{l:Math.round(l), r:Math.round(r2), w:Math.round(r2-l), c:Math.round((l+r2)/2), off:Math.round((l+r2)/2-vw/2)},
    tracks: rcnt?getComputedStyle(rcnt).gridTemplateColumns.split(' ').length:null,
    firstTrack: rcnt?getComputedStyle(rcnt).gridTemplateColumns.split(' ')[0]:null,
    lastTrack: rcnt?getComputedStyle(rcnt).gridTemplateColumns.split(' ').slice(-1)[0]:null,
    inlineCols: rcnt?(rcnt.style.gridTemplateColumns||null):null});
}"""
cmd(s, 2, "WebDriver:ExecuteScript", {"script": MEAS, "args": []})

def measure(tag):
    r = cmd(s, 3, "WebDriver:ExecuteScript", {"script": "return window.__mc()", "args": []})
    d = r.get("value")
    for _ in range(3):
        if isinstance(d, str):
            try: d = json.loads(d)
            except Exception: break
        else: break
    print(f"\n== {tag} ==")
    if isinstance(d, dict):
        for k in ("vw","center","col","rhs","ent","strip","firstImg","union","tracks","firstTrack","lastTrack","inlineCols"):
            print(f"  {k}: {d.get(k)}")
    else:
        print("  raw:", str(d)[:300])
    return d

measure("BEFORE (native)")

APPLY_C = r"""
window.__applyC = function () {
  var rcnt = document.getElementById('rcnt');
  var col = document.getElementById('center_col'), rhs = document.getElementById('rhs');
  var ent = document.querySelector('#rcnt > .SLPe5b');
  var vw = document.documentElement.clientWidth;
  rcnt.style.gridTemplateColumns = '';
  void rcnt.getBoundingClientRect();
  var cols = getComputedStyle(rcnt).gridTemplateColumns.split(' ');
  var boxes=[col,rhs,ent].filter(Boolean).map(function(e){var r=e.getBoundingClientRect();return {l:r.left,r:r.right};});
  var l=Math.min.apply(null,boxes.map(function(b){return b.l;})), r=Math.max.apply(null,boxes.map(function(b){return b.r;}));
  var delta = Math.round(vw/2 - (l+r)/2);
  var first = parseFloat(cols[0]), last = parseFloat(cols[cols.length-1]);
  if (delta > 0) { cols[0] = (first + delta) + 'px'; cols[cols.length-1] = (last - delta) + 'px'; }
  rcnt.style.gridTemplateColumns = cols.join(' ');
  return JSON.stringify({delta: delta, first: cols[0], last: cols[cols.length-1]});
}"""
cmd(s, 4, "WebDriver:ExecuteScript", {"script": APPLY_C, "args": []})
r = cmd(s, 5, "WebDriver:ExecuteScript", {"script": "return window.__applyC()", "args": []})
print("\napplyC:", r.get("value"))
measure("AFTER C (track shift)")

# screenshot
try:
    r = cmd(s, 6, "WebDriver:TakeScreenshot", {"full": False})
    b64 = r.get("value")
    if isinstance(b64, str) and len(b64) > 100:
        open(OUT, "wb").write(base64.b64decode(b64))
        print("\nscreenshot:", OUT)
except Exception as e:
    print("screenshot err:", e)