import numpy as np
from PIL import Image, ImageDraw, ImageFilter
rng = np.random.default_rng(21)
W, H = 2560, 1440
y = np.linspace(0, 1, H)[:, None]; x = np.linspace(0, 1, W)[None, :]

# base: near black with a faint cool floor
base = np.zeros((H, W, 3), np.float32) + np.array([4, 4, 6])[None, None, :]

def radial(cx, cy, rad, colour, strength, power=2.0):
    d = np.sqrt(((x - cx) * (W / H)) ** 2 + (y - cy) ** 2) / rad
    f = np.clip(1 - d, 0, 1) ** power * strength
    return f[..., None] * np.array(colour)[None, None, :]

# warm key light (behind the figure, upper right) + hot rim
base += radial(0.62, 0.42, 0.55, (255, 118, 26), 1.0, 2.2)
base += radial(0.62, 0.40, 0.22, (255, 196, 120), 0.9, 2.6)
base += radial(0.18, 0.85, 0.55, (18, 26, 44), 0.8, 2.0)

img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))

# volumetric rays from the light source
rays = Image.new('RGB', (W, H), (0, 0, 0)); rd = ImageDraw.Draw(rays)
for k in range(14):
    ang = rng.uniform(-1.5, 1.5)
    ln = rng.uniform(900, 2000)
    cx, cy = W * 0.62, H * 0.42
    rd.line([(cx, cy), (cx + ln * np.cos(ang), cy + ln * np.sin(ang))],
            fill=(int(rng.uniform(30, 70)), int(rng.uniform(18, 42)), 6),
            width=int(rng.uniform(20, 90)))
rays = rays.filter(ImageFilter.GaussianBlur(70))
img = Image.blend(img, Image.blend(img, rays, 0.5), 0.6)

# smoke clouds
sm = Image.new('RGB', (W, H), (0, 0, 0)); sd = ImageDraw.Draw(sm)
for _ in range(26):
    cx, cy = rng.integers(0, W), rng.integers(int(H * 0.2), H)
    rw, rh = rng.integers(180, 520), rng.integers(90, 260)
    v = rng.integers(18, 46)
    sd.ellipse([cx - rw, cy - rh, cx + rw, cy + rh], fill=(v, int(v * 0.8), int(v * 0.7)))
sm = sm.filter(ImageFilter.GaussianBlur(80))
img = Image.blend(img, Image.blend(img, sm, 0.45), 0.55)

# rain streaks
rain = Image.new('RGB', (W, H), (0, 0, 0)); rd = ImageDraw.Draw(rain)
for _ in range(1400):
    sx, sy = rng.integers(-200, W), rng.integers(0, H)
    ln = rng.integers(20, 90)
    rd.line([(sx, sy), (sx - int(ln * 0.35), sy + ln)],
            fill=(int(rng.uniform(90, 160)), int(rng.uniform(95, 165)), int(rng.uniform(110, 190))),
            width=1)
rain = rain.filter(ImageFilter.GaussianBlur(1.2))
img = Image.blend(img, Image.blend(img, rain, 0.5), 0.5)

# embers
em = Image.new('RGB', (W, H), (0, 0, 0)); ed = ImageDraw.Draw(em)
for _ in range(240):
    cx, cy = rng.integers(0, W), rng.integers(0, H)
    r = rng.integers(1, 4)
    ed.ellipse([cx - r, cy - r, cx + r, cy + r],
               fill=(int(rng.uniform(180, 255)), int(rng.uniform(90, 170)), 30))
em = em.filter(ImageFilter.GaussianBlur(2.0))
img = Image.blend(img, Image.blend(img, em, 0.55), 0.7)

# vignette
v = Image.new('L', (W, H), 0); vd = ImageDraw.Draw(v)
for r in range(int(W * 0.8), 0, -12):
    vd.ellipse([W / 2 - r * 1.2, H / 2 - r, W / 2 + r * 1.2, H / 2 + r],
               fill=int(255 - 175 * (r / (W * 0.8)) ** 2))
v = v.filter(ImageFilter.GaussianBlur(120))
img = Image.composite(img, Image.new('RGB', (W, H), (2, 2, 3)), v)

arr = np.asarray(img).astype(np.int16) + rng.normal(0, 3.5, (H, W, 1)).repeat(3, axis=2)
img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
img.save('bg_motiv.png')
print('bg ok')
