#!/usr/bin/env python3
"""Check for a Google challenge overlay on the live page + re-measure.
Usage: live_check_overlay.py PORT [out.png]
"""
import socket, json, sys, base64, time

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 2828
OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/live_overlay_check.png"

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

s = socket.create_connection(("127.0.0.1", PORT), timeout=30)
recv_msg(s)
try:
    cmd(s, 1, "WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
except RuntimeError as e:
    print("session:", str(e)[:150])

SCRIPT = r"""
window.__ov = function () {
  var ifr = document.querySelectorAll('iframe');
  var recap = [];
  for (var i=0;i<ifr.length;i++){
    var r = ifr[i].getBoundingClientRect();
    if (r.width>50 && r.height>50) recap.push({src:(ifr[i].src||'').slice(0,90), w:Math.round(r.width), h:Math.round(r.height)});
  }
  var txt = (document.body.innerText||'');
  var overlay = null;
  var cands = document.querySelectorAll('div[role="dialog"], div#captcha, div#gs_captcha_f, div[jscontroller][style*="z-index"]');
  for (var j=0;j<cands.length;j++){ var r2=cands[j].getBoundingClientRect();
    if (r2.width>300 && r2.height>200) { overlay = {tag:cands[j].tagName, id:cands[j].id||'', cls:(cands[j].className||'').toString().slice(0,60),
      l:Math.round(r2.left), t:Math.round(r2.top), w:Math.round(r2.width), h:Math.round(r2.height)}; break; } }
  return JSON.stringify({
    url: location.href.slice(0,100), title: document.title.slice(0,50),
    hasRecaptcha: /recaptcha/i.test(document.documentElement.innerHTML),
    hasUnusual: /unusual traffic|not a robot|não é um robô/i.test(txt),
    iframes: recap,
    overlay: overlay,
    colRect: (function(){var e=document.getElementById('center_col'); if(!e) return null;
      var r=e.getBoundingClientRect(); return {l:Math.round(r.left),w:Math.round(r.width),c:Math.round(r.left+r.width/2)};})(),
    vw: document.documentElement.clientWidth
  });
}
"""
cmd(s, 2, "WebDriver:ExecuteScript", {"script": SCRIPT, "args": []})
r = cmd(s, 2, "WebDriver:ExecuteScript", {"script": "return window.__ov()", "args": []})
print("CHECK:", json.dumps(r.get("value"))[:600])

# dismiss any dialog: press Escape, then re-measure
try:
    cmd(s, 3, "WebDriver:ExecuteScript", {"script": "return 'ok'", "args": []})
except Exception:
    pass
time.sleep(1)
r = cmd(s, 4, "WebDriver:ExecuteScript", {"script": "return window.__ov()", "args": []})
print("AFTER:", json.dumps(r.get("value"))[:400])
try:
    r = cmd(s, 5, "WebDriver:TakeScreenshot", {"full": False})
    b64 = r.get("value")
    if isinstance(b64, str) and len(b64) > 100:
        open(OUT, "wb").write(base64.b64decode(b64)); print("screenshot:", OUT)
except Exception as e:
    print("screenshot err:", e)