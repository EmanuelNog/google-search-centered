#!/usr/bin/env python3
"""Verify: measure the VISIBLE tab-label row center in the live window. Usage: script PORT"""
import socket, json, base64, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 40137

def recv_msg(sock):
    buf = b""
    while b":" not in buf:
        c = sock.recv(1)
        if not c:
            raise ConnectionError("closed")
        buf += c
    n = int(buf.split(b":")[0])
    data = b""
    while len(data) < n:
        data += sock.recv(n - len(data))
    return json.loads(data.decode())

def send_msg(sock, msg):
    data = json.dumps(msg).encode()
    sock.sendall(str(len(data)).encode() + b":" + data)

def cmd(sock, mid, name, params):
    send_msg(sock, [0, mid, name, params])
    ans = recv_msg(sock)
    if ans[2]:
        raise RuntimeError(f"{name}: {json.dumps(ans[2])[:300]}")
    return ans[3]

s = socket.create_connection(("127.0.0.1", PORT), timeout=20)
recv_msg(s)
try:
    cmd(s, 1, "WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
except RuntimeError as e:
    print("session:", e)

DEFINE = r"""window.__verify2 = function () {
  var vw = document.documentElement.clientWidth;
  var out = {clientW: vw, center: Math.round(vw / 2)};
  function rr(e) { if (!e) return null; var r = e.getBoundingClientRect();
    return {l: Math.round(r.left), r: Math.round(r.right), w: Math.round(r.width)}; }
  var pill = document.querySelector('#searchform .A8SBwf, #searchform div[role="combobox"], #searchform .RNNXgb');
  out.pill = rr(pill); out.pillTf = pill ? getComputedStyle(pill).transform : null;
  var cc = document.getElementById('center_col');
  out.col = rr(cc);
  var LABELS = ["Modo IA","AI Mode","Tudo","All","Imagens","Images","Vídeos","Videos",
    "Shopping","Notícias","News","Maps","Livros","Books","Web","Fórum","Forums",
    "Vídeos curtos","Short videos","Mais","More","Ferramentas","Tools"];
  var labels = [], all = document.querySelectorAll('a, span, div, button');
  for (var i = 0; i < all.length && labels.length < 60; i++) {
    var e = all[i];
    if (e.children.length > 2) continue;
    var t = (e.textContent || '').trim();
    if (t.length <= 16 && LABELS.indexOf(t) !== -1) {
      var r0 = e.getBoundingClientRect();
      if (r0.width > 5 && r0.height > 5 && r0.top < 300) labels.push(e);
    }
  }
  var buckets = {};
  for (var j = 0; j < labels.length; j++) {
    var tb = Math.round(labels[j].getBoundingClientRect().top / 20) * 20;
    (buckets[tb] = buckets[tb] || []).push(labels[j]);
  }
  var row = [];
  for (var k in buckets) if (buckets[k].length > row.length) row = buckets[k];
  out.labelCount = labels.length;
  out.rowCount = row.length;
  if (row.length) {
    var minL = Infinity, maxR = -Infinity, names = [];
    for (var m = 0; m < row.length; m++) {
      var r2 = row[m].getBoundingClientRect();
      minL = Math.min(minL, r2.left); maxR = Math.max(maxR, r2.right);
      names.push(row[m].textContent.trim().slice(0, 12));
    }
    out.row = {l: Math.round(minL), r: Math.round(maxR), w: Math.round(maxR - minL), center: Math.round((minL + maxR) / 2)};
    out.names = names;
    // overlap check: sort labels by left, flag any whose left is before the
    // previous one's right (with 1px tolerance)
    var boxes = [];
    for (var n = 0; n < row.length; n++) {
      var rb = row[n].getBoundingClientRect();
      boxes.push({name: row[n].textContent.trim().slice(0, 14), l: Math.round(rb.left), r: Math.round(rb.right), t: Math.round(rb.top)});
    }
    boxes.sort(function (a, b) { return (a.l - b.l) || (a.t - b.t); });
    out.overlaps = [];
    for (var p = 1; p < boxes.length; p++) {
      if (boxes[p].l < boxes[p-1].r - 1 && Math.abs(boxes[p].t - boxes[p-1].t) < 24) {
        out.overlaps.push(boxes[p-1].name + "[" + boxes[p-1].l + "-" + boxes[p-1].r + "] x " + boxes[p].name + "[" + boxes[p].l + "-" + boxes[p].r + "]");
      }
    }
    out.boxes = boxes;
  }
  // which element carries our transform, and does it/its ancestors clip?
  out.transformed = [];
  var tfs = document.querySelectorAll('[style*="translateX"]');
  for (var q = 0; q < tfs.length; q++) {
    var te = tfs[q];
    var tr = te.getBoundingClientRect();
    if (tr.top < 300 && tr.width > 100) {
      var ov = [];
      var anc = te;
      for (var a = 0; a < 4 && anc; a++, anc = anc.parentElement) {
        if (!anc.nodeType || anc === document.body) break;
        var acs = getComputedStyle(anc);
        ov.push((typeof anc.className === 'string' ? anc.className : '').slice(0, 22) + ':' + acs.overflowX);
      }
      out.transformed.push({cls: (typeof te.className === 'string' ? te.className : '').slice(0, 30),
        rect: {l: Math.round(tr.left), r: Math.round(tr.right), w: Math.round(tr.width)}, chain: ov});
    }
  }
  return out;
}; 'ok';"""

cmd(s, 2, "WebDriver:ExecuteScript", {"script": DEFINE, "args": []})
res = cmd(s, 3, "WebDriver:ExecuteScript", {"script": "return JSON.stringify(window.__verify2());", "args": []})
val = res.get("value") if isinstance(res, dict) else res
data = json.loads(val)
print("clientW:", data.get("clientW"), "center:", data.get("center"))
print("pill:", json.dumps(data.get("pill")), "tf:", data.get("pillTf"))
print("col:", json.dumps(data.get("col")))
print("row:", json.dumps(data.get("row")))
print("transformed elems:")
for t in data.get("transformed", []):
    print("  ", json.dumps(t))
real = [o for o in data.get("overlaps", []) if o.split(" x ")[0].split("[")[0] != o.split(" x ")[1].split("[")[0]]
print("real-overlaps (different labels):", len(real), real[:5])
print("lbl-chain:", json.dumps(data.get("boxes", []))[:1200])

shot = cmd(s, 4, "WebDriver:TakeScreenshot", {"full": False})
b64 = shot.get("value") if isinstance(shot, dict) else shot
if isinstance(b64, str):
    open("/tmp/after_fix2.png", "wb").write(base64.b64decode(b64))
    print("screenshot saved: /tmp/after_fix2.png")
