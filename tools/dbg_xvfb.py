#!/usr/bin/env python3
"""Debug: Xvfb + visible firefox via geckodriver, print driver stderr on failure."""
import json, os, time, subprocess, urllib.request, urllib.error, threading

xvfb = subprocess.Popen(["Xvfb", ":99", "-screen", "0", "2560x1440x24", "-nolisten", "tcp"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)
env = dict(os.environ)
for k in ("HTTP_PROXY","HTTPS_PROXY","http_proxy","https_proxy","ALL_PROXY","all_proxy"): env.pop(k, None)
env["DISPLAY"] = ":99"
proc = subprocess.Popen(["geckodriver","--port","4472","--log","debug"],
                        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
time.sleep(3)

def readish():
    time.sleep(4)
    try:
        out = proc.stdout.read()
        if out: print("GECKO LOG:\n", out[-4000:])
    except Exception as e:
        print("log read err:", e)

threading.Thread(target=readish, daemon=True).start()

try:
    req = urllib.request.Request("http://127.0.0.1:4472/session",
        data=json.dumps({"capabilities":{"alwaysMatch":{"moz:firefoxOptions":{"args":["-profile","/home/agentuser/fx-profiles/tst2","-no-remote"]}}}}).encode(),
        method="POST", headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        print("SESSION OK:", resp.read()[:300])
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read()[:400])
except Exception as e:
    print("ERR:", type(e).__name__, str(e)[:300])
time.sleep(3)
proc.terminate(); xvfb.terminate(); time.sleep(1)