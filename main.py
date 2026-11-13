#!/usr/bin/env python3
"""Mochi the Red Panda - a chibi cuteness illustration, drawn procedurally.

Pure stdlib. Renders at 2x supersampling into a byte buffer, downscales,
and writes entry.png (1024x1024) into $MAKEFUN_OUTPUT_DIR. Deterministic.
"""
import os
import math
import zlib
import struct
import random

OUT = 1024
SS = 2
W = OUT * SS
H = OUT * SS
BUF = bytearray(W * H * 3)


def S(v):
    """design space (1024) -> render space"""
    return v * SS


# ---------------------------------------------------------------- buffer ops
def blend_span(y, x0, x1, r, g, b, a):
    """alpha-blend a horizontal span (render space coords)."""
    if y < 0 or y >= H:
        return
    x0 = max(0, x0)
    x1 = min(W - 1, x1)
    if x1 < x0:
        return
    ia = 255 - a
    base = (y * W + x0) * 3
    for i in range(base, base + (x1 - x0 + 1) * 3, 3):
        BUF[i] = (BUF[i] * ia + r * a) // 255
        BUF[i + 1] = (BUF[i + 1] * ia + g * a) // 255
        BUF[i + 2] = (BUF[i + 2] * ia + b * a) // 255


def solid_span(y, x0, x1, rgb):
    if y < 0 or y >= H:
        return
    x0 = max(0, x0)
    x1 = min(W - 1, x1)
    if x1 < x0:
        return
    n = x1 - x0 + 1
    base = (y * W + x0) * 3
    BUF[base:base + n * 3] = bytes(rgb) * n


# ---------------------------------------------------------------- primitives
def ellipse(cx, cy, rx, ry, rgb, alpha=255):
    """filled ellipse, design coords."""
    cx, cy, rx, ry = S(cx), S(cy), S(rx), S(ry)
    y0 = int(cy - ry)
    y1 = int(cy + ry)
    for y in range(y0, y1 + 1):
        t = (y - cy) / ry
        dx = rx * math.sqrt(max(0.0, 1.0 - t * t))
        if alpha >= 255:
            solid_span(y, int(cx - dx), int(cx + dx), rgb)
        else:
            blend_span(y, int(cx - dx), int(cx + dx), rgb[0], rgb[1], rgb[2], alpha)


def ellipse_grad(cx, cy, rx, ry, c_in, c_out, lx=0.35, ly=0.35):
    """ellipse with radial gradient; light centre offset (lx,ly) in radii."""
    cx, cy, rx, ry = S(cx), S(cy), S(rx), S(ry)
    y0 = int(cy - ry)
    y1 = int(cy + ry)
    dr = c_out[0] - c_in[0]
    dg = c_out[1] - c_in[1]
    db = c_out[2] - c_in[2]
    for y in range(y0, y1 + 1):
        ny = (y - cy) / ry
        w = math.sqrt(max(0.0, 1.0 - ny * ny))
        dx = rx * w
        x0 = int(cx - dx)
        x1 = int(cx + dx)
        if x1 < 0 or x0 >= W or y < 0 or y >= H:
            continue
        base = (y * W + max(0, x0)) * 3
        yy = ny + ly
        for x in range(max(0, x0), min(W - 1, x1) + 1):
            nx = (x - cx) / rx + lx
            d2 = nx * nx + yy * yy
            t = d2 if d2 < 1.0 else 1.0
            t = t * t * (3.0 - 2.0 * t)
            BUF[base] = int(c_in[0] + dr * t)
            BUF[base + 1] = int(c_in[1] + dg * t)
            BUF[base + 2] = int(c_in[2] + db * t)
            base += 3


def disc(cx, cy, r, rgb, alpha=255):
    ellipse(cx, cy, r, r, rgb, alpha)


def polygon(points, rgb, alpha=255):
    """scanline polygon fill, design coords."""
    pts = [(S(x), S(y)) for x, y in points]
    ys = [p[1] for p in pts]
    y0 = max(0, int(min(ys)))
    y1 = min(H - 1, int(max(ys)))
    n = len(pts)
    for y in range(y0, y1 + 1):
        yc = y + 0.5
        xs = []
        for i in range(n):
            xa, ya = pts[i]
            xb, yb = pts[(i + 1) % n]
            if (ya <= yc < yb) or (yb <= yc < ya):
                xs.append(xa + (yc - ya) * (xb - xa) / (yb - ya))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            if alpha >= 255:
                solid_span(y, int(xs[i]), int(xs[i + 1]), rgb)
            else:
                blend_span(y, int(xs[i]), int(xs[i + 1]), rgb[0], rgb[1], rgb[2], alpha)


def thick_line(x0, y0, x1, y1, width, rgb, alpha=255):
    steps = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
    for i in range(steps + 1):
        t = i / steps
        disc(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, width / 2, rgb, alpha)


def arc_line(cx, cy, r, a0, a1, width, rgb, alpha=255):
    steps = int(abs(a1 - a0) * r * 2) + 1
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        disc(cx + r * math.cos(a), cy + r * math.sin(a), width / 2, rgb, alpha)


def star4(cx, cy, r, rgb, alpha=255):
    pts = []
    for i in range(8):
        ang = math.pi / 2 + i * math.pi / 4
        rad = r if i % 2 == 0 else r * 0.30
        pts.append((cx + rad * math.cos(ang), cy - rad * math.sin(ang)))
    polygon(pts, rgb, alpha)


def heart(cx, cy, s, rgb, alpha=255):
    disc(cx - s * 0.42, cy - s * 0.18, s * 0.52, rgb, alpha)
    disc(cx + s * 0.42, cy - s * 0.18, s * 0.52, rgb, alpha)
    polygon([(cx - s * 0.88, cy + s * 0.05), (cx + s * 0.88, cy + s * 0.05),
             (cx, cy + s * 1.05)], rgb, alpha)


def soft_ellipse(cx, cy, rx, ry, rgb, alpha, layers=5):
    for i in range(layers, 0, -1):
        f = 1.0 + 0.10 * i
        ellipse(cx, cy, rx * f, ry * f, rgb, alpha // (layers + 1 - i + 1))


# ---------------------------------------------------------------- background
def background():
    top = (255, 241, 220)
    mid = (255, 222, 192)
    bot = (255, 205, 178)
    glow_c = (S(770), S(215))
    for yo in range(OUT):
        if yo < 560:
            t = yo / 560
            c = tuple(int(top[i] + (mid[i] - top[i]) * t) for i in range(3))
        else:
            t = (yo - 560) / (OUT - 560)
            c = tuple(int(mid[i] + (bot[i] - mid[i]) * t) for i in range(3))
        for sy in range(SS):
            y = yo * SS + sy
            base = y * W * 3
            BUF[base:base + W * 3] = bytes(c) * W
    # warm sun glow, low-res blocks are fine (very smooth)
    for yo in range(0, OUT, 2):
        for xo in range(0, OUT, 2):
            dx = S(xo) - glow_c[0]
            dy = S(yo) - glow_c[1]
            d2 = (dx * dx + dy * dy) / (S(430) * S(430))
            if d2 < 1.0:
                a = int(70 * (1.0 - d2) ** 2)
                for sy in range(SS * 2):
                    for sx in range(SS * 2):
                        x = xo * SS + sx
                        y = yo * SS + sy
                        if 0 <= x < W and 0 <= y < H:
                            i = (y * W + x) * 3
                            BUF[i] = min(255, BUF[i] + a)
                            BUF[i + 1] = min(255, BUF[i + 1] + a * 3 // 4)
    # distant hill + one soft ground mound (no hard rim)
    polygon([(-20, 780), (240, 700), (520, 752), (800, 692), (1044, 770),
             (1044, 1024), (-20, 1024)], (244, 183, 168), 110)
    ellipse(512, 1062, 660, 190, (255, 216, 182), 255)


def bokeh(rng, front=False):
    for _ in range(15 if front else 24):
        cx = rng.uniform(20, 1004)
        cy = rng.uniform(20, 1004) if front else rng.uniform(20, 860)
        r = rng.uniform(9, 40 if front else 55)
        col = rng.choice([(255, 255, 255), (255, 205, 215), (255, 226, 170),
                          (255, 196, 190)])
        a = rng.randint(14, 42 if front else 60)
        disc(cx, cy, r, col, a)
        disc(cx, cy, r * 0.72, col, a // 2)


# ---------------------------------------------------------------- character
RUST_IN = (240, 138, 76)
RUST_OUT = (203, 92, 44)
CREAM_IN = (255, 248, 232)
CREAM_OUT = (250, 228, 196)
DARK = (74, 44, 32)
INK = (43, 26, 20)


def tail():
    # banded tail curling up the right side: circles along an arc
    bands = [(RUST_IN, RUST_OUT), (CREAM_IN, CREAM_OUT)]
    pts = []
    for i in range(9):
        t = i / 8
        ang = -0.5 + t * 2.05
        cx = 690 + 205 * math.cos(ang)
        cy = 800 + 205 * math.sin(ang)
        pts.append((cx, cy, 96 - 26 * t))
    for i, (cx, cy, r) in enumerate(pts):
        ci, co = bands[i % 2]
        ellipse_grad(cx, cy, r, r * 0.94, ci, co, 0.3, 0.3)
    # fluffy tip
    cx, cy, r = pts[-1]
    ellipse_grad(cx, cy, r * 1.02, r, CREAM_IN, CREAM_OUT, 0.3, 0.3)


def ears():
    for ex in (310, 714):
        ellipse_grad(ex, 268, 96, 86, (156, 96, 58), (110, 64, 40), 0.3, 0.3)
        ellipse_grad(ex, 274, 64, 58, CREAM_IN, CREAM_OUT, 0.3, 0.3)
        ellipse(ex, 280, 36, 32, (255, 178, 186), 255)
        # small soft ear-tip tufts
        for k in (-1, 0, 1):
            polygon([(ex + k * 27 - 8, 196), (ex + k * 27 + 8, 196),
                     (ex + k * 31, 172)], (110, 64, 40), 255)


def body():
    # soft contact shadow
    soft_ellipse(512, 918, 265, 40, (196, 120, 84), 120, 5)
    # body
    ellipse_grad(512, 742, 218, 188, RUST_IN, RUST_OUT, 0.32, 0.32)
    ellipse_grad(512, 782, 132, 122, CREAM_IN, CREAM_OUT, 0.3, 0.3)
    # feet in front, sitting pose, toe beans facing viewer
    for fx in (384, 640):
        ellipse_grad(fx, 902, 76, 48, RUST_IN, RUST_OUT, 0.3, 0.3)
        ellipse(fx, 908, 29, 19, (255, 168, 178), 255)
        for k in (-1, 0, 1):
            ellipse(fx + k * 33, 882, 10, 13, (255, 168, 178), 255)
    # side arms resting on belly
    for ax in (330, 694):
        ellipse_grad(ax, 762, 52, 84, RUST_IN, RUST_OUT, 0.3, 0.3)
    # bamboo shoot held in front (rounded stalk)
    polygon([(496, 838), (528, 838), (534, 742), (490, 742)], (104, 186, 98), 255)
    disc(512, 838, 17, (104, 186, 98), 255)
    disc(512, 744, 21, (128, 201, 110), 255)
    polygon([(490, 742), (534, 742), (530, 716), (494, 716)], (128, 201, 110), 255)
    polygon([(512, 716), (462, 668), (506, 690)], (110, 190, 100), 255)
    polygon([(512, 716), (566, 664), (520, 690)], (110, 190, 100), 255)
    polygon([(512, 722), (512, 640), (540, 700)], (140, 210, 118), 255)
    # paws over the bamboo
    for px in (452, 572):
        ellipse_grad(px, 792, 40, 34, RUST_IN, RUST_OUT, 0.3, 0.3)
        for k in (-1, 0, 1):
            ellipse(px + k * 22, 776, 7, 9, (255, 168, 178), 255)


def head():
    hx, hy, hr = 512, 428, 238
    # rim light crescent (light from upper-left)
    disc(hx - 9, hy - 10, hr + 7, (255, 214, 150), 200)
    ellipse_grad(hx, hy, hr, hr * 0.97, RUST_IN, RUST_OUT, 0.34, 0.34)
    # cheek fur tufts (short, soft, mostly inside the silhouette)
    for sx, d in ((290, -1), (734, 1)):
        for k in range(3):
            y0 = 508 + k * 36
            polygon([(sx, y0), (sx + d * 30, y0 + 15), (sx, y0 + 27)],
                    (219, 110, 55), 255)
    # head top tuft: three soft rounded bumps
    for k in (-1, 0, 1):
        disc(512 + k * 36, 202 - (8 if k == 0 else 0), 15, (219, 110, 55), 255)
    # cream face mask: two lobes + bridge
    ellipse_grad(410, 478, 108, 122, CREAM_IN, CREAM_OUT, 0.3, 0.3)
    ellipse_grad(614, 478, 108, 122, CREAM_IN, CREAM_OUT, 0.3, 0.3)
    ellipse_grad(512, 512, 96, 104, CREAM_IN, CREAM_OUT, 0.3, 0.3)
    # brow spots
    ellipse(398, 322, 36, 17, CREAM_IN, 235)
    ellipse(626, 322, 36, 17, CREAM_IN, 235)


def eye(ex):
    ey = 452
    # iris: deep brown radial, amber inner glow
    ellipse_grad(ex, ey, 57, 69, (122, 72, 38), (35, 20, 14), -0.25, -0.3)
    ellipse_grad(ex, ey + 12, 40, 50, (146, 90, 46), (58, 34, 20), -0.2, -0.25)
    ellipse(ex, ey + 8, 24, 33, (24, 14, 10), 255)  # pupil
    # glossy highlights
    disc(ex - 17, ey - 24, 16, (255, 255, 255), 255)
    disc(ex + 15, ey + 12, 8.5, (255, 255, 255), 235)
    disc(ex - 3, ey + 27, 4.5, (255, 255, 255), 220)
    star4(ex + 6, ey - 34, 9, (255, 255, 255), 200)
    # upper lash line + lashes
    arc_line(ex, ey - 4, 60, math.radians(195), math.radians(345), 7, INK)
    for k, (dx, dy, a) in enumerate(((-52, -30, 2.6), (-30, -52, 2.95), (34, -50, 0.35))):
        thick_line(ex + dx * 0.82, ey + dy * 0.82, ex + dx, ey + dy - 8, 6, INK)


def face():
    eye(404)
    eye(620)
    # nose + mouth
    ellipse_grad(512, 548, 27, 20, (110, 66, 48), (52, 30, 22), 0.3, 0.35)
    disc(503, 541, 6, (255, 235, 225), 200)
    thick_line(512, 566, 512, 577, 5, DARK)
    arc_line(499, 579, 14, math.radians(15), math.radians(160), 5.5, DARK)
    arc_line(525, 579, 14, math.radians(20), math.radians(165), 5.5, DARK)
    ellipse(512, 595, 13, 9, (255, 138, 158), 255)  # tiny tongue
    # blush with soft edge + sparkle dots
    for bx in (322, 702):
        soft_ellipse(bx, 548, 48, 25, (255, 140, 165), 120, 5)
        ellipse(bx, 548, 40, 20, (255, 150, 172), 120)
        for k in range(3):
            disc(bx - 18 + k * 17, 540 + (k % 2) * 9, 2.6, (255, 255, 255), 200)
    # whiskers
    for sx, d in ((318, -1), (706, 1)):
        for k in range(3):
            y0 = 540 + k * 17
            thick_line(sx, y0, sx + d * 62, y0 - 8 + k * 13, 3.4,
                       (255, 240, 220), 150)


def deco(rng):
    star4(238, 296, 24, (255, 214, 120), 235)
    star4(792, 348, 19, (255, 255, 255), 230)
    star4(848, 628, 15, (255, 214, 120), 220)
    star4(168, 612, 14, (255, 255, 255), 210)
    star4(700, 150, 13, (255, 255, 255), 200)
    heart(232, 150, 26, (255, 150, 175), 225)
    heart(742, 232, 19, (255, 170, 190), 210)
    # pink bow perched on the right ear
    polygon([(700, 192), (656, 166), (656, 218)], (255, 150, 175), 255)
    polygon([(700, 192), (744, 166), (744, 218)], (255, 150, 175), 255)
    disc(700, 192, 12, (240, 112, 142), 255)
    disc(696, 188, 4, (255, 220, 230), 255)
    heart(858, 470, 15, (255, 150, 175), 190)
    # drifting petals
    for _ in range(14):
        cx = rng.uniform(30, 994)
        cy = rng.uniform(30, 700)
        r = rng.uniform(6, 12)
        ellipse(cx, cy, r, r * 0.62, (255, 183, 197), rng.randint(90, 160))


def main():
    rng = random.Random(20261113)
    background()
    bokeh(rng, front=False)
    tail()
    ears()
    body()
    head()
    face()
    deco(rng)
    bokeh(rng, front=True)
    # downscale 2x2 box
    out = bytearray(OUT * OUT * 3)
    for yo in range(OUT):
        r0 = (yo * SS) * W * 3
        r1 = r0 + W * 3
        ob = yo * OUT * 3
        for xo in range(OUT):
            i0 = r0 + xo * SS * 3
            i1 = r1 + xo * SS * 3
            o = ob + xo * 3
            out[o] = (BUF[i0] + BUF[i0 + 3] + BUF[i1] + BUF[i1 + 3]) >> 2
            out[o + 1] = (BUF[i0 + 1] + BUF[i0 + 3 + 1] + BUF[i1 + 1] + BUF[i1 + 3 + 1]) >> 2
            out[o + 2] = (BUF[i0 + 2] + BUF[i0 + 3 + 2] + BUF[i1 + 2] + BUF[i1 + 3 + 2]) >> 2
    # PNG with Sub filter
    stride = OUT * 3
    raw = bytearray()
    for yo in range(OUT):
        raw.append(1)
        row = out[yo * stride:(yo + 1) * stride]
        prev = 0
        filt = bytearray(stride)
        for i, v in enumerate(row):
            left = row[i - 3] if i >= 3 else 0
            filt[i] = (v - left) & 0xFF
        raw += filt

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", OUT, OUT, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + chunk(b"IEND", b""))
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", ".")
    with open(os.path.join(outdir, "entry.png"), "wb") as f:
        f.write(png)


if __name__ == "__main__":
    main()
