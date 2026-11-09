#!/usr/bin/env python3
"""Dump the AI Overview control tree: which node carries the transform.

Usage: live_aiprobe.py PORT [WIDTH HEIGHT]

Reports, live off the user's SERP:
  - viewport / column / rhs / rcnt-grid geometry,
  - the AI heading ancestor chain (tag.cls, rect, inline transform),
  - every "Show more"/"Mostrar mais" label: rect, inline transform, 8 ancestors,
  - every input/textarea outside #searchform: rect, inline transform, 8 ancestors.
The point is to see WHICH node our code translates and whether it is the frame
(the pill border / the rounded bar) or an inner group (hover fill / +button row).
"""
import socket, json, sys, base64, time

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 2828
W = int(sys.argv[2]) if len(sys.argv) > 2 else 0
H = int(sys.argv[3]) if len(sys.argv) > 3 else 0


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


S = socket.create_connection(("127.0.0.1", PORT), timeout=30)
recv_msg(S)
try:
    cmd(S, 1, "WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
except RuntimeError as e:
    print("session:", str(e)[:150])

mid = 2
if W and H:
    try:
        cmd(S, mid, "WebDriver:SetWindowRect", {"x": 0, "y": 0, "width": W, "height": H})
    except Exception as e:
        print("resize:", str(e)[:120])
    mid += 1
    time.sleep(2)

PROBE = r"""
window.__dump = function () {
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width),
            t:Math.round(r.top), h:Math.round(r.height),
            c:Math.round(r.left + r.width/2)}; }
  function id(e){ if(!e||!e.tagName) return '?';
    return e.tagName.toLowerCase() + (e.id?('#'+e.id):'') +
      (e.className && typeof e.className==='string' && e.className.trim() ?
        '.'+e.className.trim().split(/\s+/).join('.') : ''); }
  function chain(seed, n){
    var out=[], e=seed;
    for (var i=0; i<n && e && e!==document.body; i++, e=e.parentElement){
      out.push({sel:id(e), box:rr(e), tf:e.style && e.style.transform || '',
                disp:getComputedStyle(e).display, pos:getComputedStyle(e).position});
    }
    return out;
  }
  var vw = document.documentElement.clientWidth;
  var out = {vw:vw, vh:document.documentElement.clientHeight, dpr:window.devicePixelRatio,
             center:Math.round(vw/2), scrollW:document.documentElement.scrollWidth,
             title:document.title.slice(0,80)};
  var col=document.getElementById('center_col'), rhs=document.getElementById('rhs'),
      rcnt=document.getElementById('rcnt');
  out.col=rr(col); out.rhs=rr(rhs);
  if (rhs){ var cs=getComputedStyle(rhs); out.rhsVisible = cs.display!=='none' && rhs.getBoundingClientRect().width>0; }
  out.rcnt = rcnt ? {box:rr(rcnt), disp:getComputedStyle(rcnt).display,
                     tracks:getComputedStyle(rcnt).gridTemplateColumns,
                     inline:rcnt.style.gridTemplateColumns} : null;

  // AI heading
  var labels=['AI Overview','Visão geral criada por IA'];
  var head=null;
  var all=document.querySelectorAll('div,span,h1,h2,h3');
  for (var i=0;i<all.length;i++){
    var e=all[i];
    if (e.children.length>3) continue;
    if (labels.indexOf((e.textContent||'').trim())===-1) continue;
    var r=e.getBoundingClientRect();
    if (r.width>5 && r.height>5){ head=e; break; }
  }
  out.heading = head ? {sel:id(head), box:rr(head), chain:chain(head,10)} : null;

  // show more labels
  var moreLabels=['Show more','Mostrar mais'];
  out.more=[];
  for (var j=0;j<all.length;j++){
    var m=all[j];
    if (moreLabels.indexOf((m.textContent||'').trim())===-1) continue;
    var mr=m.getBoundingClientRect();
    if (mr.width<5||mr.height<5||mr.width>500) continue;
    out.more.push({sel:id(m), box:rr(m), tf:m.style.transform||'', chain:chain(m,9)});
    if (out.more.length>=2) break;
  }

  // inputs outside the search form
  out.bars=[];
  var ins=document.querySelectorAll('textarea,input');
  for (var k=0;k<ins.length;k++){
    var inp=ins[k];
    if (inp.closest('#searchform')) continue;
    var ir=inp.getBoundingClientRect();
    if (ir.width<60||ir.height<8) continue;
    out.bars.push({sel:id(inp), box:rr(inp), tf:inp.style.transform||'',
                   ph:inp.placeholder||inp.getAttribute('aria-label')||'',
                   chain:chain(inp,10)});
    if (out.bars.length>=2) break;
  }

  // every transformed element inside the results zone (our fingerprints)
  out.transformed=[];
  var zone=document.getElementById('rcnt');
  if (zone){
    var zs=zone.querySelectorAll('*');
    for (var q=0;q<zs.length;q++){
      var tf=zs[q].style && zs[q].style.transform;
      if (tf && tf!=='none') out.transformed.push({sel:id(zs[q]), box:rr(zs[q]), tf:tf});
    }
  }
  return JSON.stringify(out, null, 1);
}
"""
cmd(S, mid, "WebDriver:ExecuteScript", {"script": PROBE, "args": []})
mid += 1
res = cmd(S, mid, "WebDriver:ExecuteScript", {"script": "return window.__dump()", "args": []})
print(res["value"])

if len(sys.argv) > 4:
    png = cmd(S, mid + 1, "WebDriver:TakeScreenshot", {"full": False})
    open(sys.argv[4], "wb").write(base64.b64decode(png["value"]))
    print("screenshot:", sys.argv[4])
