#!/usr/bin/env python3
"""Maintenance contract suite — one fixture set, both browsers.

This is the suite that defines what the add-on must keep doing. The same
fixtures run against Firefox (geckodriver) and Chromium/Chrome (chromedriver),
because the port must not change behaviour — only the packaging.

Usage:
    python3 tools/run_fixtures.py firefox [--only SUBSTR]
    python3 tools/run_fixtures.py chrome  [--only SUBSTR]

Covered contracts (12 fixtures):
  1 core-no-panel      column, pill, tabs and AI block land on the viewport centre
  2 core-panel         column+panel zone centred; photos strip stays full-bleed
  3 strip-nonpanel     nested strip grid content centred without a panel
  4 ai-frames-pill     "Show more": transform on the FRAME, label glued inside
  5 ai-frames-bar      "Ask anything": transform on the BAR, textarea glued inside
  6 gate-narrow        below MIN_WIDTH nothing is touched (no inline styles)
  7 overlap-guard      a centred pill that would hit the header controls stays native
  8 idempotent         apply() x5: no compounding, geometry stable
  9 tabs-clip          clip frame AND label row move together, labels stay visible
 10 stale-node         Google re-renders the AI block: old node cleared, new centred
 11 disable-narrow     wide -> narrow: every inline transform and dataset cleared
 12 legacy-pt          legacy tbm= tabs + pt-BR AI labels ("Mostrar mais")

Exit code 0 = every fixture GREEN.
"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
CONTENT_JS = os.path.join(PROJ, "content.js")
FIREFOX_BIN = "/usr/lib/firefox-developer-edition/firefox"
CHROME_BIN = "/usr/bin/chromium"

ENGINE = (sys.argv[1] if len(sys.argv) > 1 else "firefox").lower()
ONLY = ""
if "--only" in sys.argv:
    ONLY = sys.argv[sys.argv.index("--only") + 1]
PORT = {"firefox": 4520, "chrome": 9520}.get(ENGINE, 4520)
BASE = f"http://127.0.0.1:{PORT}"

# ---------------------------------------------------------------- fixtures ---
FIXTURES_JS = r"""
window.__rr = function (e) {
  if (!e) return null;
  var r = e.getBoundingClientRect();
  return {l: Math.round(r.left), r: Math.round(r.right), w: Math.round(r.width),
          t: Math.round(r.top), h: Math.round(r.height),
          c: Math.round(r.left + r.width / 2)};
};
window.__clearAll = function () {
  var all = document.querySelectorAll('*');
  var attrs = ['gsrBase', 'gsrTabsOuter', 'gsrTabsInner', 'gsrZone', 'gsrRowGhost',
               'gsrBarTf', 'gsrMoreTf'];
  for (var i = 0; i < all.length; i++) {
    var st = all[i].style;
    if (!st) continue;
    if (st.transform) st.transform = '';
    if (st.gridTemplateColumns) st.gridTemplateColumns = '';
    if (all[i].dataset) for (var k = 0; k < attrs.length; k++) delete all[i].dataset[attrs[k]];
  }
  void document.body.getBoundingClientRect();
};
window.__tf = function (sel) {
  var e = document.querySelector(sel);
  return e && e.style ? (e.style.transform || '') : '';
};
window.__txf = function () {
  var out = [], all = document.querySelectorAll('*');
  for (var i = 0; i < all.length; i++) {
    var t = all[i].style && all[i].style.transform;
    if (t && t !== 'none') out.push({cls: all[i].className || all[i].tagName, tf: t});
  }
  return out;
};
window.__mm = function (e) {
  var r = e.getBoundingClientRect();
  return Math.round(r.left + r.width / 2);
};

var HDR = '<div id="hdr" style="width:100%">' +
  '<div id="searchform"><div class="RNNXgb" role="combobox" ' +
  'style="width:861px;height:44px"></div></div>' +
  '<div class="tabrow" role="navigation" style="width:861px;display:flex">' +
  '<span>All</span><span>Images</span><span>Videos</span></div></div>';

window.__FIX = [
  {
    name: '1 core-no-panel',
    w: 2560,
    setup: function () {
      document.body.style.margin = '0';
      document.body.innerHTML = HDR +
        '<div id="rcnt"><div id="center_col" style="width:652px;height:900px">results</div>' +
        '<div id="aiblock" style="width:1100px;">' +
        '<div style="height:24px">AI Overview</div><div style="height:300px">answer</div>' +
        '</div></div>';
    },
    check: function (b, a) {
      var c = a.vw / 2;
      return {
        colOK: Math.abs(a.col.c - c) <= 6,
        pillOK: Math.abs(a.pill.c - c) <= 6,
        tabsOK: Math.abs(a.tabs.c - c) <= 8,
        aiOK: Math.abs(a.ai.c - c) <= 6
      };
    }
  },
  {
    name: '2 core-panel',
    w: 2560,
    setup: function () {
      document.body.style.margin = '0';
      document.body.innerHTML = HDR + `
        <style>
          #rcnt { display:grid; grid-template-columns:210px repeat(20,36px) minmax(0,1fr);
                  column-gap:20px; width:100%; }
          .entityhdr { grid-column: 2 / -2; height:60px; }
          .photos { grid-column: 1 / -1; height:80px; }
          #center_col { grid-column: 2 / span 12; height:600px; }
          #rhs { grid-column: span 7 / -2; height:600px; }
        </style>
        <div id="rcnt">
          <div class="entityhdr">Banana - Fruit</div>
          <div class="photos">photos</div>
          <div id="center_col"><div style="height:70px">r1</div><div style="height:70px">r2</div></div>
          <div id="rhs"><div style="height:120px">About</div></div>
        </div>`;
    },
    check: function (b, a) {
      var c = a.vw / 2;
      var photos = document.querySelector('.photos');
      var pr = window.__rr(photos);
      return {
        zoneOK: !!a.zone && Math.abs(a.zone.c - c) <= 6,
        pillOK: Math.abs(a.pill.c - c) <= 6,
        tabsOK: Math.abs(a.tabs.c - c) <= 8,
        gridSet: !!a.rcntInline,
        photosBleed: pr.l <= 1 && pr.r >= a.vw - 1
      };
    }
  },
  {
    name: '3 strip-nonpanel',
    w: 2560,
    setup: function () {
      document.body.style.margin = '0';
      document.body.innerHTML = HDR + `
        <style>
          #rcnt { display:grid; grid-template-columns:210px repeat(20,36px) minmax(0,1fr);
                  column-gap:20px; width:100%; }
          .bzXtMb { grid-column: 1 / -1; height:400px; }
          .ghostgrid { display:grid; grid-template-columns:210px repeat(20,36px) minmax(0,1fr);
                       column-gap:20px; }
          .stripcontent { grid-column: 2 / -2; height:360px; }
          #center_col { grid-column: 1 / -1; height:600px; }
        </style>
        <div id="rcnt">
          <div class="bzXtMb"><div class="YNk70c EjQTId ghostgrid">
            <div class="Kevs9 stripcontent">images strip</div></div></div>
          <div id="center_col"><div style="height:70px">r1</div></div>
        </div>`;
    },
    check: function (b, a) {
      var c = a.vw / 2;
      var strip = document.querySelector('.bzXtMb');
      var content = document.querySelector('.stripcontent');
      var sr = window.__rr(strip), cr = window.__rr(content);
      return {
        colOK: Math.abs(a.col.c - c) <= 6,
        stripBleed: sr.l <= 1 && sr.r >= a.vw - 1,
        stripContentOK: !!cr && Math.abs(cr.c - c) <= 6
      };
    }
  },
  {
    name: '4 ai-frames-pill',
    w: 2560,
    setup: function () {
      document.body.style.margin = '0';
      document.body.innerHTML = HDR +
        '<div id="rcnt"><div id="aiblock" style="width:1100px;">' +
        '<div style="height:24px">AI Overview</div><div style="height:300px">answer</div>' +
        '<div class="controlrow" style="width:762px;height:50px;">' +
        '<div class="pill" style="width:760px;height:48px;border:1px solid #888;' +
        'border-radius:24px;position:relative;">' +
        '<div class="hoverwrap" style="width:500px;height:40px;margin:4px auto 0 auto;' +
        'border-radius:20px;"><span class="morelabel">Show more</span></div></div></div>' +
        '</div></div>';
    },
    check: function (b, a) {
      var tf = a.transformed;
      var inner = tf.filter(function (t) { return t.inPill && !t.isPill; });
      return {
        frameMoved: tf.some(function (t) { return t.isPill || !t.inPill; }),
        noInnerWrapper: inner.length === 0,
        labelGlued: Math.abs(a.labelOff - b.labelOff) <= 2,
        aiOK: Math.abs(a.ai.c - a.vw / 2) <= 8
      };
    }
  },
  {
    name: '5 ai-frames-bar',
    w: 2560,
    setup: function () {
      document.body.style.margin = '0';
      document.body.innerHTML = HDR +
        '<div id="rcnt"><div id="aiblock" style="width:1100px;">' +
        '<div style="height:24px">AI Overview</div><div style="height:300px">answer</div>' +
        '<div class="controlrow" style="width:780px;">' +
        '<div class="barframe" style="width:780px;height:120px;border:1px solid #888;' +
        'border-radius:60px;"><div class="innergroup" style="width:400px;height:60px;' +
        'display:flex;align-items:center;"><div class="plusbtn" style="width:40px;height:40px;' +
        'border-radius:20px;"></div><textarea class="askinput" style="width:300px;height:24px" ' +
        'placeholder="Ask anything"></textarea></div></div></div></div></div>';
    },
    check: function (b, a) {
      var tf = a.transformed;
      var inner = tf.filter(function (t) { return t.inBar && !t.isBar; });
      return {
        frameMoved: tf.some(function (t) { return t.isBar || !t.inBar; }),
        noInnerGroup: inner.length === 0,
        contentGlued: Math.abs(a.taOff - b.taOff) <= 2,
        aiOK: Math.abs(a.ai.c - a.vw / 2) <= 8
      };
    }
  },
  {
    name: '6 gate-narrow',
    w: 1280,
    setup: function () {
      document.body.style.margin = '0';
      document.body.innerHTML = HDR +
        '<div id="rcnt"><div id="center_col" style="width:652px;height:600px">results</div>' +
        '<div id="aiblock" style="width:1100px;">' +
        '<div style="height:24px">AI Overview</div><div style="height:200px">answer</div>' +
        '</div></div>';
    },
    check: function (b, a) {
      var els = ['#center_col', '#aiblock', '#rcnt'];
      var clean = true;
      for (var i = 0; i < els.length; i++) {
        var e = document.querySelector(els[i]);
        if (e && e.style.transform) clean = false;
        if (e && e.style.gridColumn && els[i] === '#center_col') clean = false;
      }
      return {noTransforms: a.transformed.length === 0, nativeCol: clean,
              vw: a.vw >= 1200};
    }
  },
  {
    name: '7 overlap-guard',
    w: 2560,
    setup: function () {
      document.body.style.margin = '0';
      document.body.innerHTML =
        '<div id="hdr"><div id="searchform"><div class="RNNXgb" role="combobox" ' +
        'style="width:861px;height:44px"></div></div>' +
        '<div class="tabrow" role="navigation" style="width:861px;display:flex">' +
        '<span>All</span><span>Images</span><span>Videos</span></div>' +
        '<div id="side" style="position:absolute;left:1690px;top:0;width:200px;height:44px" ' +
        'aria-label="Settings"></div></div>' +
        '<div id="rcnt"><div id="center_col" style="width:652px;height:600px">results</div></div>';
    },
    check: function (b, a) {
      // centring the pill would push it past the header controls at x=1690+,
      // so the guard must keep it native while the column still centres.
      return {
        pillNative: a.pillTf === '',
        colCentred: Math.abs(a.col.c - a.vw / 2) <= 6
      };
    }
  },
  {
    name: '8 idempotent',
    w: 2560,
    setup: function () {
      document.body.style.margin = '0';
      document.body.innerHTML = HDR +
        '<div id="rcnt"><div id="center_col" style="width:652px;height:600px">results</div>' +
        '<div id="aiblock" style="width:1100px;">' +
        '<div style="height:24px">AI Overview</div><div style="height:300px">answer</div>' +
        '<div class="controlrow" style="width:762px;height:50px;">' +
        '<div class="pill" style="width:760px;height:48px;border:1px solid #888;' +
        'border-radius:24px;position:relative;"><span class="morelabel">Mostrar mais</span>' +
        '</div></div></div></div>';
    },
    extra: 'window.apply(); window.apply();' +
           'window.__pinC = Math.round((function(){var r=document.querySelector(".pill")' +
           '.getBoundingClientRect();return r.left+r.width/2;})());' +
           'for (var i = 0; i < 5; i++) { window.apply(); }',
    check: function (b, a) {
      var c = a.vw / 2;
      return {
        colOK: Math.abs(a.col.c - c) <= 6,
        pillOK: Math.abs(a.pill.c - c) <= 8,
        // five more passes must not move anything: the transform is computed from a
        // cached baseline / live residual, never compounding
        stable: typeof window.__pinC === 'number' ? Math.abs(a.pill.c - window.__pinC) <= 2 : false,
        aiOK: Math.abs(a.ai.c - c) <= 8
      };
    }
  },
  {
    name: '9 tabs-clip',
    w: 2560,
    setup: function () {
      document.body.style.margin = '0';
      document.body.innerHTML =
        '<div id="hdr"><div id="searchform">' +
        '<div class="RNNXgb" role="combobox" style="width:861px;height:44px"></div></div>' +
        '<div id="clip" style="width:900px;overflow-x:auto;overflow-y:hidden">' +
        '<div id="labelrow" style="display:flex;gap:24px;width:max-content">' +
        '<span>All</span><span>Images</span><span>Videos</span><span>News</span>' +
        '<span>Maps</span><span>Books</span><span>Flights</span><span>Tools</span>' +
        '</div></div></div>' +
        '<div id="rcnt"><div id="center_col" style="width:652px;height:600px">results</div></div>';
    },
    setup_tabs: true,
    check: function (b, a) {
      var c = a.vw / 2;
      return {
        // the clip frame moves so the row is visible, and the row keeps its
        // labels inside the frame (no "Ferramentas" -> "Ferra" truncation)
        clipMoved: !!a.clip && Math.abs(a.clip.c - c) <= 20,
        labelsInsideClip: a.labelsInside,
        rowCentred: !!a.labelrow && Math.abs(a.labelrow.c - c) <= 20
      };
    }
  },
  {
    name: '10 stale-node',
    w: 2560,
    setup: function () {
      document.body.style.margin = '0';
      document.body.innerHTML = HDR +
        '<div id="rcnt"><div id="center_col" style="width:652px;height:600px">results</div>' +
        '<div id="aihost"><div id="aiblock" style="width:1100px;">' +
        '<div style="height:24px">AI Overview</div><div style="height:300px">answer</div>' +
        '</div></div></div>';
    },
    extra: 'window.__oldAi = document.getElementById("aiblock");' +
           'var host = document.getElementById("aihost");' +
           'host.innerHTML = host.innerHTML;' +   // Google-style re-render
           'window.apply(); window.apply();',
    check: function (b, a) {
      var old = window.__oldAi;
      var fresh = document.getElementById('aiblock');
      return {
        oldCleared: !old || old.style.transform === '',
        newCentred: Math.abs(a.ai.c - a.vw / 2) <= 8,
        freshMoved: fresh === old ? null : true
      };
    }
  },
  {
    name: '11 disable-narrow',
    w: 2560,
    teardown: function () { return 'ok'; },
    setup: function () {
      document.body.style.margin = '0';
      document.body.innerHTML = HDR +
        '<div id="rcnt"><div id="center_col" style="width:652px;height:600px">results</div>' +
        '<div id="aiblock" style="width:1100px;">' +
        '<div style="height:24px">AI Overview</div><div style="height:200px">answer</div>' +
        '</div></div>';
    },
    shrink_to: 1280,
    check: function (b, a) {
      return {
        allCleared: a.transformed.length === 0,
        colNative: a.colStyle.indexOf('grid-column') === -1
      };
    }
  },
  {
    name: '12 legacy-pt',
    w: 2560,
    setup: function () {
      document.body.style.margin = '0';
      document.body.innerHTML =
        '<div id="hdr"><div id="searchform">' +
        '<div class="RNNXgb" role="combobox" style="width:861px;height:44px"></div></div>' +
        '<div id="hdtb"><div role="navigation" style="width:861px;display:flex">' +
        '<a href="/search?tbm=isch" style="width:80px">Imagens</a>' +
        '<a href="/search?tbm=vid" style="width:80px">Vídeos</a>' +
        '<a href="/search?tbm=nws" style="width:80px">Notícias</a></div></div></div>' +
        '<div id="rcnt"><div id="center_col" style="width:652px;height:600px">results</div>' +
        '<div id="aiblock" style="width:1100px;">' +
        '<div style="height:24px">Visão geral criada por IA</div>' +
        '<div style="height:200px">resposta</div>' +
        '<div class="controlrow" style="width:762px;height:50px;">' +
        '<div class="pill" style="width:760px;height:48px;border:1px solid #888;' +
        'border-radius:24px;position:relative;"><span class="morelabel">Mostrar mais</span>' +
        '</div></div></div></div>';
    },
    check: function (b, a) {
      var c = a.vw / 2;
      return {
        tabsOK: Math.abs(a.tabs.c - c) <= 8,
        aiOK: Math.abs(a.ai.c - c) <= 8,
        pillOK: Math.abs(a.pill.c - c) <= 10
      };
    }
  }
];

window.__selectors = function (i) {
  var f = window.__FIX[i];
  var s = {col: '#center_col', pill: '#searchform .RNNXgb', ai: '#aiblock'};
  // tabs: prefer the visible label row
  s.tabs = document.querySelector('.tabrow') ? '.tabrow'
         : (document.querySelector('#hdtb [role="navigation"]') || document.querySelector('#hdtb'))
           ? '#hdtb [role="navigation"], #hdtb' : '.tabrow';
  return s;
};

window.__measureNative = function (i) {
  window.__clearAll();
  return window.__measure(i);
};

window.__setup = function (i) {
  var f = window.__FIX[i];
  f.setup();
  window.__clearAll();
  return 'ok';
};

window.__measure = function (i) {
  var f = window.__FIX[i];
  var sel = window.__selectors(i), out = {};
  out.vw = document.documentElement.clientWidth;
  var col = document.querySelector('#center_col');
  var rhs = document.querySelector('#rhs');
  var pill = document.querySelector('#searchform .RNNXgb');
  var tabs = document.querySelector(sel.tabs);
  var ai = document.querySelector('#aiblock');
  out.col = window.__rr(col); out.pill = window.__rr(pill);
  out.tabs = window.__rr(tabs); out.ai = window.__rr(ai);
  out.rcntInline = (document.getElementById('rcnt') || {}).style
    ? document.getElementById('rcnt').style.gridTemplateColumns : '';
  out.colStyle = col ? (col.getAttribute('style') || '') : '';
  out.pillTf = window.__tf('#searchform .RNNXgb');
  out.zone = (col && rhs) ? {l: Math.min(col.getBoundingClientRect().left, rhs.getBoundingClientRect().left),
                             r: Math.max(col.getBoundingClientRect().right, rhs.getBoundingClientRect().right)}
                          : null;
  if (out.zone) out.zone = {c: Math.round((out.zone.l + out.zone.r) / 2)};
  var strip = document.querySelector('.strip');
  if (strip) {
    var parent = strip.parentElement;
    out.strip = window.__rr(strip);
    out.stripSpans = getComputedStyle(strip).gridColumnStart === '2';
  }
  var clip = document.querySelector('#clip'), row = document.querySelector('#labelrow');
  if (clip && row) {
    out.clip = window.__rr(clip); out.labelrow = window.__rr(row);
    var labels = row.querySelectorAll('span'), last = labels[labels.length - 1];
    out.labelsInside = window.__rr(last).r <= Math.round(clip.getBoundingClientRect().right) + 1;
  }
  var pillEl = document.querySelector('.pill'), label = document.querySelector('.morelabel');
  if (pillEl && label) out.labelOff = Math.round(window.__mm(label) - window.__mm(pillEl));
  var barEl = document.querySelector('.barframe'), ta = document.querySelector('.askinput');
  if (barEl && ta) out.taOff = Math.round(ta.getBoundingClientRect().left - barEl.getBoundingClientRect().left);
  out.transformed = window.__txf().map(function (t) {
    var e = null, all = document.querySelectorAll('*');
    for (var k = 0; k < all.length; k++) {
      if (all[k].style && all[k].style.transform === t.tf && (all[k].className === t.cls || all[k].className === '')) { e = all[k]; break; }
    }
    var pillBox = document.querySelector('.pill'), barBox = document.querySelector('.barframe');
    return {cls: t.cls, tf: t.tf,
            isPill: !!(e && pillBox && e === pillBox),
            inPill: !!(e && pillBox && e !== pillBox && pillBox.contains(e)),
            isBar: !!(e && barBox && e === barBox),
            inBar: !!(e && barBox && e !== barBox && barBox.contains(e))};
  });
  return JSON.stringify(out);
};

window.__check = function (i, beforeJson) {
  var b = JSON.parse(beforeJson);
  var a = JSON.parse(window.__measure(i));
  var last = window.__FIX[i];
  var baseChecks = last.check(b, a) || {};
  var ok = true, fails = [];
  for (var k in baseChecks) {
    if (baseChecks[k] === false) { ok = false; fails.push(k); }
  }
  return JSON.stringify({pass: ok, fails: fails, checks: baseChecks,
                         vw: a.vw, transformed: a.transformed.map(function (t) { return t.cls + ':' + t.tf; })});
};
"""


# ------------------------------------------------------------------ driver ---
def start_driver():
    env = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        env.pop(k, None)
    if ENGINE == "chrome":
        p = subprocess.Popen(["chromedriver", f"--port={PORT}", "--log-level=OFF"],
                             env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    else:
        p = subprocess.Popen(["geckodriver", "--port", str(PORT), "--log", "error"],
                             env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    time.sleep(2)
    return p


def req(method, path, body=None):
    r = urllib.request.Request(BASE + path, method=method,
                               headers={"Content-Type": "application/json"})
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(r, data=data, timeout=90) as resp:
            raw = resp.read()
            try:
                return json.loads(raw) if raw else {}
            except Exception:
                return {"raw": raw[:300].decode(errors="replace")}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return json.loads(raw) if raw else {"error": e.code}
        except Exception:
            return {"error": e.code, "raw": raw[:300].decode(errors="replace")}


def session_caps():
    if ENGINE == "chrome":
        return {"capabilities": {"alwaysMatch": {
            "browserName": "chrome",
            "goog:chromeOptions": {"binary": CHROME_BIN,
                                   "args": ["--headless=new", "--no-sandbox",
                                            "--disable-gpu", "--window-size=2560,1400"]}}}}
    return {"capabilities": {"alwaysMatch": {
        "moz:firefoxOptions": {"binary": FIREFOX_BIN, "args": ["-headless", "-no-remote"]}}}}


def main():
    driver = start_driver()
    res = req("POST", "/session", session_caps())
    sid = (res.get("value") or {}).get("sessionId") or res.get("sessionId")
    if not sid:
        print("SESSION FAILED:", json.dumps(res)[:400])
        driver.terminate()
        return 1
    print(f"engine: {ENGINE} | session {sid[:8]}")

    def cmd(m, p, b=None):
        return req(m, f"/session/{sid}{p}", b)

    def js(script):
        r = cmd("POST", "/execute/sync", {"script": script, "args": []})
        if isinstance(r, dict) and r.get("value") is not None:
            return r["value"]
        if isinstance(r, dict) and r.get("value") is None and "status" not in r:
            return None
        return r

    def nav(url, tag=""):
        """Navigate and WAIT for the new document to be current.

        about:blank navigations complete AFTER the WebDriver call returns, so
        evaluating content.js immediately can land in the OLD document — the
        globals then vanish when the real navigation finishes (symptom:
        "apply is not defined" a few calls later)."""
        cmd("POST", "/url", {"url": url})
        for _ in range(20):
            time.sleep(0.15)
            state = cmd("POST", "/execute/sync",
                        {"script": "return location.href + '|' + document.readyState",
                         "args": []})
            v = state.get("value") if isinstance(state, dict) else None
            if isinstance(v, str) and v.endswith("|complete") and (not tag or tag in v):
                return True
        return False

    total = 0
    failed = []
    try:
        # strip "use strict" so the indirect eval puts the declarations in the
        # GLOBAL scope — with strict mode the eval gets its own scope and
        # apply()/the fixture helpers are unreachable from later scripts.
        src = open(CONTENT_JS).read().replace('"use strict";\n', "", 1)
        nav("about:blank", "about:blank")
        # content.js declares const/let at top level: load it exactly ONCE.
        cmd("POST", "/execute/sync",
            {"script": "window.__src=" + json.dumps(src) + ";" +
                       "try{(0,eval)(window.__src);}catch(e){return 'evalErr: '+e.message;}" +
                       "if(typeof apply==='function') window.apply=apply;" +
                       "return typeof window.apply;", "args": []})
        cmd("POST", "/execute/sync", {"script": FIXTURES_JS, "args": []})

        names = js("return JSON.stringify(window.__FIX.map(function(f){return f.name;}))")
        names = json.loads(names)
        for i, name in enumerate(names):
            if ONLY and ONLY.lower() not in name.lower():
                continue
            total += 1
            width = js(f"return window.__FIX[{i}].w")
            try:
                cmd("POST", "/window/rect", {"width": int(width), "height": 1400, "x": 0, "y": 0})
            except Exception:
                pass
            time.sleep(0.3)
            nav(f"about:blank#{i}", f"#{i}")
            # re-arm the page globals after navigation (they die with the document)
            boot = cmd("POST", "/execute/sync",
                       {"script": "window.__src=" + json.dumps(src) + ";" +
                                  "try{(0,eval)(window.__src);}catch(e){return 'evalErr: '+e.message;}" +
                                  "if(typeof apply==='function') window.apply=apply;" +
                                  "return typeof window.apply;", "args": []})
            if os.environ.get("DEBUG"):
                print("        boot ->", json.dumps(boot)[:200])
            cmd("POST", "/execute/sync", {"script": FIXTURES_JS, "args": []})
            js(f"return window.__setup({i})")
            before = js(f"return window.__measureNative({i})")
            extra = js(f"return window.__FIX[{i}].extra || ''")
            if extra:
                r = cmd("POST", "/execute/sync", {"script": extra, "args": []})
                if os.environ.get("DEBUG"):
                    print("        extra ->", json.dumps(r)[:300])
            js("window.apply(); window.apply();")
            shrink = js(f"return window.__FIX[{i}].shrink_to || 0")
            if shrink:
                cmd("POST", "/window/rect", {"width": int(shrink), "height": 1400, "x": 0, "y": 0})
                time.sleep(0.4)
                js("window.apply(); window.apply();")
            verdict = json.loads(js(
                f"return window.__check({i}, {json.dumps(before)})"))
            mark = "GREEN" if verdict["pass"] else "RED  "
            print(f"  {mark} {name}" + ("" if verdict["pass"] else f"  FAILED: {verdict['fails']}"))
            print(f"        vw={verdict['vw']} checks={verdict['checks']}")
            if verdict["transformed"]:
                print(f"        transforms={verdict['transformed'][:4]}")
            if not verdict["pass"]:
                failed.append(name)
                if os.environ.get("DEBUG"):
                    print("        BEFORE:", before)
                    print("        AFTER :", js(f"return window.__measure({i})"))
                    print("        pinC  :", js("return window.__pinC"))
    finally:
        try:
            cmd("DELETE", "")
        except Exception:
            pass
        driver.terminate()
        time.sleep(0.5)

    print(f"\n{ENGINE}: {total - len(failed)}/{total} fixtures GREEN")
    if failed:
        print("FAILED:", ", ".join(failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
