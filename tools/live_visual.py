#!/usr/bin/env python3
"""Reload the live SERP, verify centering, hide ONLY the captcha overlay,
screenshot for a clean visual check.

Usage: live_visual.py PORT URL [out.png]
"""
import socket, json, sys, base64, time

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 2828
URL = sys.argv[2] if len(sys.argv) > 2 else "https://www.google.com/search?q=banana&hl=en"
OUT = sys.argv[3] if len(sys.argv) > 3 else "/tmp/live_clean.png"

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
    data = json.dumps(msg).encode(); sock.sendall(str(len(data)).encode() + b":" + data)

def cmd(sock, mid, name, params):
    send_msg(sock, [0, mid, name, params]); ans = recv_msg(sock)
    if ans[2]: raise RuntimeError(f"{name}: {json.dumps(ans[2])[:250]}")
    return ans[3]

def js(sock, mid, fn):
    return cmd(sock, mid, "WebDriver:ExecuteScript", {"script": fn, "args": []}).get("value")

s = socket.create_connection(("127.0.0.1", PORT), timeout=30)
recv_msg(s)
try:
    cmd(s, 1, "WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
except RuntimeError as e:
    print("session:", str(e)[:120])

print("navigate:", json.dumps(cmd(s, 2, "WebDriver:Navigate", {"url": URL}))[:120])
time.sleep(14)

MEAS = r"""
window.__v2 = function () {
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), w:Math.round(r.width), c:Math.round(r.left+r.width/2)}; }
  var vw = document.documentElement.clientWidth;
  var col=document.getElementById('center_col'), rhs=document.getElementById('rhs');
  var pil=document.querySelector('#searchform .A8SBwf, #searchform div[role="combobox"], #searchform .RNNXgb');
  var union=null;
  if (col && rhs) { var a=col.getBoundingClientRect(), b=rhs.getBoundingClientRect();
    var l=Math.min(a.left,b.left), r=Math.max(a.right,b.right);
    union={l:Math.round(l), w:Math.round(r-l), c:Math.round((l+r)/2), off:Math.round((l+r)/2 - vw/2)}; }
  return JSON.stringify({vw:vw, center:Math.round(vw/2), title:document.title.slice(0,40),
    col:rr(col), rhs:rr(rhs), pill:rr(pil), union:union,
    rcntInline: (function(){var e=document.getElementById('rcnt'); return e?((e.getAttribute('style')||'').slice(0,60)):null;})()});
}"""
js(s, 3, MEAS)
print("MEASURE:", js(s, 4, "return window.__v2()"))

HIDE = r"""
window.__hide2 = function () {
  var n = 0;
  var ifr = document.querySelectorAll('iframe');
  for (var i=0;i<ifr.length;i++){
    if (/\/sorry\//.test(ifr[i].src||'')) {
      ifr[i].style.display = 'none'; n++;
      var p = ifr[i].parentElement;
      for (var k=0;k<3 && p && p !== document.body; k++){
        var cn = (p.className||'').toString();
        if (/qk7LXc|dialog|ivkdbf/.test(cn)) { p.style.display='none'; break; }
        p = p.parentElement;
      }
    }
  }
  return JSON.stringify({hidden: n});
}"""
js(s, 5, HIDE)
print("hide:", js(s, 6, "return window.__hide2()"))
time.sleep(2)
print("RE-MEASURE:", js(s, 7, "return window.__v2()"))

try:
    r = cmd(s, 8, "WebDriver:TakeScreenshot", {"full": False})
    b64 = r.get("value")
    if isinstance(b64, str) and len(b64) > 100:
        open(OUT, "wb").write(base64.b64decode(b64)); print("screenshot:", OUT)
except Exception as e:
    print("screenshot err:", e)