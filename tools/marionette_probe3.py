#!/usr/bin/env python3
"""Probe 3: label ancestor chain with overflow/tf info. Usage: script PORT"""
import socket, json, sys

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

DEFINE = r"""window.__probe3 = function () {
  var out = {clientW: document.documentElement.clientWidth};
  function rr(e) { if (!e) return null; var r = e.getBoundingClientRect();
    return {l: Math.round(r.left), r: Math.round(r.right), w: Math.round(r.width), t: Math.round(r.top)}; }
  // leftmost tab label element
  var LABELS = ["Modo IA", "AI Mode"];
  var label = null;
  var all = document.querySelectorAll('a, span, div');
  for (var i = 0; i < all.length; i++) {
    var e = all[i];
    if (e.children.length > 2) continue;
    var t = (e.textContent || '').trim();
    if (LABELS.indexOf(t) !== -1) {
      var r0 = e.getBoundingClientRect();
      if (r0.width > 5 && r0.height > 5 && r0.top < 300) { label = e; break; }
    }
  }
  if (!label) return {noLabel: true};
  out.labelRect = rr(label);
  out.chain = [];
  var el = label;
  for (var k = 0; k < 9 && el && el !== document.body; k++, el = el.parentElement) {
    if (!el.nodeType) break;
    var r = el.getBoundingClientRect();
    var cs = getComputedStyle(el);
    out.chain.push({tag: el.tagName, cls: (typeof el.className === 'string' ? el.className : '').slice(0, 40),
      rect: rr(el), overflowX: cs.overflowX, overflowY: cs.overflowY,
      mask: (cs.maskImage && cs.maskImage !== 'none') ? cs.maskImage.slice(0, 30) : 'none',
      inlineTf: el.style.transform || null,
      display: cs.display, justifyContent: cs.justifyContent, textAlign: cs.textAlign,
      marginLeft: cs.marginLeft});
  }
  return out;
}; 'ok';"""

cmd(s, 2, "WebDriver:ExecuteScript", {"script": DEFINE, "args": []})
res = cmd(s, 3, "WebDriver:ExecuteScript", {"script": "return JSON.stringify(window.__probe3());", "args": []})
val = res.get("value") if isinstance(res, dict) else res
data = json.loads(val)
print("clientW:", data.get("clientW"), "labelRect:", json.dumps(data.get("labelRect")))
for c in data.get("chain", []):
    print(json.dumps(c))
