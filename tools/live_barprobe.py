#!/usr/bin/env python3
"""Dump the AI module's ask-bar input chain + all transformed elements.

Usage: live_barprobe.py PORT
"""
import socket, json, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 2828

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

JS = r"""
window.__bp = function () {
  function rr(e){var r=e.getBoundingClientRect();return {l:Math.round(r.left),r:Math.round(r.right),w:Math.round(r.width),h:Math.round(r.height)};}
  var out = {vw: document.documentElement.clientWidth, url: location.href.slice(0,80)};
  out.tfs = [...document.querySelectorAll('*')].filter(e=>e.style.transform).map(e=>({cls:String(e.className).slice(0,34),tf:e.style.transform})).slice(0,12);
  var ai = document.getElementById('eKIzJc') || document.querySelector('.Kevs9');
  out.ai = ai ? Object.assign({cls:String(ai.className).slice(0,30)}, rr(ai)) : null;
  var inputs = ai ? [...ai.querySelectorAll('textarea, input')] : [];
  out.inputs = inputs.map(i=>({tag:i.tagName,w:rr(i).w,h:rr(i).h,ph:String(i.placeholder||'').slice(0,18)}));
  if (inputs.length) {
    var chain = [], el = inputs[0];
    for (var i=0;i<8 && el; i++, el=el.parentElement) {
      var r = rr(el);
      chain.push({cls:String(el.className).slice(0,30), w:r.w, h:r.h, l:r.l, r:r.r, tf:el.style.transform||'-'});
    }
    out.inputChain = chain;
  }
  return JSON.stringify(out);
}
"""
cmd(S, 2, "WebDriver:ExecuteScript", {"script": JS, "args": []})
r = cmd(S, 3, "WebDriver:ExecuteScript", {"script": "return window.__bp()", "args": []})
print(json.dumps(r))
