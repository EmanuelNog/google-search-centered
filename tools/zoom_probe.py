#!/usr/bin/env python3
"""Zoom sweep probe: verify centering (zone + strip content) across browser zoom levels.

Sends Ctrl+= / Ctrl+- / Ctrl+0 via marionette actions and snapshots after each step.
Usage: zoom_probe.py PORT
"""
import socket, json, sys, time

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
    if ans[2]: raise RuntimeError(f"{name}: {json.dumps(ans[2])[:300]}")
    return ans[3]

def run_js(s, mid, script):
    r = cmd(s, mid, "WebDriver:ExecuteScript", {"script": script, "args": []})
    d = r.get("value")
    for _ in range(3):
        if isinstance(d, str):
            try: d = json.loads(d)
            except Exception: break
        else: break
    return d

S = socket.create_connection(("127.0.0.1", PORT), timeout=30)
recv_msg(S)
try:
    cmd(S, 1, "WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
except RuntimeError as e:
    print("session:", str(e)[:200])

SETUP = r"""
window.__zs = function () {
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width), c:Math.round(r.left+r.width/2)}; }
  var vw = document.documentElement.clientWidth, center = Math.round(vw/2);
  var col=document.getElementById('center_col'), rhs=document.getElementById('rhs');
  var zone=null;
  if(col&&rhs){ var a=col.getBoundingClientRect(), b=rhs.getBoundingClientRect();
    var l=Math.min(a.left,b.left), r=Math.max(a.right,b.right);
    zone={c:Math.round((l+r)/2), off:Math.round((l+r)/2-center)}; }
  var sc=document.querySelector('.bzXtMb .Kevs9') || document.querySelector('.Kevs9');
  var scc=sc?rr(sc):null;
  var pill=document.querySelector('#searchform .A8SBwf, #searchform div[role="combobox"], #searchform .RNNXgb');
  return JSON.stringify({vw:vw, center:center, dpr:window.devicePixelRatio,
    zone:zone, stripC: scc, stripOff: scc?Math.round(scc.c-center):null,
    pillOff: (function(p){ if(!p) return null; var r=p.getBoundingClientRect(); return Math.round(r.left+r.width/2-center); })(pill),
    zoom: (function(){ var m=1; try { m = parseFloat((matchMedia('(resolution: 1dppx)').media?1:window.devicePixelRatio)||1); } catch(e){} return m; })()
  });
}
"""
cmd(S, 2, "WebDriver:ExecuteScript", {"script": SETUP, "args": []})

def snap(label, mid):
    d = run_js(S, mid, "return window.__zs()")
    print(f"[{label}] vw={d.get('vw')} center={d.get('center')} dpr={round(d.get('dpr',0),3)} zoneOff={ (d.get('zone') or {}).get('off') } stripOff={d.get('stripOff')} pillOff={d.get('pillOff')}")
    return d

def zoom_action(mid, key):
    acts = {"type": "key", "id": "kb", "actions": [
        {"type": "keyDown", "value": "\uE009"},
        {"type": "keyDown", "value": key},
        {"type": "keyUp", "value": key},
        {"type": "keyUp", "value": "\uE009"},
    ]}
    try:
        cmd(S, mid, "WebDriver:PerformActions", {"actions": [acts]})
        print(f"  (sent Ctrl+{key})")
    except RuntimeError as e:
        print(f"  PerformActions Ctrl+{key} failed: {str(e)[:120]}")

snap("baseline (current zoom)", 3)
zoom_action(4, "=")
time.sleep(1.5); snap("zoom-in x1", 5)
zoom_action(6, "=")
time.sleep(1.5); snap("zoom-in x2", 7)
zoom_action(8, "-")
time.sleep(1.5); zoom_action(9, "-")
time.sleep(1.5); snap("zoom-out x2 (net 100%)", 10)
zoom_action(11, "=")
time.sleep(1.5); snap("zoom-in x1 again", 12)
zoom_action(13, "0")
time.sleep(1.5); snap("reset Ctrl+0", 14)
