# Cutest Picture — "Mochi the Red Panda" (v2)

A pure-Python (stdlib only) procedural illustration of a chibi baby red panda,
rendered by a hand-written rasterizer and written to `entry.png`
(1024×1024) in the directory named by `$MAKEFUN_OUTPUT_DIR`.

Techniques: span-fill ellipses/polygons with per-pixel radial-gradient
shading, layered-alpha soft edges (blush, shadows, bokeh), crescent rim
light, multi-highlight glossy eyes, and 2× supersampling with a box
downscale for anti-aliasing. Fully deterministic (fixed seed); two runs
produce byte-identical output.

Run: `python3 main.py` — no arguments, no network, no dependencies.
