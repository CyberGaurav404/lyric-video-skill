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
_HERE = os.path.dirname(os.path.abspath(__file__))
_ASSETS = os.path.join(_HERE, "assets", "fonts")
DEVANAGARI_FONTS = {
    True: [os.path.join(_ASSETS, "NotoSansDevanagari-Bold.ttf"),
           "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
           os.path.join(_ASSETS, "Kalam-Bold.ttf")],
    False: [os.path.join(_ASSETS, "NotoSansDevanagari-Regular.ttf"),
            "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
            os.path.join(_ASSETS, "Kalam-Bold.ttf")],
}


def font(size, bold=True, bold_path=None, reg_path=None, deva=False):
    key = (size, bold, deva)
    if key in _FONTS:
        return _FONTS[key]
    candidates = []
    if deva:
        candidates += DEVANAGARI_FONTS[bold]
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


def has_devanagari(text):
    return any("\u0900" <= ch <= "\u097F" for ch in text)


def font_for(text, size, bold, bold_path=None, reg_path=None):
    return font(size, bold, bold_path, reg_path, has_devanagari(text))


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
        self.deva = any("\u0900" <= ch <= "\u097F" for _, _, txt in lines for ch in txt)

        self.f_title = font(int(40 * s), True, bold_path, reg_path)
        self.f_artist = font(int(30 * s), False, bold_path, reg_path)
        self.f_time = font(int(21 * s), False, bold_path, reg_path, self.deva)

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
            tf = font_for(title, size, True, self.bp, self.rp)
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
                    fnt = font_for(text, int(size * s), bold, self.bp, self.rp)
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
