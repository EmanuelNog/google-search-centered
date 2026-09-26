#!/usr/bin/env python3
"""Visible (Xvfb) render of the published 1.0.2 on a Google SERP, screenshot + measure."""
import json, os, sys, time, subprocess, urllib.request, urllib.error, base64

XPI = sys.argv[1]
URL = sys.argv[2] if len(sys.argv) > 2 else "https://www.google.com/search?q=firefox+extension&hl=en"
W = int(sys.argv[3]) if len(sys.argv) > 3 else 2327
PORT = int(sys.argv[4]) if len(sys.argv) > 4 else 4470
PROFILE = sys.argv[5] if len(sys.argv) > 5 else "/home/agentuser/fx-profiles/tst8"
OUT = sys.argv[6] if len(sys.argv) > 6 else "/tmp/gsc_shot.png"
BASE = f"http://127.0.0.1:{PORT}"

# Xvfb on :99
xvfb = subprocess.Popen(["Xvfb", ":99", "-screen", "0", "2560x1440x24"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)

env = dict(os.environ)
for k in ("HTTP_PROXY","HTTPS_PROXY","http_proxy","https_proxy","ALL_PROXY","all_proxy"): env.pop(k, None)
env["DISPLAY"] = ":99"
proc = subprocess.Popen(["geckodriver","--port",str(PORT),"--log","error"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
time.sleep(2)

def req(method, path, body=None):
    r = urllib.request.Request(BASE+path, method=method, headers={"Content-Type":"application/json"})
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(r, data=data, timeout=90) as resp:
            raw = resp.read()
            try: return json.loads(raw) if raw else {}
            except Exception: return {"raw": raw[:200].decode(errors="replace")}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try: return json.loads(raw) if raw else {"error": e.code}
        except Exception: return {"error": e.code, "raw": raw[:200].decode(errors="replace")}

res = req("POST", "/session", {"capabilities":{"alwaysMatch":{"moz:firefoxOptions":{"args":["-profile", PROFILE, "-no-remote"]}}}})
sid = res.get("value",{}).get("sessionId") or res.get("sessionId")
print("sid:", sid, "| xpi:", os.path.basename(XPI))
def cmd(m, p, b=None): return req(m, f"/session/{sid}{p}", b)

r = cmd("POST","/moz/addon/install", {"path": XPI, "temporary": True})
print("addon:", json.dumps(r)[:80])
try: cmd("POST","/window/rect", {"width": W, "height": 1309, "x":0, "y":0})
except Exception as e: print("rect fail:", e)
time.sleep(2)
cmd("POST","/url", {"url": URL})
time.sleep(14)

# screenshot first via webdriver, else via import on the X display
r = cmd("POST","/screenshot",{})
b64 = r.get("value")
if isinstance(b64, str) and b64:
    open(OUT,"wb").write(base64.b64decode(b64))
    print("SHOT:", OUT, len(base64.b64decode(b64)), "bytes")
else:
    print("SHOT webdriver failed:", str(r)[:120])
    sp = subprocess
    sp.run(["import", "-display", ":99", "-window", "root", OUT], timeout=30)
    print("IMPORT:", os.path.exists(OUT), os.path.getsize(OUT) if os.path.exists(OUT) else 0)

cmd("DELETE","")
proc.terminate(); xvfb.terminate(); time.sleep(1)