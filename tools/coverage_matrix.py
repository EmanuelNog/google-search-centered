#!/usr/bin/env python3
"""Coverage matrix: load each Google result surface with the real add-on
installed and report whether the centering actually applies.

Uses the manual-Firefox + raw-marionette recipe (geckodriver is bot-walled).
One fresh profile copy per variant, one navigation each — Google starts
challenging a profile after a load or two.

Usage: coverage_matrix.py [variant ...]
"""
import json, os, shutil, socket, subprocess, sys, time

SKILL_SCRIPTS = "/home/agentuser/.hermes/skills/web/blocked-page-recovery/scripts"
sys.path.insert(0, SKILL_SCRIPTS)
from firefox_marionette import Marionette  # noqa: E402

PROJ = "/home/agentuser/Projects/firefox-google-center"
XPI = os.path.join(PROJ, "web-ext-artifacts/google_search_centered-1.0.4.zip")
DEMO = "/home/agentuser/fx-profiles/demo"
BASE_PORT = 2841

VARIANTS = {
    "all":        "https://www.google.com/search?q=banana&hl=en",
    "images":     "https://www.google.com/search?q=banana&tbm=isch&hl=en",
    "shopping":   "https://www.google.com/search?q=headphones&tbm=shop&hl=en",
    "news":       "https://www.google.com/search?q=banana&tbm=nws&hl=en",
    "videos":     "https://www.google.com/search?q=banana&tbm=vid&hl=en",
    "localmap":   "https://www.google.com/search?q=restaurants+near+me&hl=en",
    "finance":    "https://www.google.com/search?q=bitcoin+price&hl=en",
    "aimode":     "https://www.google.com/search?q=banana&udm=50&hl=en",
    "web":        "https://www.google.com/search?q=banana&udm=14&hl=en",
    "ai":         "https://www.google.com/search?q=how+to+make+coffee&hl=en",
    "flights":    "https://www.google.com/search?q=flights+to+lisbon&hl=en",
    "sports":     "https://www.google.com/search?q=lakers+score&hl=en",
    "weather":    "https://www.google.com/search?q=weather+lisbon&hl=en",
}

MEASURE = r"""
window.__cov = function () {
  function rr(e){ if(!e) return null; var r=e.getBoundingClientRect();
    return {l:Math.round(r.left), r:Math.round(r.right), w:Math.round(r.width),
            t:Math.round(r.top), h:Math.round(r.height), c:Math.round(r.left+r.width/2)}; }
  function desc(e){ return e ? (e.tagName + (e.id?('#'+e.id):'') +
    (typeof e.className==='string' && e.className ? ('.'+e.className.trim().split(/\s+/)[0]) : '')) : null; }
  var vw = document.documentElement.clientWidth;
  var pill = document.querySelector('#searchform .A8SBwf, #searchform div[role="combobox"], #searchform .RNNXgb');
  var col = document.getElementById('center_col');
  var rhs = document.getElementById('rhs');
  var rcnt = document.getElementById('rcnt');
  var main = document.getElementById('main');
  var out = {vw: vw, center: Math.round(vw/2), url: location.href.slice(0,110),
             title: document.title.slice(0,50),
             sorry: /\/sorry\//.test(location.href),
             hasRecaptchaIframe: !!document.querySelector('iframe[src*="/sorry/"]'),
             pill: rr(pill), col: rr(col), colDesc: desc(col), rhs: rr(rhs), rcnt: rr(rcnt),
             main: rr(main),
             rcntInline: rcnt ? (rcnt.getAttribute('style')||'') : null,
             colInline: col ? (col.getAttribute('style')||'') : null,
             pillTf: pill ? getComputedStyle(pill).transform : null,
             gridRcnt: rcnt ? getComputedStyle(rcnt).display : null};
  // tab row
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
  if (row.length>=2){ var minL=Infinity,maxR=-Infinity;
    for (var m=0;m<row.length;m++){ var r2=row[m].getBoundingClientRect();
      minL=Math.min(minL,r2.left); maxR=Math.max(maxR,r2.right); }
    out.tabs={l:Math.round(minL), r:Math.round(maxR), w:Math.round(maxR-minL),
              c:Math.round((minL+maxR)/2), off:Math.round((minL+maxR)/2 - vw/2)};
  } else out.tabs=null;
  if (out.pill) out.pill.off = out.pill.c - out.center;
  if (out.col) out.col.off = out.col.c - out.center;
  // biggest visible blocks anywhere in #main (to judge unknown layouts)
  var blocks=[];
  var scope = main || document.body;
  var els = scope.querySelectorAll('div,section,g-table');
  for (var n=0;n<els.length && n<4000;n++){
    var e2=els[n]; var r3=e2.getBoundingClientRect();
    // ignore horizontal scrollers/carousels (wider than the viewport) — they
    // are not centering targets and would skew the content box
    if (r3.width>400 && r3.height>120 && r3.top<2600 && r3.right <= vw+2 && r3.left >= -2){
      blocks.push({d:desc(e2), l:Math.round(r3.left), r:Math.round(r3.right),
                   w:Math.round(r3.width), h:Math.round(r3.height), t:Math.round(r3.top)});
    }
  }
  blocks.sort(function(a,b){ return (b.w*b.h)-(a.w*a.h); });
  // dedupe nested look-alikes (same rect)
  var seen={}, keep=[];
  for (var p=0;p<blocks.length;p++){ var key=blocks[p].l+':'+blocks[p].r+':'+blocks[p].w+':'+blocks[p].t;
    if (seen[key]) continue; seen[key]=1; keep.push(blocks[p]); if (keep.length>=8) break; }
  out.blocks = keep;
  // overall content box of those blocks => is the page content centered?
  if (keep.length){ var l2=Math.min.apply(null,keep.map(function(b){return b.l;}));
    var r4=Math.max.apply(null,keep.map(function(b){return b.r;}));
    out.contentBox={l:l2, r:r4, w:r4-l2, c:Math.round((l2+r4)/2),
                    off:Math.round((l2+r4)/2 - vw/2)}; }
  return JSON.stringify(out);
}
"""


def run_variant(name, url, idx):
    port = BASE_PORT + idx
    prof = f"/home/agentuser/fx-profiles/cov_{name}"
    shutil.rmtree(prof, ignore_errors=True)
    shutil.copytree(DEMO, prof, symlinks=True)
    for junk in ("lock", ".parentlock"):
        p = os.path.join(prof, junk)
        if os.path.exists(p):
            os.remove(p)
    with open(os.path.join(prof, "user.js"), "w") as fh:
        fh.write('user_pref("dom.webdriver.enabled", false);\n'
                 'user_pref("marionette.enabled", true);\n'
                 f'user_pref("marionette.port", {port});\n'
                 'user_pref("datareporting.policy.dataSubmissionEnabled", false);\n'
                 'user_pref("toolkit.telemetry.enabled", false);\n')
    env = {k: v for k, v in os.environ.items()
           if k.lower() not in ("http_proxy", "https_proxy", "all_proxy")}
    env["DISPLAY"] = ":99"
    env["MOZ_ENABLE_WAYLAND"] = "0"
    proc = subprocess.Popen(
        ["firefox", "--no-remote", "--new-instance", "-marionette", "-profile", prof, url],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)
    res = {"variant": name, "url": url}
    try:
        # wait for marionette
        deadline = time.time() + 45
        m = None
        while time.time() < deadline:
            try:
                m = Marionette(port=port, timeout=10)
                break
            except Exception:
                time.sleep(1.5)
        if m is None:
            res["error"] = "marionette port never opened"
        else:
            m.new_session()
            try:
                m.install_addon(XPI)
                res["addon"] = "installed"
            except Exception as exc:
                res["addon_error"] = str(exc)[:120]
                m.navigate(url)
            time.sleep(14)
            # The window opens at ~1330px (below MIN_WIDTH) — resize AFTER the
            # page loads; a resize issued before navigation does not stick.
            try:
                m.resize(2327, 1400)
                time.sleep(3)
            except Exception as exc:
                res["resize_error"] = str(exc)[:120]
            try:
                m.execute(MEASURE)
                val = m.execute("return window.__cov();").get("value")
                data = val
                for _ in range(3):
                    if isinstance(data, str):
                        try:
                            data = json.loads(data)
                        except Exception:
                            break
                    else:
                        break
                if isinstance(data, dict):
                    res.update(data)
                else:
                    res["raw"] = str(val)[:200]
            except Exception as exc:
                res["measure_error"] = str(exc)[:160]
            m.close()
    except Exception as exc:
        res["error"] = str(exc)[:200]
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        time.sleep(2)
    return res


def main():
    want = sys.argv[1:] or list(VARIANTS)
    results = []
    for i, name in enumerate(want):
        if name not in VARIANTS:
            print(f"unknown variant {name}"); continue
        r = run_variant(name, VARIANTS[name], i)
        results.append(r)
        summ = {k: r.get(k) for k in ("variant", "sorry", "title", "colDesc", "gridRcnt")}
        pill = r.get("pill") or {}
        tabs = r.get("tabs") or {}
        col = r.get("col") or {}
        cb = r.get("contentBox") or {}
        print(json.dumps({
            "variant": r.get("variant"),
            "page": r.get("title"),
            "sorry": r.get("sorry"),
            "recaptcha_iframe": r.get("hasRecaptchaIframe"),
            "col": r.get("colDesc"),
            "col_off": col.get("off"),
            "col_width": col.get("w"),
            "pill_off": pill.get("off"),
            "tabs_off": tabs.get("off"),
            "content_off": cb.get("off"),
            "addon_applied": bool(r.get("rcntInline") or r.get("colInline") or
                                  (r.get("pillTf") not in (None, "none"))),
            "blocks": [(b.get("d"), b.get("w")) for b in (r.get("blocks") or [])][:5],
        }, ensure_ascii=False))
        with open("/tmp/coverage_matrix.json", "w") as fh:
            json.dump(results, fh, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()