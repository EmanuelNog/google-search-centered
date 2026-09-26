#!/usr/bin/env python3
"""Minimal: open a browser session (any profile) and report the OS error from geckodriver."""
import json, os, sys, time, subprocess, urllib.request, urllib.error

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 4483
BASE = f"http://127.0.0.1:{PORT}"
env = dict(os.environ)
for k in ("HTTP_PROXY","HTTPS_PROXY","http_proxy","https_proxy","ALL_PROXY","all_proxy"): env.pop(k, None)
proc = subprocess.Popen(["geckodriver","--port",str(PORT),"--log","debug"], env=env,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
time.sleep(3)

class C:
    buf = []
    def __getattr__(self, n): return self.stop
    def stop(self): return None
c = C()

def drain():
    import threading
    def _r():
        while True:
            line = proc.stdout.readline()
            if not line: break
            c.buf.append(line)
    threading.Thread(target=_r, daemon=True).start()

drain()
try:
    req = urllib.request.Request(BASE+"/session",
        data=json.dumps({"capabilities":{"alwaysMatch":{}}}).encode(),
        method="POST", headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        print("SESSION OK:", resp.read()[:250])
except Exception as e:
    print("ERR:", type(e).__name__, str(e)[:250])
time.sleep(2)
tail = "".join(c.buf)[-2500:]
print("---- GECKODRIVER LOG ----")
print(tail)
proc.terminate(); time.sleep(1)