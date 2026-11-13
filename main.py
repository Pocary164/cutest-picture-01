#!/usr/bin/env python3
"""cutest-picture-01 entry: a chibi baby red panda, drawn entirely by code.

Pure Python 3 standard library, no network, fully deterministic (seeded PRNG
only). Renders a 1024x1024 picture with a small software rasterizer
(anti-aliased ellipses and strokes, painter's order) and writes it as a PNG
to $MAKEFUN_OUTPUT_DIR/entry.png.
"""

import math
import os
import random
import struct
import zlib

W = H = 1024
N = W * H

# ---------------------------------------------------------------------------
# Frame buffers (float RGB, 0..255)
# ---------------------------------------------------------------------------
R = [0.0] * N
G = [0.0] * N
B = [0.0] * N


def _clamp01(v):
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)


def blend(i, col, a):
    """Alpha-over blend of col into pixel i with coverage a in 0..1."""
    if a <= 0.0:
        return
    if a >= 1.0:
        R[i] = col[0]
        G[i] = col[1]
        B[i] = col[2]
    else:
        ia = 1.0 - a
        R[i] = R[i] * ia + col[0] * a
        G[i] = G[i] * ia + col[1] * a
        B[i] = B[i] * ia + col[2] * a


def ellipse(cx, cy, rx, ry, col, amax=1.0, soft=1.3, fall=0.0, grad=None,
            frame=None):
    """Filled ellipse with anti-aliased edge.

    col: (r, g, b). grad: optional (top, bottom) colours mixed vertically.
    fall: if > 0, alpha falls off radially as (1 - q) ** fall (soft blob).
    frame: optional (ox, oy, ca, sa); shape coords live in a rotated frame
    whose origin sits at canvas (ox, oy); (ca, sa) = (cos, sin) of its tilt.
    """
    if rx <= 0 or ry <= 0 or amax <= 0.0:
        return
    # Canvas-space bounding box.
    if frame is None:
        x0 = int(max(0, math.floor(cx - rx - 2)))
        x1 = int(min(W - 1, math.ceil(cx + rx + 2)))
        y0 = int(max(0, math.floor(cy - ry - 2)))
        y1 = int(min(H - 1, math.ceil(cy + ry + 2)))
    else:
        ox, oy, ca, sa = frame
        pts = []
        for lx, ly in ((cx - rx, cy - ry), (cx + rx, cy - ry),
                       (cx - rx, cy + ry), (cx + rx, cy + ry)):
            pts.append((ox + ca * lx - sa * ly, oy + sa * lx + ca * ly))
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x0 = int(max(0, math.floor(min(xs) - 2)))
        x1 = int(min(W - 1, math.ceil(max(xs) + 2)))
        y0 = int(max(0, math.floor(min(ys) - 2)))
        y1 = int(min(H - 1, math.ceil(max(ys) + 2)))
    minr = min(rx, ry)
    irx = 1.0 / rx
    iry = 1.0 / ry
    for y in range(y0, y1 + 1):
        row = y * W
        for x in range(x0, x1 + 1):
            if frame is None:
                u = x - cx
                v = y - cy
            else:
                ox, oy, ca, sa = frame
                dx = x - ox
                dy = y - oy
                u = ca * dx + sa * dy - cx
                v = -sa * dx + ca * dy - cy
            q = (u * irx) * (u * irx) + (v * iry) * (v * iry)
            if fall > 0.0:
                if q >= 1.0:
                    continue
                a = amax * ((1.0 - q) ** fall)
            else:
                if q >= 1.21:
                    continue
                d = (math.sqrt(q) - 1.0) * minr
                a = amax * _clamp01(0.5 - d / soft + 0.5)
            if a <= 0.003:
                continue
            if grad is not None:
                t = _clamp01(0.5 + v / (2.0 * ry))
                c = (grad[0][0] + (grad[1][0] - grad[0][0]) * t,
                     grad[0][1] + (grad[1][1] - grad[0][1]) * t,
                     grad[0][2] + (grad[1][2] - grad[0][2]) * t)
            else:
                c = col
            blend(row + x, c, a)


def stroke(pts, rad, col, amax=1.0):
    """A smooth stroke: filled circles stamped along a point list."""
    for (x, y) in pts:
        ellipse(x, y, rad, rad, col, amax=amax, soft=1.2)


def qbez(p0, p1, p2, n=60):
    pts = []
    for i in range(n + 1):
        t = i / n
        s = 1.0 - t
        pts.append((s * s * p0[0] + 2 * s * t * p1[0] + t * t * p2[0],
                    s * s * p0[1] + 2 * s * t * p1[1] + t * t * p2[1]))
    return pts


def earc(cx, cy, rx, ry, a0, a1, n=40):
    """Points along an elliptical arc, angles in radians."""
    pts = []
    for i in range(n + 1):
        t = a0 + (a1 - a0) * (i / n)
        pts.append((cx + rx * math.cos(t), cy + ry * math.sin(t)))
    return pts


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
BG_TOP = (255, 241, 220)
BG_BOT = (255, 204, 172)
FUR_TOP = (246, 148, 86)
FUR_BOT = (216, 100, 50)
FUR = (232, 124, 66)
FUR_DARK = (172, 74, 36)
CREAM = (255, 246, 230)
CREAM_SH = (248, 224, 192)
EAR_OUT = (112, 63, 44)
EAR_RIM = (255, 249, 240)
EAR_IN = (250, 203, 178)
EYE_TOP = (64, 37, 35)
EYE_BOT = (126, 76, 54)
NOSE = (94, 49, 49)
MOUTH = (122, 64, 54)
BLUSH = (255, 120, 136)
WHITE = (255, 255, 255)
PETAL = (255, 178, 198)
FLOWER_C = (255, 206, 92)
LEAF = (141, 205, 141)


def background(rng):
    # Vertical gradient.
    for y in range(H):
        t = y / (H - 1)
        r = BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * t
        g = BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * t
        b = BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * t
        base = y * W
        for x in range(W):
            i = base + x
            R[i] = r
            G[i] = g
            B[i] = b
    # Warm glow behind the subject.
    ellipse(512, 470, 470, 430, WHITE, amax=0.34, fall=1.6)
    # Bokeh: soft pastel circles.
    tints = [(255, 255, 255), (255, 214, 196), (255, 226, 208),
             (255, 199, 214)]
    for _ in range(26):
        cx = rng.uniform(0, W)
        cy = rng.uniform(0, H)
        rad = rng.uniform(14, 74)
        col = tints[rng.randrange(len(tints))]
        ellipse(cx, cy, rad, rad, col, amax=rng.uniform(0.05, 0.16),
                fall=1.3)
    # A few tiny sparkles (four-point stars from two thin ellipses).
    for (sx, sy, s) in ((148, 176, 30), (884, 148, 36), (118, 430, 22),
                        (908, 436, 24), (252, 104, 20), (788, 88, 22)):
        ellipse(sx, sy, s * 0.16, s, WHITE, amax=0.75, soft=1.6)
        ellipse(sx, sy, s, s * 0.16, WHITE, amax=0.75, soft=1.6)
        ellipse(sx, sy, s * 0.22, s * 0.22, WHITE, amax=0.9, soft=1.4)


def tail():
    # Banded tail curling up on the right: fat dots along a curve.
    pts = qbez((700, 940), (950, 920), (918, 660), n=90)
    for k, (x, y) in enumerate(pts):
        t = k / len(pts)
        rad = 56 - 20 * t
        col = CREAM if (k // 11) % 2 == 1 else FUR
        ellipse(x, y, rad, rad * 0.92, col, amax=1.0, soft=1.2,
                grad=(FUR_TOP, FUR_BOT) if col is FUR else None)


def body():
    ellipse(512, 972, 320, 34, (120, 60, 40), amax=0.14, fall=1.2)  # shadow
    ellipse(512, 872, 238, 168, FUR, grad=(FUR_TOP, FUR_BOT))
    ellipse(512, 902, 142, 104, CREAM, grad=(CREAM, CREAM_SH))


def paw(sx, sy):
    """A raised paw with toe beans, centred at (sx, sy)."""
    ellipse(sx, sy, 58, 72, FUR, grad=(FUR_TOP, FUR_BOT))
    ellipse(sx, sy + 16, 27, 33, CREAM, amax=0.95)
    for dx in (-30, 0, 30):
        ellipse(sx + dx, sy - 34, 10, 13, CREAM, amax=0.95)


def head():
    # Head group: tilted frame, origin at head centre on canvas.
    tilt = math.radians(-7.0)
    fr = (512.0, 462.0, math.cos(tilt), math.sin(tilt))

    def E(cx, cy, rx, ry, col, **kw):
        ellipse(cx, cy, rx, ry, col, frame=fr, **kw)

    # Ears: cream rim, dark outer, soft inner.
    for sgn in (-1, 1):
        ex = 242 * sgn
        E(ex, -202, 118, 124, EAR_RIM)
        E(ex, -198, 102, 109, EAR_OUT, grad=((128, 74, 52), (96, 52, 38)))
        E(ex, -192, 64, 72, EAR_IN)
    # Head base + soft outline pass (slightly larger, darker, lower).
    E(0, 6, 322, 296, FUR_DARK)
    E(0, 0, 318, 292, FUR, grad=(FUR_TOP, FUR_BOT))
    # Face mask: cream patches (muzzle + around the eyes).
    E(0, 96, 210, 158, CREAM, grad=(CREAM, CREAM_SH))
    E(-118, -14, 102, 110, CREAM)
    E(118, -14, 102, 110, CREAM)
    # White brow spots.
    E(-118, -128, 54, 27, CREAM, amax=0.95)
    E(118, -128, 54, 27, CREAM, amax=0.95)
    # Forehead shading: a gentle darker cap at the very bottom edge.
    E(0, 262, 240, 60, FUR_DARK, amax=0.18, fall=1.1)
    # Blush.
    E(-206, 94, 58, 30, BLUSH, amax=0.55, fall=1.0)
    E(206, 94, 58, 30, BLUSH, amax=0.55, fall=1.0)
    # Eyes: big, glossy, with lash arcs.
    for sgn in (-1, 1):
        ex = 118 * sgn
        E(ex, -4, 55, 71, EYE_TOP, grad=(EYE_TOP, EYE_BOT))
        # highlights
        E(ex - 17, -27, 17, 21, WHITE, amax=0.98)
        E(ex + 15, 22, 9, 11, WHITE, amax=0.85)
        E(ex + 21, -38, 5.5, 7, WHITE, amax=0.9)
        # upper lash: thick dark arc over the top of the eye
        pts = earc(ex, -4, 61, 77, math.pi * 1.08, math.pi * 1.92, n=36)
        loc = []
        for (lx, ly) in pts:
            ox, oy, ca, sa = fr
            loc.append((ox + ca * lx - sa * ly, oy + sa * lx + ca * ly))
        stroke(loc, 6.5, (74, 42, 38), amax=0.85)
    # Nose + tiny highlight.
    E(0, 96, 28, 20, NOSE)
    E(-9, 89, 7, 5, WHITE, amax=0.8)
    # Mouth: philtrum + two small arcs (a "w" mouth).
    stroke([(512.0, 462.0)], 0.1, MOUTH, amax=0.0)  # no-op keeps order clear
    ox, oy, ca, sa = fr

    def to_canvas(lx, ly):
        return (ox + ca * lx - sa * ly, oy + sa * lx + ca * ly)

    pts = [to_canvas(0, 114 + 3 * math.sin(t)) for t in
           [i * 0.1 for i in range(5)]]
    stroke([to_canvas(0, 112), to_canvas(0, 126)], 4.5, MOUTH, amax=0.95)
    for sgn in (-1, 1):
        arc = earc(17 * sgn, 122, 17, 13, math.pi * 0.12, math.pi * 0.88,
                   n=24)
        stroke([to_canvas(lx, ly) for (lx, ly) in arc], 4.5, MOUTH,
               amax=0.95)
    # Flower tucked by the right ear: five petals + golden centre.
    fx, fy = 258, -172
    for k in range(5):
        a = k * (2 * math.pi / 5) - math.pi / 2
        E(fx + 27 * math.cos(a), fy + 27 * math.sin(a), 24, 24, PETAL)
    E(fx + 20, fy + 34, 26, 12, LEAF)
    E(fx, fy, 15, 15, FLOWER_C)


def foreground():
    # A whisper of foreground bokeh at the corners.
    ellipse(66, 950, 120, 100, WHITE, amax=0.10, fall=1.4)
    ellipse(966, 930, 130, 110, (255, 214, 196), amax=0.10, fall=1.4)
    ellipse(950, 70, 90, 80, WHITE, amax=0.08, fall=1.4)


def vignette():
    cx, cy = W / 2, H / 2
    maxd = math.hypot(cx, cy)
    for y in range(H):
        for x in range(W):
            d = math.hypot(x - cx, y - cy) / maxd
            f = 1.0 - 0.09 * (d * d)
            i = y * W + x
            R[i] *= f
            G[i] *= f
            B[i] *= f


def draw():
    rng = random.Random(20261113)
    background(rng)
    tail()
    body()
    head()
    paw(192, 664)
    paw(832, 664)
    foreground()
    vignette()


# ---------------------------------------------------------------------------
# PNG writing
# ---------------------------------------------------------------------------
def write_png(path):
    bR = bytes([max(0, min(255, int(v + 0.5))) for v in R])
    bG = bytes([max(0, min(255, int(v + 0.5))) for v in G])
    bB = bytes([max(0, min(255, int(v + 0.5))) for v in B])
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        s = y * W
        row = bytearray(W * 3)
        row[0::3] = bR[s:s + W]
        row[1::3] = bG[s:s + W]
        row[2::3] = bB[s:s + W]
        raw += row
    comp = zlib.compress(bytes(raw), 6)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        c += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return c

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
           chunk(b"IDAT", comp) + chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)


def main():
    draw()
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    write_png(os.path.join(outdir, "entry.png"))


if __name__ == "__main__":
    main()
