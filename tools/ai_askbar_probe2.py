#!/usr/bin/env python3
"""AI ask-bar centering, round 2: deep chains, screenshot, native-narrow comparison.

Usage: ai_askbar_probe2.py PORT URL
"""
import socket, json, sys, time, subprocess

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 2828
URL = sys.argv[2] if len(sys.argv) > 2 else "https://www.google.com/search?q=what+is+a+banana&hl=en&gl=us"
SCR = "/tmp/ai_state.png"

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

def xdo(*args):
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    env["DISPLAY"] = ":99"
    subprocess.run(["xdotool"] + list(args), env=env, capture_output=True)

S = socket.create_connection(("127.0.0.1", PORT), timeout=30)
recv_msg(S)
try:
    cmd(S, 1, "WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
except RuntimeError as e:
    print("session:", str(e)[:150])

print("navigate:", json.dumps(cmd(S, 2, "WebDriver:Navigate", {"url": URL}))[:80])
time.sleep(15)

SETUP = r"""
window.__ab2 = function () {
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width), t:Math.round(r.top), h:Math.round(r.height), c:Math.round(r.left+r.width/2)}; }
  function cls(e){ return String((e&&e.className)||'').slice(0,55); }
  function deepChain(e, max){ var a=[], n=e; for(var i=0;i<(max||14)&&n;i++,n=n.parentElement){
    var mark = (n.style&&n.style.transform) ? ' [tf '+n.style.transform+']' : '';
    var idm = (n.id==='eKIzJc'||n.id==='Odp5De'||n.id==='m-x-content') ? ' ***'+n.id : '';
    a.push(n.tagName+(n.id?'#'+n.id:'')+'.'+cls(n)+mark+idm); } return a; }
  var vw=document.documentElement.clientWidth, center=Math.round(vw/2);
  var ek=document.getElementById('eKIzJc');
  var ta=document.querySelector('textarea');
  var wpo=document.querySelector('.wPoHPd');
  return JSON.stringify({vw:vw, center:center,
    eKIzJc: ek?rr(ek):null, eKIzJcChain: ek?deepChain(ek):null,
    textarea: ta?rr(ta):null, taChain: ta?deepChain(ta):null,
    wPoHPd: wpo?rr(wpo):null, wpoChain: wpo?deepChain(wpo):null});
}
"""
cmd(S, 3, "WebDriver:ExecuteScript", {"script": SETUP, "args": []})

def show(label, mid):
    d = run_js(S, mid, "return window.__ab2()")
    print(f"\n== {label} (vw={d.get('vw')} center={d.get('center')}) ==")
    print("eKIzJc:", d.get("eKIzJc"))
    print("  chain:", d.get("eKIzJcChain"))
    print("textarea:", d.get("textarea"))
    print("  chain:", d.get("taChain"))
    print("wPoHPd:", d.get("wPoHPd"))
    print("  chain:", d.get("wpoChain"))
    return d

show("with add-on, 2327", 4)

# screenshot now
try:
    r = cmd(S, 5, "WebDriver:TakeScreenshot", {"full": False})
    import base64
    b64 = r.get("value")
    if isinstance(b64, str) and len(b64) > 100:
        open(SCR, "wb").write(base64.b64decode(b64)); print("screenshot:", SCR)
except Exception as e:
    print("shot err:", e)

# resize narrow => add-on inactive => native relationship
xdo("search", "--class", "firefox", "windowsize", "%1", "1280", "1400")
time.sleep(3)
show("NATIVE-ish at 1280 (add-on inactive)", 6)
# restore
xdo("search", "--class", "firefox", "windowsize", "%1", "2327", "1400")
time.sleep(3)
show("back to 2327", 7)
