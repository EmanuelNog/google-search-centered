#!/usr/bin/env python3
"""Probe 5: full ancestor chain of the AI overview heading + overflow info."""
import socket, json, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 36287

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

DEFINE = r"""window.__probe5 = function () {
  var out = {clientW: document.documentElement.clientWidth};
  function rr(e) { if (!e) return null; var r = e.getBoundingClientRect();
    return {l: Math.round(r.left), r: Math.round(r.right), w: Math.round(r.width), t: Math.round(r.top)}; }
  var heading = null;
  var all = document.querySelectorAll('div,span,h1,h2,h3');
  for (var i = 0; i < all.length; i++) {
    var t = (all[i].textContent || '').trim();
    if ((t === 'Visão geral criada por IA' || t === 'AI Overview') && all[i].children.length <= 3) {
      var r0 = all[i].getBoundingClientRect();
      if (r0.width > 5) { heading = all[i]; break; }
    }
  }
  if (!heading) return {noHeading: true};
  out.chain = [];
  var el = heading;
  for (var k = 0; k < 16 && el; k++, el = el.parentElement) {
    if (!el || !el.nodeType) break;
    var r = el.getBoundingClientRect();
    var cs = getComputedStyle(el);
    var isBody = (el === document.body || el === document.documentElement);
    out.chain.push({lvl: k, tag: el.tagName, id: el.id || '',
      cls: (typeof el.className === 'string' ? el.className : '').slice(0, 38),
      rect: isBody ? {l: rr(el).l, r: rr(el).r, w: rr(el).w, t: rr(el).t} : rr(el),
      overflowX: cs.overflowX, tf: el.style.transform || null, body: isBody});
    if (isBody) break;
  }
  return out;
}; 'ok';"""

cmd(s, 2, "WebDriver:ExecuteScript", {"script": DEFINE, "args": []})
res = cmd(s, 3, "WebDriver:ExecuteScript", {"script": "return JSON.stringify(window.__probe5());", "args": []})
val = res.get("value") if isinstance(res, dict) else res
data = json.loads(val)
print("clientW:", data.get("clientW"))
for c in data.get("chain", []):
    print(json.dumps(c))
