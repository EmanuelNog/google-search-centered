#!/usr/bin/env python3
"""Repro: published GSC 1.0.2 on en-US All tab, measure what the AI-block code does."""
import json, os, shutil, subprocess, sys, time, urllib.request

PROFILE = "/home/agentuser/fx-profiles/tst2"
XPI = sys.argv[1] if len(sys.argv) > 1 else "/tmp/amo102/../amo_102.xpi"
QUERY = sys.argv[2] if len(sys.argv) > 2 else "firefox+extension"
PORT = 4444
BASE = f"http://127.0.0.1:{PORT}"

def req(method, path, body=None):
    r = urllib.request.Request(BASE + path, method=method, headers={"Content-Type": "application/json"})
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(r, data=data, timeout=60) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        return json.loads(raw) if raw else {"error": e.code}

# launch geckodriver with the profile
env = dict(os.environ)
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    env.pop(k, None)
proc = subprocess.Popen(
    ["geckodriver", "--port", str(PORT), "--log", "error"],
    env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
time.sleep(2)
try:
    cap = {
        "capabilities": {
            "alwaysMatch": {
                "moz:firefoxOptions": {
                    "args": ["-headless", "-profile", PROFILE,
                             "-setDefaultBrowser", ""],
                },
                "goog:chromeOptions": None,
            }
        }
    }
    res = req("POST", "/session", cap)
    sid = res.get("value", {}).get("sessionId") or res.get("sessionId")
    if not sid:
        print("NEWSESSION FAIL:", json.dumps(res)[:500]); sys.exit(1)
    print("session:", sid)

    def cmd(method, path, body=None):
        return req(method, f"/session/{sid}{path}", body)

    # install add-on (the published xpi)
    r = cmd("POST", "/moz/addon/install", {"path": XPI, "temporary": True})
    print("addon install:", json.dumps(r)[:200])

    # set a wide window so MIN_WIDTH (1440) is met
    try:
        r = cmd("POST", "/window/rect", {"width": 1920, "height": 1080, "x": 0, "y": 0})
        print("window rect:", json.dumps(r)[:120])
    except Exception as e:
        print("winrect fail:", e)
    time.sleep(2)

    # navigate: en-US All tab (user's real conditions: BR region, EN interface)
    url = f"https://www.google.com.br/search?q={QUERY}&hl=en"
    r = cmd("POST", "/url", {"url": url})
    # wait out any simple challenge, then re-set window, then wait for render
    time.sleep(6)
    for attempt in range(4):
        chk = cmd("POST", "/execute/sync", {"script":
            "return document.title + '|' + (document.querySelector('.g-recaptcha') ? 'RECAPTCHA' : '') + '|' + (document.body && document.body.textContent.indexOf('solveSimpleChallenge') !== -1 ? 'SIMPLE' : '')", "args": []})
        t = chk.get("value") or ""
        print("chk:", t[:80])
        if "SIMPLE" in t:
            cmd("POST", "/execute/sync", {"script":
                "try { if (window.solveSimpleChallenge) { solveSimpleChallenge(0,0); } } catch(e){}; "
                "var b = document.querySelector('form button, form input[type=submit], center button'); "
                "if (b) b.click(); return 'clicked';", "args": []})
            time.sleep(4)
        elif "captcha" in t.lower() or "recaptcha" in t:
            break
        else:
            break
    time.sleep(8)

    r = cmd("POST", "/execute/sync", {"script":
        "return document.documentElement.outerHTML.slice(0, 600)", "args": []})
    print("page head:", (r.get("value") or "")[:600])

    # measure: what getAiBlock finds + post-apply positions
    MEASURE = r"""
    window.__m = function () {
      var vw = document.documentElement.clientWidth;
      var out = {clientW: vw, center: Math.round(vw / 2), aiHits: [], col: null, pill: null, tabs: null, ai: null, aiTf: null, colTf: null, colStyle: null};
      function rr(e) { if (!e) return null; var r = e.getBoundingClientRect();
        return {l: Math.round(r.left), r: Math.round(r.right), w: Math.round(r.width), t: Math.round(r.top)}; }
      out.col = rr(document.getElementById('center_col'));
      out.rhs = rr(document.getElementById('rhs'));
      out.colTf = document.getElementById('center_col') ? getComputedStyle(document.getElementById('center_col')).transform : null;
      out.colStyle = document.getElementById('center_col') ? (document.getElementById('center_col').getAttribute('style') || '') : null;
      out.pill = rr(document.querySelector('#searchform .A8SBwf, #searchform div[role="combobox"], #searchform .RNNXgb'));
      var AI = ['Visão geral criada por IA', 'AI Overview'];
      var all = document.querySelectorAll('div, span, h1, h2, h3');
      for (var i = 0; i < all.length; i++) {
        var e = all[i];
        if (e.children.length > 3) continue;
        var t = (e.textContent || '').trim();
        if (AI.indexOf(t) !== -1) {
          var r0 = e.getBoundingClientRect();
          if (r0.width > 5 && r0.height > 5) out.aiHits.push({tag: e.tagName, w: Math.round(r0.width), h: Math.round(r0.height),
            cls: (typeof e.className === 'string' ? e.className : '').slice(0, 50), parent: (e.parentElement ? e.parentElement.tagName : '')});
        }
      }
      // the exact getAiBlock walk from content.js 1.0.2
      var heading = null;
      for (var i = 0; i < all.length; i++) {
        var e = all[i];
        if (e.children.length > 3) continue;
        var t = (e.textContent || '').trim();
        if (AI.indexOf(t) !== -1) {
          var r0 = e.getBoundingClientRect();
          if (r0.width > 5 && r0.height > 5) { heading = e; break; }
        }
      }
      if (heading) {
        var el = heading, best = null, chain = [];
        for (var i = 0; i < 16 && el && el !== document.body; i++, el = el.parentElement) {
          var w = el.getBoundingClientRect().width;
          chain.push({tag: el.tagName, id: el.id || '', cls: (typeof el.className === 'string' ? el.className : '').slice(0, 36), w: Math.round(w)});
          if (w >= vw * 0.9) break;
          if (w > 500) best = el;
        }
        out.ai = {heading: heading.tagName, hCls: (typeof heading.className === 'string' ? heading.className : '').slice(0, 40), best: best ? {tag: best.tagName, id: best.id, cls: (typeof best.className === 'string' ? best.className : '').slice(0, 50), r: rr(best), tf: getComputedStyle(best).transform, containsCol: !!best.querySelector('#center_col')} : null, chain: chain};
      } else out.ai = 'no heading';
      return JSON.stringify(out);
    }"""
    cmd("POST", "/execute/sync", {"script": MEASURE, "args": []})
    r = cmd("POST", "/execute/sync", {"script": "return JSON.stringify(window.__m())", "args": []})
    val = r.get("value")
    if isinstance(val, str):
        print("MEASURE:", json.dumps(json.loads(val), indent=1)[:3000])
    else:
        print("MEASURE raw:", json.dumps(val)[:3000])

    # tabs row (replicating content.js getTabRow logic)
    TABSROW = r"""
    window.__t = function () {
      var LABELS = ["Modo IA","AI Mode","Tudo","All","Imagens","Images","Videos","Videos","Shopping","Noticias","News","Maps","Livros","Books","Web","Forum","Forums","Videos curtos","Short videos","Mais","More","Ferramentas","Tools"];
      var seen = {}, all = document.querySelectorAll('a, span, div, button');
      for (var i = 0; i < all.length; i++) {
        var e = all[i];
        if (e.children.length > 2) continue;
        var t = (e.textContent || '').trim();
        if (t.length <= 16 && LABELS.indexOf(t) !== -1) {
          var r = e.getBoundingClientRect();
          if (r.width > 5 && r.height > 5 && r.top < 300) {
            var prev = seen[t];
            if (!prev || r.width * r.height > prev.area) seen[t] = {el: e, area: r.width * r.height};
          }
        }
      }
      var labels = [];
      for (var k in seen) labels.push(seen[k].el);
      if (labels.length < 2) return {labels: labels.length, buckets: null};
      var buckets = {};
      for (var j = 0; j < labels.length; j++) {
        var top = Math.round(labels[j].getBoundingClientRect().top / 20) * 20;
        (buckets[top] = buckets[top] || []).push(labels[j]);
      }
      var row = [], bestTop = null;
      for (var b in buckets) if (buckets[b].length > row.length) { row = buckets[b]; bestTop = b; }
      var minL = Infinity, maxR = -Infinity;
      for (var m = 0; m < row.length; m++) {
        var rr = row[m].getBoundingClientRect();
        minL = Math.min(minL, rr.left); maxR = Math.max(maxR, rr.right);
      }
      var out = {labels: labels.length, bucketTop: bestTop, rowLen: row.length, bboxW: Math.round(maxR - minL), center: Math.round((minL + maxR) / 2),
        rects: row.map(function(e){ var r2 = e.getBoundingClientRect(); return {txt: (e.textContent||'').trim().slice(0,14), l: Math.round(r2.left), r: Math.round(r2.right), w: Math.round(r2.width)}; })};
      return JSON.stringify(out);
    }"""
    cmd("POST", "/execute/sync", {"script": TABSROW, "args": []})
    r = cmd("POST", "/execute/sync", {"script": "return JSON.stringify(window.__t())", "args": []})
    print("TABS:", r.get("value"))

    cmd("DELETE", "")
finally:
    proc.terminate()
    time.sleep(1)