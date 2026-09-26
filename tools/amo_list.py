#!/usr/bin/env python3
"""Submit the current build of Google Search Centered as a LISTED (public store)
version via the AMO API v5.

Why this exists: `web-ext sign --channel listed` cannot attach a license, and
AMO rejects listed versions without one ("This field, or custom_license, is
required for listed versions"). The API version-create call takes a license id
directly. This mirrors the proven flow used for xcom-reels-blocker.

Flow: upload (channel=listed) -> poll validation -> create listed version with
license + release notes. Idempotent: exits early if the manifest version is
already on AMO in any channel.

Creds: BWS (AMO_API_KEY / AMO_API_SECRET, project General-Projects).
"""
import base64, hashlib, hmac, json, os, subprocess, sys, time, uuid, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
API = "https://addons.mozilla.org/api/v5"
SLUG = "google-search-centered"
LICENSE = "MPL-2.0"
BWS = os.path.expanduser("~/.hermes/bin/bws")

MANIFEST = json.load(open(os.path.join(PROJ, "manifest.json")))
VERSION = MANIFEST["version"]
XPI = os.path.join(PROJ, "web-ext-artifacts", f"google_search_centered-{VERSION}.zip")
RELEASE_NOTES = {
    "en-US": ("Centers the AI overview panel as well as the results column, the search bar "
              "and the filter tabs. New original icon art. Full scope: results, search bar, "
              "filter tabs and AI overview are centered on wide screens (>=1440px) when no "
              "knowledge panel is shown.")
}


def creds():
    out = subprocess.run([BWS, "secret", "list", "--output", "json"], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit("ERROR: cannot read BWS secrets: " + out.stderr.strip()[:200])
    s = {x["key"]: x["value"] for x in json.loads(out.stdout)}
    try:
        return s["AMO_API_KEY"], s["AMO_API_SECRET"]
    except KeyError:
        sys.exit("ERROR: AMO_API_KEY / AMO_API_SECRET not in BWS")


def b64u(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def jwt(issuer, secret):
    h = b64u(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    now = int(time.time())
    p = b64u(json.dumps({"iss": issuer, "jti": str(uuid.uuid4()), "iat": now, "exp": now + 120}).encode())
    sig = b64u(hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest())
    return f"{h}.{p}.{sig}"


def req(method, url, token, body=None, headers=None):
    h = {"Authorization": f"JWT {token}"}
    if headers:
        h.update(headers)
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            raw = resp.read()
            try:
                parsed = json.loads(raw) if raw else None
            except Exception:
                parsed = raw
            return resp.status, parsed
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw[:400].decode(errors="replace")
        return e.code, parsed


def multipart(field, filename, data, extra=None):
    boundary = "----amo" + uuid.uuid4().hex
    parts = []
    if extra:
        for k, v in extra.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts += [
        f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
        f'Content-Type: application/octet-stream\r\n\r\n'.encode(),
        data, b"\r\n", f"--{boundary}--\r\n".encode(),
    ]
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def main():
    issuer, secret = creds()
    token = jwt(issuer.strip(), secret.strip())

    # idempotency: is this version already on AMO (any channel)?
    st, vs = req("GET", f"{API}/addons/addon/{SLUG}/versions/?filter=all_with_unlisted&page_size=20", token)
    if st == 200:
        for v in vs.get("results", []):
            if v.get("version") == VERSION:
                print(f"v{VERSION} already on AMO: channel={v.get('channel')} — nothing to do")
                return 0
    else:
        print(f"warning: cannot list versions: HTTP {st} {json.dumps(vs)[:160]}")

    if not os.path.exists(XPI):
        sys.exit(f"ERROR: build missing: {XPI} (run web-ext build first)")
    print(f"submitting {os.path.basename(XPI)} as {SLUG} v{VERSION} (listed)")

    # 1. upload on the listed channel
    data, ctype = multipart("upload", os.path.basename(XPI), open(XPI, "rb").read(),
                            extra={"channel": "listed"})
    st, resp = req("POST", f"{API}/addons/upload/", token, data, {"Content-Type": ctype})
    if st != 201:
        print("upload failed:", st, json.dumps(resp)[:400])
        return 1
    uid = resp["uuid"]
    print("upload ok:", uid)

    # 2. poll validation
    valid = False
    for _ in range(60):
        st, resp = req("GET", f"{API}/addons/upload/{uid}/", token)
        if isinstance(resp, dict) and resp.get("processed"):
            valid = bool(resp.get("valid"))
            break
        time.sleep(3)
    if not valid:
        print("validation FAILED:", json.dumps(resp.get("validation_results", {}).get("errors", []))[:600])
        return 1
    print("validation passed")

    # 3. create the listed version — the license id is what web-ext cannot send
    body = json.dumps({"upload": uid, "license": LICENSE,
                       "release_notes": RELEASE_NOTES}).encode()
    st, resp = req("POST", f"{API}/addons/addon/{SLUG}/versions/", token, body,
                   {"Content-Type": "application/json"})
    if st not in (201, 202):
        print("version create failed:", st, json.dumps(resp)[:600])
        return 1
    print("submitted:",
          "version=", resp.get("version"),
          "| channel=", resp.get("channel"),
          "| file_status=", (resp.get("file") or {}).get("status"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
