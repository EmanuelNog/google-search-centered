#!/usr/bin/env python3
"""Experiment on the LIVE banana SERP (marionette): how does each candidate
fix move the block? Candidates:
  A) padding-left on #rcnt  (shifts fixed tracks right, 1fr absorbs)
  B) translateX on col + rhs
Measures the entity header, photo strip, column, panel and the pill/tabs.
Usage: exp_panel_fix.py PORT
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
    print("session:", str(e)[:150])

DEFINE = r"""
window.__m2 = function () {
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width), c:Math.round(r.left+r.width/2)}; }
  var vw = document.documentElement.clientWidth;
  var col = document.getElementById('center_col');
  var rhs = document.getElementById('rhs');
  var rcnt = document.getElementById('rcnt');
  var pil = document.querySelector('#searchform .A8SBwf, #searchform div[role="combobox"], #searchform .RNNXgb');
  // tab row via label clustering
  var LABELS=["AI Mode","All","Images","Shopping","Videos","Short videos","News","More","Tools"];
  var labels=[], all=document.querySelectorAll('a,span,div,button');
  for (var i=0;i<all.length;i++){ var e=all[i]; if(e.children.length>2) continue;
    var t=(e.textContent||'').trim();
    if(t.length<=16 && LABELS.indexOf(t)!==-1){ var r=e.getBoundingClientRect();
      if(r.width>5&&r.height>5&&r.top<320) labels.push(e); } }
  var buckets={};
  for (var j=0;j<labels.length;j++){ var tb=Math.round(labels[j].getBoundingClientRect().top/20)*20;
    (buckets[tb]=buckets[tb]||[]).push(labels[j]); }
  var row=[]; for (var k in buckets) if(buckets[k].length>row.length) row=buckets[k];
  var tabBox=null;
  if (row.length>=2){ var minL=Infinity,maxR=-Infinity;
    for (var m=0;m<row.length;m++){ var r2=row[m].getBoundingClientRect();
      minL=Math.min(minL,r2.left); maxR=Math.max(maxR,r2.right); }
    tabBox={l:Math.round(minL), r:Math.round(maxR), w:Math.round(maxR-minL), c:Math.round((minL+maxR)/2)}; }
  var ent = document.querySelector('#rcnt > .SLPe5b');
  var strip = document.querySelector('#rcnt > .bzXtMb, #rcnt > div[class*="bzXtMb"]');
  var out = {vw: vw, center: Math.round(vw/2),
    col: rr(col), rhs: rr(rhs), ent: rr(ent), strip: rr(strip), pill: rr(pil), tabs: tabBox,
    rcntStyle: rcnt ? (rcnt.getAttribute('style')||'') : null,
    rcntPadL: rcnt ? getComputedStyle(rcnt).paddingLeft : null,
    rcntCols: rcnt ? getComputedStyle(rcnt).gridTemplateColumns.slice(0,80) : null,
    colTf: col?getComputedStyle(col).transform:null,
    rhsTf: rhs?getComputedStyle(rhs).transform:null};
  // union of col+rhs (+entity header if it spans wider)
  var boxes=[col,rhs,ent].filter(Boolean).map(rr);
  if (boxes.length){ var l=Math.min.apply(null,boxes.map(function(b){return b.l;}));
    var r=Math.max.apply(null,boxes.map(function(b){return b.r;}));
    out.union={l:l,r:r,w:r-l,c:Math.round((l+r)/2),off:Math.round((l+r)/2 - vw/2)}; }
  return JSON.stringify(out);
}"""
cmd(s, 2, "WebDriver:ExecuteScript", {"script": DEFINE, "args": []})

def measure(tag):
    r = cmd(s, 3, "WebDriver:ExecuteScript", {"script": "return JSON.stringify(window.__m2())", "args": []})
    val = r.get("value")
    d = val
    for _ in range(3):
        if isinstance(d, str):
            try: d = json.loads(d)
            except Exception: break
        else: break
    print(f"\n== {tag} ==")
    if not isinstance(d, dict):
        print(" raw:", str(val)[:300]); return None
    for key in ("vw", "center", "col", "rhs", "ent", "strip", "pill", "tabs", "union",
                "rcntPadL", "colTf", "rhsTf", "rcntStyle"):
        print(f"  {key}: {d.get(key)}")
    return d

before = measure("BEFORE")

# --- candidate A: padding-left on #rcnt ---
APPLY_A = r"""
window.__applyA = function () {
  var rcnt = document.getElementById('rcnt');
  var col = document.getElementById('center_col'), rhs = document.getElementById('rhs');
  var ent = document.querySelector('#rcnt > .SLPe5b');
  var vw = document.documentElement.clientWidth;
  var boxes=[col,rhs,ent].filter(Boolean).map(function(e){var r=e.getBoundingClientRect();
    return {l:r.left,r:r.right};});
  var l=Math.min.apply(null,boxes.map(function(b){return b.l;}));
  var r=Math.max.apply(null,boxes.map(function(b){return b.r;}));
  var delta = Math.round(vw/2 - (l+r)/2);
  rcnt.style.paddingLeft = delta + 'px';
  return JSON.stringify({delta: delta});
}"""
cmd(s, 4, "WebDriver:ExecuteScript", {"script": APPLY_A, "args": []})
r = cmd(s, 5, "WebDriver:ExecuteScript", {"script": "return window.__applyA()", "args": []})
print("\napplyA:", r.get("value"))
after_a = measure("AFTER A (padding-left on #rcnt)")

# revert
cmd(s, 6, "WebDriver:ExecuteScript", {"script": "document.getElementById('rcnt').style.paddingLeft=''; return 'ok'", "args": []})

# --- candidate B: translateX on col + rhs ---
APPLY_B = r"""
window.__applyB = function () {
  var col = document.getElementById('center_col'), rhs = document.getElementById('rhs');
  var ent = document.querySelector('#rcnt > .SLPe5b');
  var vw = document.documentElement.clientWidth;
  var boxes=[col,rhs,ent].filter(Boolean).map(function(e){var r=e.getBoundingClientRect();
    return {l:r.left,r:r.right};});
  var l=Math.min.apply(null,boxes.map(function(b){return b.l;}));
  var r=Math.max.apply(null,boxes.map(function(b){return b.r;}));
  var delta = Math.round(vw/2 - (l+r)/2);
  [col,rhs].forEach(function(e){ e.style.transform = 'translateX(' + delta + 'px)'; });
  return JSON.stringify({delta: delta});
}"""
cmd(s, 7, "WebDriver:ExecuteScript", {"script": APPLY_B, "args": []})
r = cmd(s, 8, "WebDriver:ExecuteScript", {"script": "return window.__applyB()", "args": []})
print("\napplyB:", r.get("value"))
after_b = measure("AFTER B (translate col+rhs)")