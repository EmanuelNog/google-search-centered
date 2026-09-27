#!/usr/bin/env python3
"""Measure the live Google SERP DOM through marionette (raw TCP).

Usage: marionette_serp_probe.py PORT

Dumps the facts needed for the "no AI overview" bug (About + photos layout):
grid structure around #center_col, #rhs, block boxes, AI text, tabs, and the
scrolling/centering containers.
"""
import socket, json, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 2828

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

s = socket.create_connection(("127.0.0.1", PORT), timeout=25)
recv_msg(s)
try:
    cmd(s, 1, "WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
except RuntimeError as e:
    print("session:", str(e)[:200])

DEFINE = r"""
window.__serp = function () {
  var vw = document.documentElement.clientWidth;
  var out = {vw: vw, center: Math.round(vw/2), url: location.href.slice(0,110),
             title: document.title.slice(0,60),
             bodyText: (document.body.innerText||'').slice(0,220).replace(/\n+/g,' | ')};
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width),
            t:Math.round(r.top), h:Math.round(r.height), tf:getComputedStyle(e).transform}; }
  function desc(e){ if(!e) return '-'; return e.tagName + (e.id?('#'+e.id):'') +
    (typeof e.className==='string' && e.className ? ('.'+e.className.trim().split(/\s+/).slice(0,2).join('.')) : ''); }
  out.col = rr(document.getElementById('center_col'));
  out.colDesc = desc(document.getElementById('center_col'));
  out.rhs = rr(document.getElementById('rhs'));
  out.rcnt = rr(document.getElementById('rcnt'));
  out.main = rr(document.getElementById('main'));
  out.search = rr(document.getElementById('search'));
  out.hdtb = rr(document.getElementById('hdtb'));
  out.appbar = rr(document.getElementById('appbar'));
  out.topstuff = rr(document.getElementById('topstuff'));
  // ancestors of #center_col with display/grid info
  var col = document.getElementById('center_col');
  out.colChain = [];
  var el = col ? col.parentElement : null;
  for (var i=0; el && i<8; i++, el = el.parentElement) {
    var cs = getComputedStyle(el);
    out.colChain.push({d:desc(el), display:cs.display, gridCols:cs.gridTemplateColumns,
      w:Math.round(el.getBoundingClientRect().width), l:Math.round(el.getBoundingClientRect().left)});
  }
  out.colDisplay = col ? getComputedStyle(col).display : null;
  out.colParentDisplay = col && col.parentElement ? getComputedStyle(col.parentElement).display : null;
  out.colParentGrid = col && col.parentElement ? getComputedStyle(col.parentElement).gridTemplateColumns : null;
  out.colSelfGridColumn = col ? getComputedStyle(col).gridColumn : null;
  // pill
  var pill = document.querySelector('#searchform .A8SBwf, #searchform div[role="combobox"], #searchform .RNNXgb');
  out.pill = rr(pill); out.pillDesc = desc(pill);
  // AI text anywhere?
  out.aiRe = /AI Overview|Visão geral criada por IA/.test(document.body.innerText||'');
  // top-level blocks inside column
  var blocks = [];
  if (col) {
    for (var j=0; j<col.children.length; j++) {
      var c = col.children[j]; var r = c.getBoundingClientRect();
      blocks.push({d:desc(c), l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width),
                   t:Math.round(r.top), h:Math.round(r.height)});
    }
  }
  out.colBlocks = blocks.slice(0,16);
  // "About" heading-ish
  var about = [];
  var all = document.querySelectorAll('div,span,h1,h2,h3');
  for (var k=0;k<all.length;k++){ var e=all[k]; if(e.children.length>1) continue;
    var t=(e.textContent||'').trim();
    if(/^(About|Sobre)\b/.test(t) && t.length<70){ var r=e.getBoundingClientRect();
      if(r.top<2500 && r.width>10) about.push([t.slice(0,44), Math.round(r.left), Math.round(r.top), Math.round(r.width), desc(e.parentElement)]); } }
  out.aboutHits = about.slice(0,8);
  // image strip
  var imgs = document.querySelectorAll('img'), ti = [];
  for (var m=0;m<imgs.length;m++){ var r=imgs[m].getBoundingClientRect();
    if(r.top<1700 && r.width>70 && r.height>70) ti.push([Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)]); }
  out.topImages = {count: ti.length, sample: ti.slice(0,12)};
  // tab labels
  var LABELS=["Modo IA","AI Mode","Tudo","All","Imagens","Images","Vídeos","Videos","Shopping","Notícias","News","Maps","Livros","Books","Web","Fórum","Forums","Mais","More","Ferramentas","Tools"];
  var hits=[];
  for (var n=0;n<all.length;n++){ var e2=all[n]; if(e2.children.length>2) continue;
    var t2=(e2.textContent||'').trim();
    if(t2.length<=16 && LABELS.indexOf(t2)!==-1){ var r2=e2.getBoundingClientRect();
      if(r2.width>5&&r2.height>5&&r2.top<320) hits.push([t2,Math.round(r2.left),Math.round(r2.top),Math.round(r2.width)]); } }
  out.tabHits = hits.slice(0,16);
  return JSON.stringify(out);
}"""
cmd(s, 2, "WebDriver:ExecuteScript", {"script": DEFINE, "args": []})
r = cmd(s, 3, "WebDriver:ExecuteScript", {"script": "return JSON.stringify(window.__serp())", "args": []})
val = r.get("value") if isinstance(r, dict) else r
print(val)
try:
    d = json.loads(val)
    print("\n--- SUMMARY ---")
    print("viewport:", d.get("vw"), "center:", d.get("center"))
    print("col:", d.get("col"), d.get("colDesc"))
    print("col display:", d.get("colDisplay"), "| parent display:", d.get("colParentDisplay"),
          "| parent grid:", d.get("colParentGrid"), "| col gridColumn:", d.get("colSelfGridColumn"))
    print("rhs:", d.get("rhs"))
    print("pill:", d.get("pill"))
    print("aiRe:", d.get("aiRe"))
    print("colChain:")
    for c in (d.get("colChain") or []):
        print("   ", c)
    print("colBlocks:")
    for b in (d.get("colBlocks") or []):
        print("   ", b)
    print("aboutHits:")
    for a in (d.get("aboutHits") or []):
        print("   ", a)
    print("topImages:", d.get("topImages"))
    print("tabHits:", d.get("tabHits"))
except Exception as e:
    print("parse err:", e)