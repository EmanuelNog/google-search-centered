# Google Search Centered (Firefox)

Centers Google's search UI on wide screens.

On big monitors Google pins the search results column, the search box and the
filter-tabs row (AI Mode / All / Images / ...) to the LEFT zone of its CSS
grids, even when the right side of the page is empty. This add-on centers
three elements on the viewport center:

1. the **results column** (`#center_col`) — spans the full grid row
   (`grid-column: 1 / -1`) and centers with auto margins;
2. the **search bar pill**;
3. the **filter tabs row** (All / Images / Videos / ...).

Items 2 and 3 are shifted with `transform: translateX(delta)` where delta is
derived at runtime from each element's untransformed baseline — nothing is
hardcoded, so any viewport width between (or beyond) the tested sizes stays
correct. A live overlap guard drops the shifting when a centered item would
collide with the header controls (Settings / Apps / Sign in); at those widths
the native layout is kept.

It only kicks in when:

- the window is at least **1440px** wide (one knob, `MIN_WIDTH` in
  `content.js`), and
- no **knowledge panel** (`#rhs`) is visible — when Google shows one, the
  add-on leaves the original layout untouched.

Works on `google.com` and regional Google domains (see the matches list in
`manifest.json`; add your country TLD there if it is missing).

## Install (temporary, for development / personal use)

1. Open Firefox and go to `about:debugging#/runtime/this-firefox`
2. Click **Load Temporary Add-on…**
3. Select `manifest.json` from this folder

The add-on stays active until Firefox is closed.

## Install (permanent — signed release)

Every release ships a Mozilla-signed `.xpi` that installs permanently in any
Firefox (release channel):

1. Download `google-search-centered-1.0.1.xpi` from the
   [latest release](https://github.com/EmanuelNog/google-search-centered/releases/latest)
2. In Firefox: `about:addons` → gear icon → **Install Add-on From File…** →
   pick the file (or just drag the file into the Firefox window)

To sign your own builds instead:

```bash
npx web-ext sign --source-dir . --api-key=<JWT issuer> --api-secret=<secret> --channel unlisted
```

(AMO developer credentials: https://addons.mozilla.org/developers/addon/api/key/)

## Verified behavior (Firefox 151, Sep 2026 — measured live in the browser)

| Window | client width | column | pill | tabs |
|--------|-------------|--------|------|------|
| 2560x1440 (full)  | 2548 | centered | centered | centered |
| 1920x1080 (full)  | 1908 | centered | centered | centered |
| 1600             | 1588 | centered | centered | centered |
| 1440x900         | 1428 | centered | centered | centered |
| 1280 (2560 half) | 1268 | native | native | native |
| 960 (1920 half)  | 948  | native | native | native |
| any width + knowledge panel | — | native | native | native |

All centered states land within ±1px of `clientWidth / 2`, with zero
horizontal overflow, and re-center correctly when the window is resized in
either direction (including across the 1440px threshold). Larger monitors
(4K etc.) use the same live math and need no changes.

## Customization

- `MIN_WIDTH` in `content.js` — threshold (px) above which centering applies.
- Results column width and all offsets are captured from the live page.

## Notes

- Google renders the tabs strip differently per locale/layout (en-US uses a
  `role="navigation"` wrapper; pt-BR 2026 renders div-based tabs in a
  different container). The add-on locates the strip by tab-label text and
  centers the label row plus its clip/fade frame, so both variants work.
- `tools/` contains Marionette probe scripts that can inspect and measure a
  live Firefox window (used to verify against the real browser).

## Screenshots

- `screenshots/before.png` — native 2560px layout (column at 9% of the width)
- `screenshots/after.png` — with the add-on: pill, tabs and results centered