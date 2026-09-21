"use strict";

/*
 * Google Search Centered
 *
 * Google lays its results column (#center_col), the search-bar row and the
 * filter-tabs row into the LEFT zone of full-width CSS grids / containers
 * even when no knowledge panel is shown on the right — so on very wide
 * screens all content hugs the left edge of the viewport.
 *
 * This script centers three elements on the viewport center:
 *   1. the results column (#center_col) — spans the full grid row
 *      (grid-column: 1 / -1) plus auto margins,
 *   2. the search bar (pill), and
 *   3. the filter tabs row (the All/Images/Videos/... strip).
 *
 * Items 2 and 3 are shifted with transform: translateX(delta), where delta
 * is computed live from each element's untransformed baseline — nothing is
 * hardcoded, so every width between and beyond the tested sizes stays
 * correct. A right-side overlap guard disables shifting when the centered
 * item would collide with the header controls (Settings / Apps / Sign in) —
 * at those widths the native layout stays.
 *
 * All of it applies ONLY when:
 *   - the viewport is at least MIN_WIDTH wide, and
 *   - no knowledge panel (#rhs) is visible (centering would overlap it).
 *
 * Inline styles are used (CSP-proof, wins over Google's stylesheets).
 * Runs from document_start so centering is in place before first paint
 * completes; a mutation observer re-applies it if Google re-renders or if a
 * knowledge panel appears/disappears.
 */

const MIN_WIDTH = 1440; // px — only center on screens this wide or larger
const PILL_SELECTOR =
  '#searchform .A8SBwf, #searchform div[role="combobox"], #searchform .RNNXgb';

const TAB_LABELS = [
  "Modo IA", "AI Mode", "Tudo", "All", "Imagens", "Images", "Vídeos", "Videos",
  "Shopping", "Notícias", "News", "Maps", "Livros", "Books", "Web", "Fórum",
  "Forums", "Vídeos curtos", "Short videos", "Mais", "More", "Ferramentas",
  "Tools",
];

// Build the visible tab-label row: one element per distinct label (outermost
// duplicate), clustered to the densest horizontal band.
function getTabRow() {
  const seen = new Map(); // text -> widest element carrying it
  const all = document.querySelectorAll("a, span, div, button");
  for (let i = 0; i < all.length; i++) {
    const e = all[i];
    if (e.children.length > 2) continue;
    const t = (e.textContent || "").trim();
    if (t.length <= 16 && TAB_LABELS.indexOf(t) !== -1) {
      const r = e.getBoundingClientRect();
      if (r.width > 5 && r.height > 5 && r.top < 300) {
        const prev = seen.get(t);
        if (!prev || r.width * r.height > prev.area) {
          seen.set(t, { el: e, area: r.width * r.height });
        }
      }
    }
  }
  const labels = [];
  for (const v of seen.values()) labels.push(v.el);
  if (labels.length < 2) return null;
  const buckets = new Map();
  for (const l of labels) {
    const t = Math.round(l.getBoundingClientRect().top / 20) * 20;
    if (!buckets.has(t)) buckets.set(t, []);
    buckets.get(t).push(l);
  }
  let row = [];
  for (const arr of buckets.values()) if (arr.length > row.length) row = arr;
  if (row.length < 2) return null;
  let minL = Infinity;
  let maxR = -Infinity;
  for (const l of row) {
    const r = l.getBoundingClientRect();
    minL = Math.min(minL, r.left);
    maxR = Math.max(maxR, r.right);
  }
  return { row, bboxW: maxR - minL };
}

// Shared walk over the tab-row ancestors. Never crosses into the search pill.
// accept(el, cnt, w, tab) decides whether the current ancestor is a keeper.
function walkTabs(accept) {
  const tab = getTabRow();
  if (!tab) return null;
  const pillEl = document.querySelector(PILL_SELECTOR);
  let el = tab.row[0];
  let best = null;
  for (let i = 0; i < 9 && el && el !== document.body; i++, el = el.parentElement) {
    if (pillEl && el.contains(pillEl)) break; // never move the pill's subtree
    let cnt = 0;
    for (const l of tab.row) if (el.contains(l)) cnt++;
    const w = el.getBoundingClientRect().width;
    if (accept(el, cnt, w, tab)) best = el;
  }
  return best;
}

// Inner target: the visible label row itself — widest ancestor still within
// +10% of the label group's own width.
function getTabsRow() {
  const found = walkTabs((el, cnt, w, tab) => {
    return (
      cnt === tab.row.length && w > 100 && w <= tab.bboxW * 1.1 + 4
    );
  });
  if (found) return found;
  return legacyTabsRow();
}

// Outer target: the first ancestor slightly wider than the label group — the
// frame that carries the scroll clip + right-edge fade. It must move with the
// row, or the shifted row gets clipped ("Ferramentas" -> "Ferra").
function getTabsOuter(fallbackInner) {
  const found = walkTabs((el, cnt, w, tab) => {
    return (
      cnt >= 2 &&
      w > tab.bboxW * 1.1 + 4 &&
      w <= document.documentElement.clientWidth * 0.9
    );
  });
  if (found) return found;
  return null;
}

// Legacy layouts: [role=navigation] wrapper, then tbm=/udm= links.
function legacyTabsRow() {
  const vw = document.documentElement.clientWidth;
  const fit = (el) => {
    if (!el) return false;
    const w = el.getBoundingClientRect().width;
    return w > 300 && w < vw * 0.9;
  };
  const direct = document.querySelector('#hdtb [role="navigation"], #hdtb-msb');
  if (fit(direct)) return direct;
  const links = document.querySelectorAll('#hdtb a[href*="tbm="], #hdtb a[href*="udm="]');
  if (links.length >= 2) {
    let el = links[0];
    let best = null;
    for (let i = 0; i < 6 && el && el !== document.body; i++, el = el.parentElement) {
      let cnt = 0;
      for (const l of links) if (el.contains(l)) cnt++;
      if (cnt >= 2 && fit(el)) best = el;
    }
    if (best) return best;
  }
  return null;
}

let colWidth = null; // captured from the live element on first apply
let lastPillEl = null; // last transformed pill / tab targets — stale
let lastTabsOuter = null; // transforms on replaced nodes are cleared
let lastTabsInner = null; // on re-target

function rhsVisible() {
  const rhs = document.getElementById("rhs");
  if (!rhs) return false;
  const cs = getComputedStyle(rhs);
  return (
    cs.display !== "none" &&
    cs.visibility !== "hidden" &&
    rhs.getBoundingClientRect().width > 0
  );
}

// Left edge of the header's right-side controls (Settings/Apps/Sign in).
// Used by the overlap guard: a centered item must not reach these.
function rightControlsLeft() {
  const labels = ["Settings", "Google apps", "Sign in"];
  let min = Infinity;
  for (const label of labels) {
    const el = document.querySelector('[aria-label="' + label + '"]');
    if (el) min = Math.min(min, el.getBoundingClientRect().left);
  }
  // Fallback: the known right-side container of the header row.
  if (!isFinite(min)) {
    const side =
      document.querySelector("#searchform .Q3DXx, #searchform .uZkjhb") ||
      document.querySelector("#searchform > div > div:last-child");
    if (side) min = side.getBoundingClientRect().left;
  }
  return isFinite(min) ? min : Infinity;
}

// Center an in-flow element on the viewport center via translateX(delta),
// computed from its cached UNTRANSFORMED baseline (per window width).
// Measuring the live rect would include our own previous transform and
// oscillate. Returns true when centered/cleared, false when not laid out.
function centerItem(el, key) {
  let base = null;
  try {
    base = JSON.parse(el.dataset[key] || "null");
  } catch (e) {
    base = null;
  }
  if (!base || Math.abs(base.iw - window.innerWidth) > 2) {
    el.style.transform = "";
    void el.getBoundingClientRect(); // force layout without transform
    const r0 = el.getBoundingClientRect();
    if (r0.width > 100) {
      base = { iw: window.innerWidth, left: r0.left, width: r0.width };
      el.dataset[key] = JSON.stringify(base);
    } else {
      // Layout not ready (Google re-renders these nodes on resize).
      setTimeout(scheduleApply, 150);
      return false;
    }
  }
  // Overlap guard: only center if the item fits left of the header controls.
  const vw = document.documentElement.clientWidth;
  const centeredRight = base.left + (vw / 2 - (base.left + base.width / 2)) + base.width;
  const guard = rightControlsLeft();
  if (centeredRight > guard - 16) {
    el.style.transform = "";
    return true; // keep native at this width; no centering
  }
  const delta = Math.round(vw / 2 - (base.left + base.width / 2));
  if (Math.abs(delta) > 1) {
    el.style.transform = "translateX(" + delta + "px)";
  } else {
    el.style.transform = "";
  }
  return true;
}

// Iterative residual centering for the inner tab row: it sits inside the
// outer frame, so a one-shot cached baseline would fight the outer transform.
// Adjusting by the measured residual each pass converges in a frame or two
// and is idempotent once centered (residual ~ 0 -> no write -> no loop).
function centerInner(el) {
  const r = el.getBoundingClientRect();
  if (r.width < 100) return;
  const residual = Math.round(
    document.documentElement.clientWidth / 2 - (r.left + r.width / 2)
  );
  let base = 0;
  const m = (el.style.transform || "").match(/translateX\((-?[\d.]+)px\)/);
  if (m) base = parseFloat(m[1]);
  if (Math.abs(residual) >= 2) {
    el.style.transform = "translateX(" + (base + residual) + "px)";
  } else if (base === 0 && el.style.transform) {
    el.style.transform = "";
  }
}

function apply() {
  const active = window.innerWidth >= MIN_WIDTH && !rhsVisible();

  // --- results column ---
  const col = document.getElementById("center_col");
  if (col) {
    if (active) {
      // Width must be measured after layout exists (document_start can see 0).
      if (colWidth === null) {
        const w = col.getBoundingClientRect().width;
        if (w > 100) colWidth = w;
        else return; // not laid out yet; the observer will call us again
      }
      col.style.gridColumn = "1 / -1";
      col.style.width = colWidth + "px";
      col.style.marginLeft = "auto";
      col.style.marginRight = "auto";
    } else {
      col.style.gridColumn = "";
      col.style.width = "";
      col.style.marginLeft = "";
      col.style.marginRight = "";
      colWidth = null;
    }
  }

  // --- search bar pill ---
  const pill = document.querySelector(PILL_SELECTOR);
  if (pill !== lastPillEl && lastPillEl) {
    lastPillEl.style.transform = "";
    delete lastPillEl.dataset.gsrBase;
  }
  if (pill) {
    lastPillEl = pill;
    if (active) {
      centerItem(pill, "gsrBase");
    } else {
      pill.style.transform = "";
      delete pill.dataset.gsrBase;
    }
  } else {
    lastPillEl = null;
  }

  // --- filter tabs row (outer frame + inner label row) ---
  const tabsOuter = getTabsOuter();
  const tabsInner = getTabsRow();
  if (tabsOuter !== lastTabsOuter && lastTabsOuter) {
    lastTabsOuter.style.transform = "";
    delete lastTabsOuter.dataset.gsrTabsOuter;
  }
  if (tabsInner !== lastTabsInner && lastTabsInner) {
    lastTabsInner.style.transform = "";
    delete lastTabsInner.dataset.gsrTabsInner;
  }
  if (active) {
    if (tabsOuter) {
      lastTabsOuter = tabsOuter;
      centerItem(tabsOuter, "gsrTabsOuter");
    } else {
      lastTabsOuter = null;
    }
    if (tabsInner && tabsInner !== tabsOuter) {
      lastTabsInner = tabsInner;
      centerInner(tabsInner);
    } else {
      lastTabsInner = null;
    }
  } else {
    if (tabsOuter) {
      tabsOuter.style.transform = "";
      delete tabsOuter.dataset.gsrTabsOuter;
    }
    if (tabsInner) {
      tabsInner.style.transform = "";
      delete tabsInner.dataset.gsrTabsInner;
    }
    lastTabsOuter = null;
    lastTabsInner = null;
  }

  if (active) {
    scheduleVerify();
  } else {
    clearTimeout(verifyTimer);
  }
}

// Frame-throttled: Google mutates the results tree a lot during render.
let scheduled = false;
function scheduleApply() {
  if (scheduled) return;
  scheduled = true;
  requestAnimationFrame(() => {
    scheduled = false;
    apply();
  });
}

// Verify-and-retry: Google re-renders header nodes during resize and can
// clear our inline styles after the last mutation pass — so keep re-applying
// until the centering sticks. verifyCount bounds the total retries and is
// reset only on user-driven viewport changes (see listeners below).
let verifyTimer = null;
let verifyCount = 0;
function verifyStable() {
  const targets = [
    document.querySelector(PILL_SELECTOR),
    getTabsRow(),
    document.getElementById("center_col"),
  ];
  let off = 0;
  const vw = document.documentElement.clientWidth;
  for (const el of targets) {
    if (!el) continue;
    const r = el.getBoundingClientRect();
    off += Math.abs(Math.round(vw / 2 - (r.left + r.width / 2)));
  }
  if (off > 6 && verifyCount < 6) {
    verifyCount++;
    scheduleApply();
    verifyTimer = setTimeout(verifyStable, 350);
  }
}
function scheduleVerify() {
  clearTimeout(verifyTimer);
  verifyTimer = setTimeout(verifyStable, 350);
}

apply();
function onViewportChange() {
  verifyCount = 0;
  scheduleApply();
}
window.addEventListener("resize", onViewportChange);
window.addEventListener("orientationchange", onViewportChange);
document.addEventListener("DOMContentLoaded", apply);
window.addEventListener("load", apply);

new MutationObserver(scheduleApply).observe(document.documentElement, {
  childList: true,
  subtree: true,
  attributes: true,
  attributeFilter: ["style"],
});