import argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

_ap = argparse.ArgumentParser(description="procedural album cover")
_ap.add_argument("--out", default="cover.png")
_ap.add_argument("--title", default="THE SPECTRE")
_ap.add_argument("--artist", default="ALAN WALKER")
_ap.add_argument("--size", type=int, default=1000)
_args, _ = _ap.parse_known_args()
rng = np.random.default_rng(11)
S = _args.size
y = np.linspace(0, 1, S)[:, None]; x = np.linspace(0, 1, S)[None, :]

# deep indigo -> near black radial
d = np.sqrt((x - 0.5) ** 2 + (y - 0.42) ** 2) / 0.85
base = np.zeros((S, S, 3), np.float32)
for k, col in [(0.0, (46, 40, 96)), (0.45, (18, 20, 46)), (1.0, (6, 6, 12))]:
    pass
g = np.clip(1 - d, 0, 1) ** 1.6
base += g[..., None] * np.array([52, 46, 112])[None, None, :]
base += (1 - np.clip(d, 0, 1))[..., None] * np.array([8, 6, 14])[None, None, :]
base += np.array([6, 6, 12])[None, None, :]
img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))

# smoke swirls
sm = Image.new('RGB', (S, S), (0, 0, 0)); sd = ImageDraw.Draw(sm)
for _ in range(16):
    cx, cy = rng.integers(150, S - 150), rng.integers(120, S - 200)
    rw, rh = rng.integers(160, 420), rng.integers(80, 260)
    col = (rng.integers(40, 90), rng.integers(50, 100), rng.integers(120, 200))
    sd.ellipse([cx - rw, cy - rh, cx + rw, cy + rh], fill=col)
sm = sm.filter(ImageFilter.GaussianBlur(70))
img = Image.blend(img, Image.blend(img, sm, 0.5), 0.55)

d = ImageDraw.Draw(img)
# concentric rings
for i, r in enumerate((300, 240, 180)):
    d.ellipse([S/2 - r, S*0.42 - r, S/2 + r, S*0.42 + r],
              outline=(120 + i*30, 150 + i*25, 235 - i*20), width=2)

# ghost silhouette (soft vertical glow)
ghost = Image.new('RGB', (S, S), (0, 0, 0)); gd = ImageDraw.Draw(ghost)
gd.ellipse([S/2 - 95, S*0.30, S/2 + 95, S*0.52], fill=(150, 175, 235))
gd.polygon([(S/2 - 110, S*0.50), (S/2 + 110, S*0.50), (S/2 + 150, S*0.72), (S/2 - 150, S*0.72)],
           fill=(120, 145, 210))
ghost = ghost.filter(ImageFilter.GaussianBlur(34))
img = Image.blend(img, Image.blend(img, ghost, 0.35), 0.45)

# vignette
v = Image.new('L', (S, S), 0); vd = ImageDraw.Draw(v)
for r in range(int(S*0.78), 0, -8):
    vd.ellipse([S/2 - r, S/2 - r, S/2 + r, S/2 + r], fill=int(255 - 150*(r/(S*0.78))**2))
v = v.filter(ImageFilter.GaussianBlur(70))
img = Image.composite(img, Image.new('RGB', (S, S), (2, 2, 4)), v)

# typography
def font(sz, bold=True):
    p = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    return ImageFont.truetype(p, sz)

d = ImageDraw.Draw(img)
def spaced(text, y, fnt, fill, gap):
    w = sum(fnt.getlength(c) + gap for c in text) - gap
    xx = (S - w) / 2
    for c in text:
        d.text((xx, y), c, font=fnt, fill=fill)
        xx += fnt.getlength(c) + gap

spaced(_args.title.upper()[:18], S*0.78, font(74), (255, 255, 255), 6)
spaced(_args.artist.upper()[:24], S*0.875, font(30, False), (170, 180, 205), 10)

# grain
arr = np.asarray(img).astype(np.int16) + rng.normal(0, 3.0, (S, S, 1)).repeat(3, axis=2)
img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
img.save(_args.out)
print('cover ->', _args.out)
