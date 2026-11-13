# Cutest Picture — a chibi baby red panda, drawn entirely by code

`main.py` is a small software renderer (Python 3 standard library only, no
network, fully deterministic) that draws one picture and writes it to
`$MAKEFUN_OUTPUT_DIR/entry.png` (1024×1024 PNG).

**The picture:** a chibi baby red panda with a gently tilted head — huge
glossy eyes with lash arcs and triple highlights, a cream face mask with
white brow spots, pink blush, a tiny nose and "w" mouth, a pink flower
tucked by one ear, both front paws raised showing cream toe beans, a
chubby seated body, and a cream-banded tail curling up beside it. The
background is a soft peach gradient with pastel bokeh and sparkles.

**How it is generated:** every shape is an anti-aliased ellipse or stroke
painted in order into a float frame buffer by a tiny rasterizer written
for this entry; the face is drawn in a rotated frame to get the head
tilt. A seeded PRNG (fixed seed) places the background bokeh, so two runs
produce byte-identical output. The PNG is encoded with `zlib` + `struct`
from the standard library.

Run it the way the grader does:

```
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
# writes out/entry.png
```
