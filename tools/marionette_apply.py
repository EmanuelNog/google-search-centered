#!/usr/bin/env python3
"""Live test: shift the h5JSWd-level row +44 and disable the scroll clip. Usage: script PORT"""
import socket, json, base64, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 44427

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
        raise RuntimeError(f"{name}: {json.dumps(ans[2])[:300]}")
    return ans[3]

s = socket.create_connection(("127.0.0.1", PORT), timeout=20)
recv_msg(s)
try:
    cmd(s, 1, "WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
except RuntimeError as e:
    print("session:", e)

TEST = r"""(() => {
  var out = {};
  var label = null;
  var all = document.querySelectorAll('a, span, div');
  for (var i = 0; i < all.length; i++) {
    var e = all[i];
    if (e.children.length > 2) continue;
    var t = (e.textContent || '').trim();
    if (t === 'Modo IA') { var r0 = e.getBoundingClientRect(); if (r0.width > 5 && r0.top < 300) { label = e; break; } }
  }
  var row = label ? label.parentElement.parentElement.parentElement : null;
  var clip = row ? row.parentElement : null; // HTOhZ
  out.rowCls = row ? row.className : null;
  out.clipCls = clip ? clip.className : null;
  if (clip) clip.style.overflowX = 'visible';
  if (row) {
    var r = row.getBoundingClientRect();
    var delta = Math.round(1536 / 2 - (r.left + r.width / 2));
    out.delta = delta;
    // compose with any existing transform
    var cur = getComputedStyle(row).transform;
    var base = 0;
    var m = cur.match(/matrix\(1, 0, 0, 1, (-?[\d.]+), 0\)/);
    if (m) base = parseFloat(m[1]);
    row.style.transform = 'translateX(' + (base + delta) + 'px)';
    out.newTf = row.style.transform;
  }
  return out;
})();"""

res = cmd(s, 2, "WebDriver:ExecuteScript", {"script": TEST, "args": []})
val = res.get("value") if isinstance(res, dict) else res
print("apply:", json.dumps(val))

shot = cmd(s, 3, "WebDriver:TakeScreenshot", {"full": False})
b64 = shot.get("value") if isinstance(shot, dict) else shot
if isinstance(b64, str):
    open("/tmp/live_test.png", "wb").write(base64.b64decode(b64))
    print("screenshot saved: /tmp/live_test.png")
