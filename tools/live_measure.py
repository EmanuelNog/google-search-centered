#!/usr/bin/env python3
"""Measure the live SERP via marionette (no navigation, no install).
Usage: live_measure.py PORT [out.png]
"""
import socket, json, sys, base64

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 2828
OUT = sys.argv[2] if len(sys.argv) > 2 else None

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

s = socket.create_connection(("127.0.0.1", PORT), timeout=30)
recv_msg(s)
try:
    cmd(s, 1, "WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
except RuntimeError as e:
    print("session:", str(e)[:150])

MEAS = open(__file__.replace("live_measure.py", "live_verify_panel.py")).read()
# reuse the measure snippet from live_verify_panel.py
START = MEAS.index('MEAS = r"""') + len('MEAS = r"""')
END = MEAS.index('"""', START)
script = MEAS[START:END]
cmd(s, 2, "WebDriver:ExecuteScript", {"script": script, "args": []})
r = cmd(s, 3, "WebDriver:ExecuteScript", {"script": "return window.__lv()", "args": []})
d = r.get("value")
for _ in range(3):
    if isinstance(d, str):
        try: d = json.loads(d)
        except Exception: break
    else: break
print("== LIVE MEASURE ==")
if isinstance(d, dict):
    for k in ("vw","center","title","col","rhs","pill","tabs","strip","union","aiText","rcntInline","colInline"):
        print(f"  {k}: {d.get(k)}")
    u = d.get("union") or {}
    if abs(u.get("off", 999)) <= 6:
        print("\nVERDICT: GREEN — content zone centered (off %s px)" % u.get("off"))
    else:
        print("\nVERDICT: RED — zone off by %s px" % u.get("off"))
else:
    print("  raw:", str(d)[:400])
if OUT:
    try:
        r = cmd(s, 4, "WebDriver:TakeScreenshot", {"full": False})
        b64 = r.get("value")
        if isinstance(b64, str) and len(b64) > 100:
            open(OUT, "wb").write(base64.b64decode(b64)); print("screenshot:", OUT)
    except Exception as e:
        print("screenshot err:", e)