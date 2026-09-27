#!/usr/bin/env python3
"""Live verification on the REAL Google SERP with the real add-on.

Installs the built xpi as a TEMPORARY add-on through marionette (no
geckodriver → no navigator.webdriver flag → Google serves the real page),
navigates to the SERP, then measures the centered blocks and screenshots.

Usage: live_verify_panel.py PORT XPI URL [out.png]
"""
import socket, json, sys, base64, time

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 2828
XPI = sys.argv[2] if len(sys.argv) > 2 else "/home/agentuser/Projects/firefox-google-center/web-ext-artifacts/google_search_centered-1.0.4.zip"
URL = sys.argv[3] if len(sys.argv) > 3 else "https://www.google.com/search?q=banana&hl=en"
OUT = sys.argv[4] if len(sys.argv) > 4 else "/tmp/live_panel_after.png"

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

s = socket.create_connection(("127.0.0.1", PORT), timeout=30)
recv_msg(s)
try:
    cmd(s, 1, "WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
except RuntimeError as e:
    print("session:", str(e)[:200])

print("install addon:", json.dumps(cmd(s, 2, "Addon:Install", {"path": XPI, "temporary": True}))[:200])
print("navigate:", json.dumps(cmd(s, 3, "WebDriver:Navigate", {"url": URL}))[:160])
time.sleep(15)

MEAS = r"""
window.__lv = function () {
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width), c:Math.round(r.left+r.width/2)}; }
  var vw = document.documentElement.clientWidth;
  var col=document.getElementById('center_col'), rhs=document.getElementById('rhs'), rcnt=document.getElementById('rcnt');
  var pil=document.querySelector('#searchform .A8SBwf, #searchform div[role="combobox"], #searchform .RNNXgb');
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
  var tabs=null;
  if (row.length>=2){ var minL=Infinity,maxR=-Infinity;
    for (var m=0;m<row.length;m++){ var r2=row[m].getBoundingClientRect();
      minL=Math.min(minL,r2.left); maxR=Math.max(maxR,r2.right); }
    tabs={l:Math.round(minL), r:Math.round(maxR), w:Math.round(maxR-minL), c:Math.round((minL+maxR)/2)}; }
  var strip=null, kids=rcnt?rcnt.children:[];
  for (var n=0;n<kids.length;n++){ var cs=getComputedStyle(kids[n]);
    if (cs.gridColumnStart==='1' && cs.gridColumnEnd==='-1' && kids[n].getBoundingClientRect().height>20){ strip=kids[n]; break; } }
  var union=null;
  if (col && rhs) { var a=col.getBoundingClientRect(), b=rhs.getBoundingClientRect();
    var l=Math.min(a.left,b.left), r=Math.max(a.right,b.right);
    union={l:Math.round(l), r:Math.round(r), w:Math.round(r-l), c:Math.round((l+r)/2), off:Math.round((l+r)/2 - vw/2)}; }
  return JSON.stringify({vw:vw, center:Math.round(vw/2), title:document.title.slice(0,40),
    col:rr(col), rhs:rr(rhs), pill:rr(pil), tabs:tabs, strip:rr(strip), union:union,
    aiText: /AI Overview/.test(document.body.innerText||''),
    rcntInline: rcnt ? (rcnt.getAttribute('style')||'').slice(0,120) : null,
    colInline: col ? (col.getAttribute('style')||'').slice(0,120) : null});
}"""
cmd(s, 4, "WebDriver:ExecuteScript", {"script": MEAS, "args": []})
r = cmd(s, 5, "WebDriver:ExecuteScript", {"script": "return window.__lv()", "args": []})
d = r.get("value")
for _ in range(3):
    if isinstance(d, str):
        try: d = json.loads(d)
        except Exception: break
    else: break
print("\n== LIVE MEASURE (add-on 1.0.4 active) ==")
if isinstance(d, dict):
    for k in ("vw","center","title","col","rhs","pill","tabs","strip","union","aiText","rcntInline","colInline"):
        print(f"  {k}: {d.get(k)}")
    u = d.get("union") or {}
    ok = abs(u.get("off", 999)) <= 6
    print("\nVERDICT:", "GREEN — content zone centered" if ok else f"RED — zone off by {u.get('off')}px")
else:
    print("  raw:", str(d)[:400])

try:
    r = cmd(s, 6, "WebDriver:TakeScreenshot", {"full": False})
    b64 = r.get("value")
    if isinstance(b64, str) and len(b64) > 100:
        open(OUT, "wb").write(base64.b64decode(b64))
        print("screenshot:", OUT)
except Exception as e:
    print("screenshot err:", e)