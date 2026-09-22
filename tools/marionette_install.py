#!/usr/bin/env python3
"""Install updated add-on via marionette, reload, measure AI overview centering."""
import socket, json, base64, sys, time

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 36287
XPI = "/home/agentuser/Projects/firefox-google-center/web-ext-artifacts/google_search_centered-1.0.2.zip"

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

s = socket.create_connection(("127.0.0.1", PORT), timeout=30)
recv_msg(s)
try:
    cmd(s, 1, "WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
except RuntimeError as e:
    print("session:", e)

try:
    res = cmd(s, 2, "Addon:Install", {"path": XPI, "temporary": True})
    print("addon install:", json.dumps(res)[:150])
except RuntimeError as e:
    print("addon install err:", e)

cmd(s, 3, "WebDriver:Refresh", {})
time.sleep(10)

DEFINE = r"""window.__ai_measure = function () {
  var vw = document.documentElement.clientWidth;
  var out = {clientW: vw, center: Math.round(vw / 2)};
  function rr(e) { if (!e) return null; var r = e.getBoundingClientRect();
    return {l: Math.round(r.left), r: Math.round(r.right), w: Math.round(r.width), t: Math.round(r.top)}; }
  var col = document.getElementById('center_col');
  out.col = rr(col);
  var pill = document.querySelector('#searchform .A8SBwf, #searchform div[role="combobox"], #searchform .RNNXgb');
  out.pill = rr(pill);
  // AI block (mirror of content.js getAiBlock)
  var heading = null;
  var all = document.querySelectorAll('div,span,h1,h2,h3');
  for (var i = 0; i < all.length; i++) {
    if (all[i].children.length > 3) continue;
    var t = (all[i].textContent || '').trim();
    if (t === 'Visão geral criada por IA' || t === 'AI Overview') {
      var r0 = all[i].getBoundingClientRect();
      if (r0.width > 5 && r0.height > 5) { heading = all[i]; break; }
    }
  }
  if (!heading) { out.ai = 'not present on this page'; return out; }
  var el = heading, best = null;
  for (var k = 0; k < 16 && el && el !== document.body; k++, el = el.parentElement) {
    var w = el.getBoundingClientRect().width;
    if (w >= vw * 0.9) break;
    if (w > 500) best = el;
  }
  out.ai = best ? {rect: rr(best), tf: best.style.transform} : 'no bounded block';
  if (best) {
    var rb = best.getBoundingClientRect();
    out.aiCentered = Math.abs((rb.left + rb.width / 2) - vw / 2) < 4;
    out.aiCenter = Math.round(rb.left + rb.width / 2);
  }
  return out;
}; 'ok';"""

cmd(s, 4, "WebDriver:ExecuteScript", {"script": DEFINE, "args": []})
res = cmd(s, 5, "WebDriver:ExecuteScript", {"script": "return JSON.stringify(window.__ai_measure());", "args": []})
val = res.get("value") if isinstance(res, dict) else res
data = json.loads(val)
print("clientW:", data.get("clientW"), "center:", data.get("center"))
print("col:", json.dumps(data.get("col")))
print("pill:", json.dumps(data.get("pill")))
print("AI:", json.dumps(data.get("ai")))
print("AI centered:", data.get("aiCentered"), "| AI center:", data.get("aiCenter"))

shot = cmd(s, 6, "WebDriver:TakeScreenshot", {"full": False})
b64 = shot.get("value") if isinstance(shot, dict) else shot
if isinstance(b64, str):
    open("/tmp/ai_fix.png", "wb").write(base64.b64decode(b64))
    print("screenshot: /tmp/ai_fix.png")
