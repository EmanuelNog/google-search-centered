#!/usr/bin/env python3
"""Live page state + centering dump (and optional navigate/screenshot).

Survives reboots (lives in the repo, unlike the old /tmp helpers).
Usage: live_state.py PORT [URL_OR_-] [OUT.png]
"""
import socket, json, sys, base64, time

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 2828
URL = sys.argv[2] if len(sys.argv) > 2 else "-"
OUT = sys.argv[3] if len(sys.argv) > 3 else None

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

S = socket.create_connection(("127.0.0.1", PORT), timeout=30)
recv_msg(S)
try:
    cmd(S, 1, "WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
except RuntimeError as e:
    print("session:", str(e)[:150])

mid = 2
if URL != "-":
    print("navigate:", json.dumps(cmd(S, mid, "WebDriver:Navigate", {"url": URL}))[:90]); mid += 1
    time.sleep(16)

JS = r"""
window.__ls = function () {
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width), t:Math.round(r.top), h:Math.round(r.height), c:Math.round(r.left+r.width/2)}; }
  function cls(e){ return String((e&&e.className)||'').slice(0,45); }
  var vw = document.documentElement.clientWidth;
  var out = {url: location.href.slice(0,110), title: document.title.slice(0,60),
             vw: vw, center: Math.round(vw/2), dark: matchMedia('(prefers-color-scheme: dark)').matches};
  var col=document.getElementById('center_col'), rhs=document.getElementById('rhs'), rcnt=document.getElementById('rcnt');
  out.col = rr(col); out.rhs = rhs ? {r: rr(rhs), visible: getComputedStyle(rhs).display!=='none' && rhs.getBoundingClientRect().width>0} : null;
  out.rcntInline = rcnt ? (rcnt.getAttribute('style')||'').slice(0,90) : null;
  var zone=null;
  if (col && rhs && rhs.getBoundingClientRect().width>0) { var a=col.getBoundingClientRect(), b=rhs.getBoundingClientRect();
    var l=Math.min(a.left,b.left), r=Math.max(a.right,b.right);
    zone={l:Math.round(l), r:Math.round(r), c:Math.round((l+r)/2), off:Math.round((l+r)/2 - vw/2)}; }
  out.zone = zone;
  var pill=document.querySelector('#searchform .A8SBwf, #searchform div[role="combobox"], #searchform .RNNXgb');
  out.pill = rr(pill);
  var ais = [];
  var ek = document.getElementById('eKIzJc'); if (ek) ais.push({what:'eKIzJc', rect: rr(ek)});
  var ni = document.querySelector('.niO4u'); if (ni) ais.push({what:'pill.niO4u', rect: rr(ni)});
  var in7 = document.querySelector('.in7vHe'); if (in7) ais.push({what:'pillwrap.in7vHe', rect: rr(in7), tf: in7.style.transform||''});
  var uab = document.querySelector('.UAbVe'); if (uab) ais.push({what:'barwrap.UAbVe', rect: rr(uab), tf: uab.style.transform||''});
  out.ai = ais;
  var tfs=[]; var all=document.querySelectorAll('*');
  for (var i=0;i<all.length && tfs.length<20;i++){ if (all[i].style && all[i].style.transform) tfs.push(cls(all[i])+' | '+all[i].style.transform); }
  out.transforms = tfs;
  return JSON.stringify(out);
}
"""
cmd(S, mid, "WebDriver:ExecuteScript", {"script": JS, "args": []}); mid += 1
r = cmd(S, mid, "WebDriver:ExecuteScript", {"script": "return window.__ls()", "args": []}); mid += 1
d = r.get("value")
for _ in range(3):
    if isinstance(d, str):
        try: d = json.loads(d)
        except Exception: break
    else: break
if isinstance(d, dict):
    for k in ("url","title","vw","center","dark","col","rhs","zone","pill","rcntInline"):
        print(f"  {k}: {d.get(k)}")
    for a in d.get("ai") or []: print("  ai:", a)
    print("  transforms:", d.get("transforms"))
else:
    print("raw:", str(d)[:400])

if OUT:
    try:
        r = cmd(S, mid, "WebDriver:TakeScreenshot", {"full": False})
        b64 = r.get("value")
        if isinstance(b64, str) and len(b64) > 100:
            open(OUT, "wb").write(base64.b64decode(b64)); print("screenshot:", OUT)
    except Exception as e:
        print("screenshot err:", e)
