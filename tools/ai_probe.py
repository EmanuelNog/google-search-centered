#!/usr/bin/env python3
"""Probe for AI-overview renders: locate #Odp5De / show-more / ask-anything + row geometry.

Usage: ai_probe.py PORT URL
"""
import socket, json, sys, time

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 2828
URL = sys.argv[2] if len(sys.argv) > 2 else "https://www.google.com/search?q=what+is+a+banana&hl=en&gl=us"

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
    print("session:", str(e)[:150])

print("navigate:", json.dumps(cmd(S, 2, "WebDriver:Navigate", {"url": URL}))[:100])
time.sleep(15)

JS = r"""
window.__ai = function () {
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width), t:Math.round(r.top), h:Math.round(r.height), c:Math.round(r.left+r.width/2)}; }
  function cls(e){ return String((e&&e.className)||'').slice(0,60); }
  var vw = document.documentElement.clientWidth, center = Math.round(vw/2);
  var out = {vw:vw, center:center, url:location.href.slice(0,110),
    aiText: /AI Overview|Visão geral criada por IA|Visão geral com IA/.test(document.body.innerText||'')};
  var rhs = document.getElementById('rhs');
  out.rhs = rhs ? {rect: (function(){var r=rhs.getBoundingClientRect(); return {l:Math.round(r.left), w:Math.round(r.width)};})(), vis: (function(){var cs=getComputedStyle(rhs); return cs.display!=='none' && rhs.getBoundingClientRect().width>0;})()} : null;
  var rcnt = document.getElementById('rcnt');
  out.rcntInline = rcnt ? (rcnt.getAttribute('style')||'').slice(0,80) : null;
  var od = document.getElementById('Odp5De');
  out.odp5de = od ? rr(od) : null;
  out.odp5deChain = null;
  if (od) { var ch=[], n=od; for (var i=0;i<7&&n;i++,n=n.parentElement) ch.push(n.tagName+(n.id?'#'+n.id:'')+'.'+cls(n)); out.odp5deChain=ch; }
  out.ekizjc = (function(){ var e=document.getElementById('eKIzJc'); return e?rr(e):null; })();
  var rows=[];
  var bzs=document.querySelectorAll('.bzXtMb');
  for (var i=0;i<bzs.length && i<6;i++){ var b=bzs[i]; var cs=getComputedStyle(b);
    var row={rect:rr(b), gcs:cs.gridColumnStart, gce:cs.gridColumnEnd, text:(b.innerText||'').replace(/\s+/g,' ').slice(0,60)};
    var g=b.querySelector('div');
    var grids=[]; var all=b.querySelectorAll('div');
    for (var j=0;j<all.length;j++){ var el=all[j]; var ecs=getComputedStyle(el);
      if(ecs.display==='grid'){ grids.push({cls:cls(el), rect:rr(el), gtc:ecs.gridTemplateColumns.slice(0,110), inline:(el.getAttribute('style')||'').slice(0,60)}); if(grids.length>=3) break; } }
    row.grids=grids;
    rows.push(row); }
  out.rows=rows;
  // "show more" / "ask anything" candidates by text (any children count, small-ish)
  var cands=[];
  var alls=document.querySelectorAll('button, a, div, span');
  for (var k=0;k<alls.length;k++){ var e=alls[k]; var t=(e.innerText||'').trim();
    if (t.length<=40 && /(show more|ask anything|mostrar mais|pergunte|fazer uma pergunta)/i.test(t)) {
      var r=e.getBoundingClientRect(); if(r.width>5&&r.height>5) {
        var seen=false; for (var c=0;c<cands.length;c++){ if (cands[c].rect.l===Math.round(r.left) && cands[c].rect.t===Math.round(r.top) && cands[c].t===t.slice(0,40)) { seen=true; break; } }
        if(!seen) cands.push({t:t.replace(/\s+/g,' ').slice(0,40), tag:e.tagName, cls:cls(e), rect:rr(e), off: Math.round(r.left+r.width/2-center)}); } } }
  out.askCands=cands.slice(0,10);
  out.bodyHasShowMore = (document.body.innerText.match(/show more/gi)||[]).length;
  out.bodyHasAsk = (document.body.innerText.match(/ask anything/gi)||[]).length;
  // Odp5De bottom-most elements (controls usually live at the panel bottom)
  if (od) {
    var deep=[];
    var oa=od.querySelectorAll('*');
    for (var m=0;m<oa.length;m++){ var q=oa[m]; var qr=q.getBoundingClientRect();
      if (qr.width>5&&qr.height>5) deep.push({t:Math.round(qr.top), cls:cls(q), tag:q.tagName, rect:{l:Math.round(qr.left), r:Math.round(qr.right), w:Math.round(qr.width), t:Math.round(qr.top), h:Math.round(qr.height), c:Math.round(qr.left+qr.width/2)}, txt:(q.innerText||'').replace(/\s+/g,' ').slice(0,50), kidc:q.children.length}); }
    deep.sort(function(a,b){ return b.rect.t - a.rect.t; });
    out.panelBottom=deep.slice(0,12);
  }
  return JSON.stringify(out);
}
"""
cmd(S, 3, "WebDriver:ExecuteScript", {"script": JS, "args": []})
r = cmd(S, 4, "WebDriver:ExecuteScript", {"script": "return window.__ai()", "args": []})
d = r.get("value")
for _ in range(3):
    if isinstance(d, str):
        try: d = json.loads(d)
        except Exception: break
    else: break
if isinstance(d, dict):
    print("url:", d.get("url")); print("vw:", d.get("vw"), "center:", d.get("center"), "aiText:", d.get("aiText"))
    print("rhs:", d.get("rhs"), "| rcntInline:", d.get("rcntInline"))
    print("oddp5de:", d.get("odp5de")); print("odp5deChain:", d.get("odp5deChain")); print("eKIzJc:", d.get("ekizjc"))
    print("bodyHasShowMore:", d.get("bodyHasShowMore"), "bodyHasAsk:", d.get("bodyHasAsk"))
    print("bzXtMb rows:")
    for row in d.get("rows") or []: print("  ", json.dumps(row)[:700])
    print("ask/show-more candidates:")
    for c in d.get("askCands") or []: print("  ", c)
    print("panelBottom (top-most first = lowest on page):")
    for c in d.get("panelBottom") or []: print("  ", c)
else:
    print("raw:", str(d)[:500])
