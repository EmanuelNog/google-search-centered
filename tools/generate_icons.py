#!/usr/bin/env python3
"""Generate the add-on icons (deterministic, no dependencies).

Concept: a wide screen with the results column pulled to the viewport center —
blue column with text bars centered, ghost bars left/right showing the rest of
the page. Drawn at 8x supersampling, box-downsampled to 96 and 48 px.
"""
import struct, zlib, os

S = 8                 # supersample factor
BIG = 96 * S          # 768

def new_buf(size):
    return bytearray(size * size * 4)  # RGBA

def put(buf, size, x, y, color):
    i = (y * size + x) * 4
    buf[i:i+4] = bytes(color)

def fill_rounded_rect(buf, size, x0, y0, x1, y1, radius, color):
    """Filled rounded rectangle [x0,x1)x[y0,y1) with corner radius."""
    r = radius
    for y in range(max(0, int(y0)), min(size, int(y1))):
        for x in range(max(0, int(x0)), min(size, int(x1))):
            # corner distance check
            cx = None
            if x < x0 + r:
                cx = x0 + r
            elif x >= x1 - r:
                cx = x1 - r
            cy = None
            if y < y0 + r:
                cy = y0 + r
            elif y >= y1 - r:
                cy = y1 - r
            if cx is not None and cy is not None:
                if (x - cx) ** 2 + (y - cy) ** 2 > r * r:
                    continue
            put(buf, size, x, y, color)

def downsample(buf, big, factor):
    n = big // factor
    out = bytearray(n * n * 4)
    area = factor * factor
    for y in range(n):
        for x in range(n):
            rt = gt = bt = at = 0
            for dy in range(factor):
                for dx in range(factor):
                    i = ((y * factor + dy) * big + (x * factor + dx)) * 4
                    a = buf[i + 3]
                    rt += buf[i] * a
                    gt += buf[i + 1] * a
                    bt += buf[i + 2] * a
                    at += a
            o = (y * n + x) * 4
            if at == 0:
                out[o:o+4] = b"\x00\x00\x00\x00"
            else:
                out[o] = rt // at
                out[o+1] = gt // at
                out[o+2] = bt // at
                out[o+3] = at // area
    return out, n

def write_png(path, buf, n):
    raw = bytearray()
    for y in range(n):
        raw.append(0)
        raw += buf[y * n * 4:(y + 1) * n * 4]
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", n, n, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + chunk(b"IEND", b""))
    open(path, "wb").write(png)
    print(f"{path}: {n}x{n}, {len(png)} bytes")

def k(v):
    """scale helper: design coords are for 96px; scale to BIG."""
    return int(round(v * S))

def draw():
    size = BIG
    buf = new_buf(size)
    white = (255, 255, 255, 255)
    border = (218, 220, 224, 255)   # #DADCE0
    screen_bg = (248, 249, 250, 255)  # #F8F9FA
    blue = (66, 133, 244, 255)      # #4285F4
    ghost = (232, 234, 237, 255)    # #E8EAED

    # rounded app tile with a light border
    fill_rounded_rect(buf, size, k(4), k(4), k(92), k(92), k(22), border)
    fill_rounded_rect(buf, size, k(6), k(6), k(90), k(90), k(20), white)

    # screen
    fill_rounded_rect(buf, size, k(16), k(26), k(80), k(74), k(8), border)
    fill_rounded_rect(buf, size, k(18), k(28), k(78), k(72), k(6), screen_bg)

    # ghost bars (left / right — the rest of a wide page)
    fill_rounded_rect(buf, size, k(25), k(39), k(40), k(43), k(2), ghost)
    fill_rounded_rect(buf, size, k(25), k(50), k(36), k(54), k(2), ghost)
    fill_rounded_rect(buf, size, k(56), k(39), k(71), k(43), k(2), ghost)
    fill_rounded_rect(buf, size, k(60), k(50), k(71), k(54), k(2), ghost)

    # centered results column with text bars
    fill_rounded_rect(buf, size, k(43), k(32), k(53), k(68), k(4), blue)
    for i, (ty, tx1) in enumerate(((40, 50), (48, 50), (56, 47))):
        fill_rounded_rect(buf, size, k(45), k(ty), k(tx1), k(ty + 2.4), k(1.2), white)

    return buf

if __name__ == "__main__":
    root = os.path.join(os.path.dirname(__file__), "..", "icons")
    os.makedirs(root, exist_ok=True)
    big = draw()
    for px, factor in ((96, 8), (48, 16), (32, 24)):
        out, n = downsample(big, BIG, factor)
        write_png(os.path.join(root, f"icon-{px}.png"), out, n)
