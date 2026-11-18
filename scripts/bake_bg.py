import argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

_ap = argparse.ArgumentParser(description="bloom + teal-orange grade + vignette")
_ap.add_argument("--in", dest="src", default="bg_cine.png")
_ap.add_argument("--out", dest="dst", default="bg_baked.png")
_ap.add_argument("--width", type=int, default=1920)
_ap.add_argument("--height", type=int, default=1080)
_args, _ = _ap.parse_known_args()

img = Image.open(_args.src).convert('RGB').resize((_args.width, _args.height), Image.LANCZOS)

# --- bloom / halation on highlights ---
arr = np.asarray(img).astype(np.float32) / 255.0
lum = arr.max(axis=2)
mask = np.clip((lum - 0.55) / 0.45, 0, 1) ** 1.5
bright = (arr * mask[..., None] * 255).astype(np.uint8)
bloom = Image.fromarray(bright).filter(ImageFilter.GaussianBlur(28))
bloom2 = Image.fromarray(bright).filter(ImageFilter.GaussianBlur(70))
img = Image.blend(img, Image.blend(img, bloom, 0.55), 0.45)
img = Image.blend(img, Image.blend(img, bloom2, 0.40), 0.35)

# --- teal-orange grade ---
arr = np.asarray(img).astype(np.float32) / 255.0
sh = arr[..., 2] - arr[..., 0]          # blue minus red
shadow_w = np.clip(0.55 - arr.mean(axis=2), 0, 1)[..., None]
high_w = np.clip(arr.mean(axis=2) - 0.45, 0, 1)[..., None]
arr = arr + shadow_w * np.array([-0.02, 0.01, 0.06]) + high_w * np.array([0.07, 0.02, -0.03])
arr = np.clip(arr, 0, 1)
# gentle S-curve contrast
arr = np.clip((arr - 0.5) * 1.08 + 0.5, 0, 1)
img = Image.fromarray((arr * 255).astype(np.uint8))

# --- vignette ---
W, H = img.size
v = Image.new('L', (W, H), 0); vd = ImageDraw.Draw(v)
for r in range(int(W * 0.8), 0, -12):
    vd.ellipse([W / 2 - r * 1.2, H / 2 - r, W / 2 + r * 1.2, H / 2 + r],
               fill=int(255 - 165 * (r / (W * 0.8)) ** 2))
v = v.filter(ImageFilter.GaussianBlur(120))
img = Image.composite(img, Image.new('RGB', (W, H), (2, 2, 3)), v)

img.save(_args.dst)
print('baked ->', _args.dst)
