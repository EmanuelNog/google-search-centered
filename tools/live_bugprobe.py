#!/usr/bin/env python3
"""Bug probe for live SERP issues (knowledge panel images row, header rows).

Connects to a marionette-enabled Firefox (manual instance, Xvfb), optionally
installs the built xpi, navigates, then dumps geometry + chains for the
elements under investigation plus the standard add-on targets.

Usage: live_bugprobe.py PORT XPI URL [out.png]
"""
import socket, json, sys, base64, time

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 2828
XPI = sys.argv[2] if len(sys.argv) > 2 else None
URL = sys.argv[3] if len(sys.argv) > 3 else "https://www.google.com/search?q=banana&hl=en&gl=us"
OUT = sys.argv[4] if len(sys.argv) > 4 else None

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

if XPI:
    print("install addon:", json.dumps(cmd(s, 2, "Addon:Install", {"path": XPI, "temporary": True}))[:200])
if URL != "-":
    print("navigate:", json.dumps(cmd(s, 3, "WebDriver:Navigate", {"url": URL}))[:160])
    time.sleep(16)
else:
    time.sleep(1)

MEAS = r"""
window.__bp = function () {
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width),
            t:Math.round(r.top), h:Math.round(r.height), c:Math.round(r.left+r.width/2)}; }
  function chain(e){ var out=[], n=e; for(var i=0;i<6&&n;i++){
    var cls = (n.className && typeof n.className==='string') ? '.'+String(n.className).split(' ').slice(0,3).join('.') : '';
    out.push(n.tagName+(n.id?'#'+n.id:'')+cls); n=n.parentElement; } return out; }
  function info(e){ if(!e) return null; var cs=getComputedStyle(e);
    return {rect:rr(e), chain:chain(e), gcs:cs.gridColumnStart, gce:cs.gridColumnEnd,
            disp:cs.display, tf:(e.style.transform||''), text:(e.innerText||'').replace(/\s+/g,' ').slice(0,70)}; }
  var vw = document.documentElement.clientWidth;
  var col=document.getElementById('center_col'), rhs=document.getElementById('rhs'), rcnt=document.getElementById('rcnt');
  var pil=document.querySelector('#searchform .A8SBwf, #searchform div[role="combobox"], #searchform .RNNXgb');
  var kids=[];
  if(rcnt){ var ks=rcnt.children; for(var i=0;i<ks.length;i++){ var k=ks[i], kcs=getComputedStyle(k), kr=k.getBoundingClientRect();
    if(kr.height>10) kids.push({cls:String(k.className).slice(0,50), gcs:kcs.gridColumnStart, gce:kcs.gridColumnEnd, rect:rr(k)}); } }
  var union=null;
  if (col && rhs) { var a=col.getBoundingClientRect(), b=rhs.getBoundingClientRect();
    var l=Math.min(a.left,b.left), r=Math.max(a.right,b.right);
    union={l:Math.round(l), r:Math.round(r), c:Math.round((l+r)/2), off:Math.round((l+r)/2 - vw/2)}; }
  return JSON.stringify({vw:vw, center:Math.round(vw/2), url:location.href.slice(0,90), title:document.title.slice(0,60),
    col:rr(col), rhs:rr(rhs), pill:rr(pil), union:union,
    rcntGrid: rcnt?getComputedStyle(rcnt).gridTemplateColumns.slice(0,160):null,
    rcntInline: rcnt?(rcnt.getAttribute('style')||'').slice(0,160):null,
    kids:kids,
    bz: info(document.querySelector('.bzXtMb')),
    slp: info(document.querySelector('.SLPe5b')),
    ynk: info(document.querySelector('.YNk70c')),
    hdtb: info(document.getElementById('hdtb'))});
}
"""
cmd(s, 4, "WebDriver:ExecuteScript", {"script": MEAS, "args": []})
r = cmd(s, 5, "WebDriver:ExecuteScript", {"script": "return window.__bp()", "args": []})
d = r.get("value")
for _ in range(3):
    if isinstance(d, str):
        try: d = json.loads(d)
        except Exception: break
    else: break
print("\n== BUG PROBE ==")
if isinstance(d, dict):
    for k in ("vw","center","url","title","col","rhs","pill","union","rcntGrid","rcntInline"):
        print(f"  {k}: {d.get(k)}")
    print("  kids:")
    for kid in d.get("kids") or []:
        print(f"    {kid}")
    for k in ("bz","slp","ynk","hdtb"):
        print(f"  {k}: {json.dumps(d.get(k), ensure_ascii=False)[:400]}")
else:
    print("  raw:", str(d)[:600])

if OUT:
    try:
        r = cmd(s, 6, "WebDriver:TakeScreenshot", {"full": False})
        b64 = r.get("value")
        if isinstance(b64, str) and len(b64) > 100:
            open(OUT, "wb").write(base64.b64decode(b64)); print("screenshot:", OUT)
    except Exception as e:
        print("screenshot err:", e)
