# Spotify-Style Lyric Video — Production Brief

**Ye file kisi bhi chat mein paste kar do, saath mein audio + cover + lyrics bhej do — bas.**
Neeche poora spec aur ready-to-run code hai, isliye koi bhi assistant (ya main) bilkul isi
quality ka lyric video bana sakta hai.

---

## 1. Inputs (kya chahiye)

| # | Cheez | Format | Na ho to |
|---|-------|--------|----------|
| 1 | Gaana | `.mp3` / `.m4a` / `.wav` | — zaroori |
| 2 | Cover art | square `.png`/`.jpg`, min 1000×1000 | main Figma se bana dunga (Section 5) ya procedural (Appendix B) |
| 3 | Lyrics + timing | `.srt` (ek cue per line) ya `.lrc` | main audio se transcribe + align kar dunga (Section 4) |
| 4 | Title + artist | text | cover/metadata se |
| 5 | Length | full song ya `--start` / `--duration` (jaise 20s teaser) | default poora gaana |

SRT format:

```
1
00:00:09,600 --> 00:00:13,980
Hello, hello, can you hear me?
```

---

## 2. Design spec (yahi rakho, tabhi look match karega)

| Element | Value |
|---|---|
| Canvas | 1920×1080, 30 fps, h264 CRF 19 + AAC 192k |
| Background | cover 1.25× scale, 58px blur, 66% dark overlay (#08090E) |
| Album card | x=150, y=120, 600×600, radius 18, shadow blur 22 / alpha 135 |
| Title / artist | bold 40px white / 30px #9698A4, card se 46px neeche |
| Icons | star outline + 3 dots, right edge, #D2D2DA |
| Progress bar | card se 140px neeche, track #50525C 4px, fill gold #F0C05A, knob 12px |
| Time labels | 21px #9698A2 — left `0:42`, right `-2:03` |
| Lyrics column | centre x=1370, active line y=520 |
| Active / ±1 / ±2 / ±3 line | 54px white bold / 42px #9698A4 / 38px #696A76 / 34px #484954 |
| Line spacing | 104px |
| Gold accent | #F0C05A |

**Motion (yahi "smooth" feel deta hai):** position continuous hai, jump nahi —
`scroll = (activeIndex - 1) + smoothstep((t - lineStart + 0.30) / 0.60)`.
Line change par 0.6s eased glide, 0.30s pehle shuru hota hai.

---

## 3. Run kaise kare

```bash
pip install pillow imageio-ffmpeg

# poora gaana
python spotify_lyrics.py --audio song.mp3 --srt song.srt --cover cover.png \
    --title "Song (Nightcore)" --artist "Artist" --out lyric_video.mp4

# 20 second teaser (9.6s se)
python spotify_lyrics.py --audio song.mp3 --srt song.srt --cover cover.png \
    --title "Song" --artist "Artist" --start 9.6 --duration 20 --out teaser.mp4
```

Lambe gaane 3–4 chunks mein render karo, phir jodo:

```bash
python spotify_lyrics.py ... --start 0   --duration 45 --out p1.mp4
python spotify_lyrics.py ... --start 45  --duration 45 --out p2.mp4
python spotify_lyrics.py ... --start 90  --duration 45 --out p3.mp4
python spotify_lyrics.py ... --start 135 --duration 30 --out p4.mp4
printf "file 'p1.mp4'\nfile 'p2.mp4'\nfile 'p3.mp4'\nfile 'p4.mp4'\n" > parts.txt
ffmpeg -f concat -safe 0 -i parts.txt -c copy full.mp4
```

Speed: 1080p30 par ~1.7 video-second per render-second (2 cores) → 45s chunk ≈ 80s.
2 GB RAM pod par chunk 45s se bada mat rakho (ffmpeg `Cannot allocate memory` dega).

---

## 4. SRT nahi hai? (transcription + alignment)

1. **ASR with word timestamps** — `faster-whisper`, `word_timestamps=True`,
   `language="hi"` / `"en"`. 2GB RAM par 10s se bade audio chunk `mkl_malloc` error dete hain —
   audio ko 8–10s chunks mein todo, offset add karo.
2. **Official lyrics text** user se lo. Gaane mein ASR ka text galat aata hai — sirf timing ke liye use karo.
3. **Align** — official words vs ASR words par `difflib.SequenceMatcher`
   (lowercase, punctuation strip). Match hue words ko ASR timing, baaki ko aage-peeche ke
   matched words ke beech proportionally baant do.
4. **SRT** — line start = pehla word, end = aakhri word. ±0.2–0.4s normal hai.
5. **Gap** — do lines ke beech 6s se zyada (instrumental) ho to lyrics hide karo ya
   chhota equaliser dikhao; blank screen mat chhodo.

---

## 5. Cover art (Figma)

1. `create_new_file` → design file (need `planKey` from `whoami`).
2. `generate_vector_illustration` (kind `illustration`, 1000×1000). Prompt example:
   > "Album cover illustration in delicate hand-drawn line-art style: a lone figure in a hooded
   > jacket seen from behind under a street lamp on a rainy night, thin ink outlines, soft indigo
   > violet and dusty rose watercolor washes, minimal pale background, melancholic romantic mood,
   > elegant poster art, no text"
   *(Figma AI credits kharch hote hain — per call.)*
3. `use_figma` se compose: 1000×1000 frame → illustration child → gradient scrim
   (transparent → #050510 @0.92) → indigo wash (multiply 35%) → title (Inter Bold, letterspacing 7)
   → gold 110×4 bar → subtitle.
4. `get_screenshot` (1000×1000) → PNG → wahi `--cover` mein do.

---

## 6. QA checklist

- [ ] duration = audio duration (±0.1s), 1920×1080, 30fps
- [ ] audio stream maujood, drift nahi
- [ ] progress bar ka time playback time ke barabar, remaining sahi (`-2:33` type)
- [ ] ek hi active line, transition par jump nahi (2–3 frames check karo)
- [ ] koi line clip nahi ho rahi
- [ ] instrumental gap mein screen khaali nahi
- [ ] cover text card ke andar, icons title se overlap nahi

---

## 7. Variations

- **20s teaser** → `--start 9.6 --duration 20`
- **9:16 reels** → `--width 1080 --height 1920` (card upar, lyrics neeche karne ke liye layout numbers scale hote hain)
- **Karaoke word highlight** → active line ke andar word-by-word gold highlight (word timings chahiye)
- **Accent colour** → gold ki jagah rose/cyan (`GOLD` constant badlo)

---

## Appendix A — `spotify_lyrics.py` (self-contained renderer)

```python
#!/usr/bin/env python3
"""
spotify_lyrics.py — Spotify "now playing" style lyric video generator.

Layout: blurred cover background, rounded album card + title/artist + progress bar
on the left, smoothly scrolling lyrics on the right (active line bright, neighbours
dimmed, continuous eased scroll — no jumping).

Requirements:
    pip install pillow imageio-ffmpeg      (or have ffmpeg on PATH)

Usage:
    python spotify_lyrics.py --audio song.mp3 --srt song.srt --cover cover.png \
        --title "The Spectre (Nightcore)" --artist "Alan Walker" --out video.mp4

    # 20 second teaser from 9.6s
    python spotify_lyrics.py ... --start 9.6 --duration 20 --out teaser.mp4

For long songs render in chunks (e.g. 0-45, 45-90, ...) and join:
    ffmpeg -f concat -safe 0 -i parts.txt -c copy full.mp4
"""

import argparse
import math
import os
import re
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

GOLD = (240, 192, 90)
WHITE = (255, 255, 255)


# --------------------------------------------------------------------------- #
# fonts
# --------------------------------------------------------------------------- #
_FONTS = {}


def font(size, bold=True, bold_path=None, reg_path=None):
    key = (size, bold)
    if key in _FONTS:
        return _FONTS[key]
    candidates = []
    if bold:
        candidates += [bold_path] if bold_path else []
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ]
    else:
        candidates += [reg_path] if reg_path else []
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/Library/Fonts/Arial.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]
    f = None
    for p in candidates:
        if p and os.path.exists(p):
            f = ImageFont.truetype(p, size)
            break
    if f is None:
        f = ImageFont.load_default()
    _FONTS[key] = f
    return f


# --------------------------------------------------------------------------- #
# subtitles
# --------------------------------------------------------------------------- #
def ts_to_sec(x):
    x = x.strip().replace(",", ".")
    parts = [float(p) for p in x.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    h, m, s = parts[-3:]
    return h * 3600 + m * 60 + s


def parse_srt(path):
    raw = open(path, encoding="utf-8-sig").read().replace("\r\n", "\n")
    out = []
    for block in re.split(r"\n\s*\n", raw.strip()):
        rows = [r for r in block.split("\n") if r.strip()]
        idx = 1 if rows and re.fullmatch(r"\d+", rows[0].strip()) else 0
        if len(rows) <= idx or "-->" not in rows[idx]:
            continue
        a, b = rows[idx].split("-->")
        text = " ".join(r.strip() for r in rows[idx + 1:]).strip()
        if text:
            out.append((ts_to_sec(a), ts_to_sec(b), text))
    return sorted(out)


def audio_duration(path):
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            out = subprocess.check_output(
                [ffprobe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=nw=1:nk=1", path])
            return float(out.decode().strip())
        except Exception:
            pass
    # ffprobe missing: ask ffmpeg itself
    try:
        out = subprocess.run([ffmpeg_exe(), "-i", path], capture_output=True).stderr.decode()
        m = re.search(r"Duration: (\d+):(\d+):(\d+\.?\d*)", out)
        if m:
            h, mi, se = m.groups()
            return int(h) * 3600 + int(mi) * 60 + float(se)
    except Exception:
        pass
    try:
        import av
        with av.open(path) as c:
            return float(c.duration) / 1e6
    except Exception:
        return 0.0


def ffmpeg_exe():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def fmt_clock(x):
    x = max(x, 0)
    return f"{int(x // 60)}:{int(x % 60):02d}"


def smoothstep(p):
    p = min(max(p, 0.0), 1.0)
    return p * p * (3 - 2 * p)


# --------------------------------------------------------------------------- #
# renderer
# --------------------------------------------------------------------------- #
class SpotifyLyrics:
    def __init__(self, lines, cover, title, artist, total, w=1920, h=1080,
                 accent=GOLD, bold_path=None, reg_path=None):
        self.W, self.H = w, h
        self.lines = lines
        self.total = total or (lines[-1][1] if lines else 1.0)
        self.accent = accent
        self.bp, self.rp = bold_path, reg_path
        s = w / 1920.0                                   # scale vs 1080p design

        self.f_title = font(int(40 * s), True, bold_path, reg_path)
        self.f_artist = font(int(30 * s), False, bold_path, reg_path)
        self.f_time = font(int(21 * s), False, bold_path, reg_path)

        self.card_x, self.card_y, self.card = int(150 * s), int(120 * s), int(600 * s)
        self.cx, self.cy = int(1370 * s), int(520 * s)
        self.spacing = int(104 * s)

        # background: blurred cover + dark overlay
        bg = cover.resize((int(h * cover.width / cover.height * 1.25), int(h * 1.25)),
                          Image.LANCZOS)
        left = (bg.width - w) // 2
        top = (bg.height - h) // 2
        bg = bg.crop((left, top, left + w, top + h)).filter(
            ImageFilter.GaussianBlur(max(18, int(58 * s))))
        self.bg = Image.blend(bg, Image.new("RGB", (w, h), (8, 9, 14)), 0.66)

        self.base = self._build_base(cover, title, artist, s)
        self._tiles = {}

    # -- static chrome, rendered once -------------------------------------- #
    def _build_base(self, cover, title, artist, s):
        W, H = self.W, self.H
        img = self.bg.copy()

        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle(
            [self.card_x - 10, self.card_y + 14,
             self.card_x + self.card + 10, self.card_y + self.card + 30],
            radius=int(30 * s), fill=(0, 0, 0, 135))
        shadow = shadow.filter(ImageFilter.GaussianBlur(int(22 * s)))
        img = Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB")

        art = cover.resize((self.card, self.card), Image.LANCZOS)
        mask = Image.new("L", (self.card, self.card), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, self.card, self.card],
                                               radius=int(18 * s), fill=255)
        img.paste(art, (self.card_x, self.card_y), mask)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([self.card_x, self.card_y,
                             self.card_x + self.card, self.card_y + self.card],
                            radius=int(18 * s), outline=(60, 60, 70), width=1)

        ty = self.card_y + self.card + int(46 * s)
        tf, size = self.f_title, int(40 * s)
        while tf.getlength(title) > self.card - int(120 * s) and size > int(24 * s):
            size -= max(1, int(s))
            tf = font(size, True, self.bp, self.rp)
        d.text((self.card_x, ty), title, font=tf, fill=WHITE)
        d.text((self.card_x, ty + int(56 * s)), artist, font=self.f_artist,
               fill=(150, 152, 164))

        # star + dots
        ix, iy = self.card_x + self.card - int(14 * s), ty + int(18 * s)
        for k in range(3):
            r = int(4 * s)
            cy = iy + (k - 1) * int(14 * s)
            d.ellipse([ix - r, cy - r, ix + r, cy + r], fill=(210, 210, 218))
        sx = ix - int(58 * s)
        pts = []
        for k in range(10):
            ang = -math.pi / 2 + k * math.pi / 5
            rad = (16 if k % 2 == 0 else 7) * s
            pts.append((sx + rad * math.cos(ang), iy + rad * math.sin(ang)))
        d.polygon(pts, outline=(210, 210, 218), width=max(1, int(2 * s)))

        self.py = ty + int(140 * s)
        d.line([(self.card_x, self.py), (self.card_x + self.card, self.py)],
               fill=(80, 82, 92), width=max(2, int(4 * s)))
        return img

    # -- glyph cache -------------------------------------------------------- #
    def _tile(self, text, fnt, colour, key):
        k = (text, colour, key)
        t = self._tiles.get(k)
        if t is None:
            pad = 10
            wpx = int(fnt.getlength(text)) + pad * 2
            asc, desc = fnt.getmetrics()
            im = Image.new("RGBA", (max(wpx, 1), asc + desc + pad * 2), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((pad, pad), text, font=fnt, fill=colour + (255,))
            t = (im, pad)
            self._tiles[k] = t
        return t

    def _put(self, img, text, fnt, colour, key, x, y):
        t, pad = self._tile(text, fnt, colour, key)
        img.paste(t, (int(x) - pad, int(y) - pad), t)

    # -- scroll ------------------------------------------------------------- #
    def scroll_pos(self, t):
        lines = self.lines
        idx = None
        for i, (a, b, _) in enumerate(lines):
            if a <= t <= b:
                idx = i
                break
        if idx is None:
            for i, (a, b, _) in enumerate(lines):
                if a > t:
                    idx = i
                    break
            if idx is None:
                idx = len(lines) - 1
        p = smoothstep((t - (lines[idx][0] - 0.30)) / 0.60)
        return (idx - 1 + p) if idx > 0 else idx * p

    # -- frame -------------------------------------------------------------- #
    def frame(self, t):
        s = self.W / 1920.0
        img = self.base.copy()
        d = ImageDraw.Draw(img)

        # progress
        frac = min(max(t / self.total, 0), 1) if self.total else 0
        px = self.card_x + int(self.card * frac)
        d.line([(self.card_x, self.py), (px, self.py)], fill=self.accent,
               width=max(2, int(4 * s)))
        knob = max(3, int(6 * s))
        d.ellipse([px - knob, self.py - knob, px + knob, self.py + knob], fill=self.accent)
        d.text((self.card_x, self.py + int(18 * s)), fmt_clock(t),
               font=self.f_time, fill=(150, 152, 162))
        d.text((self.card_x + self.card, self.py + int(18 * s)),
               "-" + fmt_clock(self.total - t), font=self.f_time,
               fill=(150, 152, 162), anchor="ra")

        # lyrics
        scroll = self.scroll_pos(t)
        tiers = [(0.5, 54, WHITE, "a", True), (1.5, 42, (150, 152, 164), "b", False),
                 (2.5, 38, (105, 106, 118), "c", False), (3.2, 34, (72, 73, 84), "d", False)]
        for j, (a, b, text) in enumerate(self.lines):
            dist = abs(j - scroll)
            if dist > 3.2:
                continue
            for lim, size, colour, key, bold in tiers:
                if dist < lim:
                    fnt = font(int(size * s), bold, self.bp, self.rp)
                    y = self.cy + (j - scroll) * self.spacing - int(24 * s)
                    x = self.cx - fnt.getlength(text) / 2
                    self._put(img, text, fnt, colour, key, x, y)
                    break
        return img


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Spotify-style lyric video")
    ap.add_argument("--audio", required=True)
    ap.add_argument("--srt", required=True)
    ap.add_argument("--cover", required=True)
    ap.add_argument("--title", default="Song Title")
    ap.add_argument("--artist", default="Artist")
    ap.add_argument("--out", default="lyric_video.mp4")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--font", dest="reg", help="regular .ttf path")
    ap.add_argument("--font-bold", dest="bold", help="bold .ttf path")
    args = ap.parse_args()

    lines = parse_srt(args.srt)
    if not lines:
        sys.exit("no cues found in %s" % args.srt)

    total = audio_duration(args.audio) or lines[-1][1]
    end = args.start + (args.duration if args.duration else max(0.0, total - args.start))

    cover = Image.open(args.cover).convert("RGB")
    R = SpotifyLyrics(lines, cover, args.title, args.artist, total,
                      args.width, args.height, GOLD, args.bold, args.reg)

    ff = ffmpeg_exe()
    subprocess.run([ff, "-y", "-ss", str(args.start), "-t", str(end - args.start),
                    "-i", args.audio, "-ac", "2", "-ar", "44100", "_lyric_audio.wav"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    cmd = [ff, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{args.width}x{args.height}", "-r", str(args.fps), "-i", "-",
           "-i", "_lyric_audio.wav",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
           "-x264-params", "rc-lookahead=10", "-pix_fmt", "yuv420p", "-threads", "2",
           "-c:a", "aac", "-b:a", "192k", "-shortest", args.out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                         stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    n = int(round((end - args.start) * args.fps))
    for i in range(n):
        p.stdin.write(R.frame(args.start + i / args.fps).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        sys.exit(p.stderr.read().decode()[-1200:])
    try:
        os.remove("_lyric_audio.wav")
    except OSError:
        pass
    print(f"done: {args.out}  ({n} frames, {n / args.fps:.1f}s)")


if __name__ == "__main__":
    main()

```

---

## Appendix B — `cover_art.py` (procedural cover, Figma na ho to)

```python
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
rng = np.random.default_rng(11)
S = 1000
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

spaced('THE SPECTRE', S*0.78, font(74), (255, 255, 255), 6)
spaced('ALAN WALKER', S*0.875, font(30, False), (170, 180, 205), 10)

# grain
arr = np.asarray(img).astype(np.int16) + rng.normal(0, 3.0, (S, S, 1)).repeat(3, axis=2)
img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
img.save('cover_spectre.png')
print('cover ok')

```
