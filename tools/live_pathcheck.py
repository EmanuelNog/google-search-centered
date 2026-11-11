#!/usr/bin/env python3
"""Resolve a CSS ancestor chain step by step on the live page.

Usage: live_pathcheck.py PORT ["sel1 > sel2 > ..."]
Reports, per step: match count, first match rect/cls/kids, and whether the
next step resolves inside it. Also dumps the show-more label chain (if any)
and the AI module rects for context.
"""
import socket, json, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 2828
CHAIN = sys.argv[2] if len(sys.argv) > 2 else (
    "html body#gsr.srp > div#main.main.n48JGd > div#cnt.e9EfHf > "
    "div#rcnt.NbTBrb.YNk70c.EjQTId.uW3HW.GyAeWb > div.bzXtMb.M8OgIe.dRpWwb > "
    "div#Odp5De > div.YNk70c.EjQTId > div.Kevs9.SLPe5b > div#eKIzJc.SePcAf"
)

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

S = socket.create_connection(("127.0.0.1", PORT), timeout=30)
recv_msg(S)
try:
    cmd(S, 1, "WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
except RuntimeError as e:
    print("session:", str(e)[:120])

JS = r"""
window.__pc = function (chain) {
  function rr(e){var r=e.getBoundingClientRect();return {l:Math.round(r.left),r:Math.round(r.right),w:Math.round(r.width),h:Math.round(r.height),c:Math.round(r.left+r.width/2)};}
  var steps = chain.split('>').map(s=>s.trim()).filter(Boolean);
  var out = {url: location.href.slice(0,90), vw: document.documentElement.clientWidth, steps: []};
  var ctx = document.documentElement;
  var full = 'html';
  for (var i=0;i<steps.length;i++) {
    var sel = steps[i].replace(/^html\s*/, '').trim();
    var scope = (i === 0) ? document : ctx;
    var nodes = [];
    try { nodes = sel ? [...document.querySelectorAll(full + ' ' + sel)] : []; } catch(e) { nodes = []; }
    var info = {sel: sel, n: nodes.length};
    if (nodes.length) { info.first = rr(nodes[0]); info.cls = String(nodes[0].className).slice(0,40); info.kids = nodes[0].children.length; ctx = nodes[0]; }
    out.steps.push(info);
    full += ' ' + sel;
  }
  var mod = document.querySelector('.Kevs9'); out.kevs = mod ? rr(mod) : null;
  var ek = document.getElementById('eKIzJc'); out.ekiz = ek ? {cls:String(ek.className).slice(0,30), r:rr(ek), kids:[...ek.children].map(c=>String(c.className).slice(0,24)||c.tagName)} : null;
  var more = [...document.querySelectorAll('div,span,button')].filter(e=>/^(show more|mostrar mais)$/i.test((e.textContent||'').trim()));
  out.more = more.slice(0,4).map(e=>{var r=rr(e); var chain=[]; var n=e;
     for (var i=0;i<6 && n;i++,n=n.parentElement) chain.push(String(n.className).slice(0,26)||n.tagName);
     return {cls:String(e.className).slice(0,30), kids:e.children.length, r:r, tf:e.style.transform||'-', chain:chain};});
  return JSON.stringify(out);
}
"""
cmd(S, 2, "WebDriver:ExecuteScript", {"script": JS, "args": []})
r = cmd(S, 3, "WebDriver:ExecuteScript", {"script": "return window.__pc(arguments[0])", "args": [CHAIN]})
if isinstance(r, dict):
    r = r.get("value")
d = json.loads(r)
print("url:", d["url"])
print("vw:", d["vw"])
for s in d["steps"]:
    print(f"  {s['sel'][:52]:55s} n={s['n']}" + (f" first={s['first']} cls={s['cls']} kids={s['kids']}" if s.get("first") else "  <MISSING>"))
print("kevs:", d["kevs"])
print("ekiz:", json.dumps(d["ekiz"])[:220])
print("show-more candidates:")
for m in d["more"]:
    print("  ", json.dumps(m))
