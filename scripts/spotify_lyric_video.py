#!/usr/bin/env python3
"""
spotify_lyric_video.py
----------------------
Spotify "now playing / lyrics" style lyric video generator.

Layout (16:9 by default):
  * blurred album-art background with a dark overlay
  * rounded album card on the left, title + artist + star/dots icons below it
  * progress bar with elapsed time and remaining time
  * scrolling lyrics on the right, active line bright white, others dimmed,
    with "..." separators where the song has an instrumental gap

Requirements:
    pip install pillow imageio-ffmpeg
    (imageio-ffmpeg ships an ffmpeg binary; a system ffmpeg on PATH also works)

Usage:
    python spotify_lyric_video.py \
        --audio song.mp3 \
        --lyrics song.srt \
        --cover cover.jpg \
        --title "Song Name" \
        --artist "Artist Name" \
        --out lyric_video.mp4

    # just a 10 second excerpt starting at 9.6 s
    python spotify_lyric_video.py --audio song.mp3 --lyrics song.srt \
        --cover cover.jpg --title "Song" --artist "Artist" \
        --start 9.6 --duration 10 --out demo.mp4

Lyrics input: an .srt file (or an .lrc file) with one line per cue.
Generate one with any transcription/alignment tool, or write it by hand:

    1
    00:00:09,600 --> 00:00:13,980
    Hello, hello, can you hear me?

If --cover is not given, a simple placeholder cover is drawn from the title.
"""

import argparse
import math
import os
import re
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def load_font(size, bold=False, font_path=None):
    """Return a truetype font, falling back to common system fonts."""
    candidates = []
    if font_path:
        candidates.append(font_path)
    if bold:
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ]
    else:
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/Library/Fonts/Arial.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def ts_to_seconds(ts):
    """'00:01:02,500' (SRT) or '00:01:02.50' / '01:02.50' (LRC) -> seconds."""
    ts = ts.strip().replace(",", ".")
    parts = ts.split(":")
    parts = [float(p) for p in parts]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    h, m, s = parts[-3:]
    return h * 3600 + m * 60 + s


def parse_lyrics(path):
    """Read an .srt or .lrc file -> list of (start, end, text)."""
    raw = open(path, encoding="utf-8-sig").read().replace("\r\n", "\n")
    lines = []

    if path.lower().endswith(".lrc"):
        stamps = []
        for row in raw.split("\n"):
            m = re.match(r"\[(\d+):(\d+[.,]\d+)\](.*)", row)
            if m:
                stamps.append((int(m.group(1)) * 60 + ts_to_seconds(m.group(2)),
                               m.group(3).strip()))
        stamps = [(t, txt) for t, txt in stamps if txt]
        for i, (t, txt) in enumerate(stamps):
            end = stamps[i + 1][0] if i + 1 < len(stamps) else t + 3.0
            lines.append((t, end, txt))
        return lines

    # SRT
    for block in re.split(r"\n\s*\n", raw.strip()):
        rows = [r for r in block.split("\n") if r.strip()]
        if not rows:
            continue
        idx = 0
        if re.fullmatch(r"\d+", rows[0].strip()):
            idx = 1
        if idx >= len(rows) or "-->" not in rows[idx]:
            continue
        a, b = rows[idx].split("-->")
        text = " ".join(r.strip() for r in rows[idx + 1:]).strip()
        if text:
            lines.append((ts_to_seconds(a), ts_to_seconds(b), text))
    return sorted(lines)


def audio_duration(path):
    """Duration in seconds using ffprobe (falls back to 0 if unavailable)."""
    try:
        ffprobe = shutil.which("ffprobe")
        if ffprobe:
            out = subprocess.check_output(
                [ffprobe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=nw=1:nk=1", path])
            return float(out.decode().strip())
    except Exception:
        pass
    try:
        import av  # PyAV, optional
        with av.open(path) as c:
            return float(c.duration) / 1e6
    except Exception:
        return 0.0


def ffmpeg_exe():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        sys.exit("ffmpeg not found: pip install imageio-ffmpeg")


def fmt_clock(sec):
    sec = max(sec, 0)
    return f"{int(sec // 60)}:{int(sec % 60):02d}"


# --------------------------------------------------------------------------- #
# artwork
# --------------------------------------------------------------------------- #
def make_placeholder_cover(size, title, artist):
    cover = Image.new("RGB", (size, size), (12, 14, 26))
    d = ImageDraw.Draw(cover)
    for y in range(size):
        t = y / size
        d.line([(0, y), (size, y)],
               fill=(int(16 + 26 * t), int(18 + 20 * t), int(38 + 34 * t)))
    glow = Image.new("RGB", (size, size), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r in range(int(size * 0.48), 0, -10):
        a = int(90 * (1 - r / (size * 0.48)))
        gd.ellipse([size / 2 - r, size * 0.42 - r, size / 2 + r, size * 0.42 + r],
                   fill=(a // 3, a // 2, a))
    cover = Image.blend(cover, Image.blend(cover, glow, 0.6), 0.85)
    d = ImageDraw.Draw(cover)
    for r in (int(size * 0.28), int(size * 0.23), int(size * 0.19)):
        d.ellipse([size / 2 - r, size * 0.42 - r, size / 2 + r, size * 0.42 + r],
                  outline=(120, 170, 255), width=max(2, size // 300))
    def fit(text, start, max_ratio=0.86, bold=False):
        fsize = int(size * start)
        font = load_font(fsize, bold=bold)
        while font.getlength(text) > size * max_ratio and fsize > 12:
            fsize -= 2
            font = load_font(fsize, bold=bold)
        return font

    t_txt, a_txt = title.upper(), artist.upper()
    d.text((size / 2, size * 0.80), t_txt,
           font=fit(t_txt, 0.07, bold=True), fill=(255, 255, 255), anchor="mm")
    d.text((size / 2, size * 0.88), a_txt,
           font=fit(a_txt, 0.035), fill=(160, 175, 200), anchor="mm")
    return cover


def make_background(cover, w, h):
    """Blurred, darkened, cover-filled background."""
    scale = max(w / cover.width, h / cover.height) * 1.15
    big = cover.resize((int(cover.width * scale) + 2, int(cover.height * scale) + 2),
                       Image.LANCZOS)
    left = (big.width - w) // 2
    top = (big.height - h) // 2
    bg = big.crop((left, top, left + w, top + h))
    bg = bg.filter(ImageFilter.GaussianBlur(max(18, w // 42)))
    return Image.blend(bg, Image.new("RGB", (w, h), (10, 11, 16)), 0.62)


# --------------------------------------------------------------------------- #
# renderer
# --------------------------------------------------------------------------- #
class Renderer:
    def __init__(self, args, lines, cover):
        self.w, self.h = args.width, args.height
        self.fps = args.fps
        self.total = args.total or audio_duration(args.audio) or lines[-1][1]
        self.title, self.artist = args.title, args.artist
        self.args = args
        self.cover = cover
        self.s = self.w / 1920.0                      # scale factor vs 1080p design
        self.bg = make_background(cover, self.w, self.h)

        # card geometry (design units are for a 1920x1080 canvas)
        self.card_x = int(140 * self.s)
        self.card_y = int(110 * self.s)
        self.card = int(620 * self.s)

        self.f_title = load_font(int(38 * self.s), bold=True, font_path=args.font_bold)
        self.f_artist = load_font(int(28 * self.s), font_path=args.font)
        self.f_time = load_font(int(20 * self.s), font_path=args.font)

        # lyric sequence with "..." separators for instrumental gaps
        self.seq = []
        for i, (st, en, txt) in enumerate(lines):
            if self.seq and st - self.seq[-1][2] > args.gap:
                self.seq.append(("...", self.seq[-1][2] + 0.6, self.seq[-1][2] + 1.2))
            self.seq.append((txt, st, en))

    # ---- timeline helpers ----
    def current_index(self, t):
        for i, (_, st, en) in enumerate(self.seq):
            if st <= t <= en:
                return i
        for i, (_, st, _en) in enumerate(self.seq):
            if st > t:
                return i
        return len(self.seq) - 1

    def rounded(self, img, box, radius, fill):
        ImageDraw.Draw(img).rounded_rectangle(box, radius=radius, fill=fill)

    # ---- one frame ----
    def frame(self, t):
        w, h, s = self.w, self.h, self.s
        img = self.bg.copy()

        # card with soft shadow
        shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle(
            [self.card_x - int(8 * s), self.card_y + int(10 * s),
             self.card_x + self.card + int(8 * s), self.card_y + self.card + int(26 * s)],
            radius=int(26 * s), fill=(0, 0, 0, 120))
        shadow = shadow.filter(ImageFilter.GaussianBlur(int(18 * s)))
        img = Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB")

        self.rounded(img, [self.card_x, self.card_y,
                           self.card_x + self.card, self.card_y + self.card],
                     int(20 * s), (20, 22, 30))
        art = self.cover.resize((self.card, self.card), Image.LANCZOS)
        mask = Image.new("L", (self.card, self.card), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, self.card, self.card],
                                               radius=int(20 * s), fill=255)
        img.paste(art, (self.card_x, self.card_y), mask)
        d = ImageDraw.Draw(img)

        # title / artist / icons
        ty = self.card_y + self.card + int(42 * s)
        d.text((self.card_x, ty), self.title, font=self.f_title, fill=(255, 255, 255))
        d.text((self.card_x, ty + int(52 * s)), self.artist,
               font=self.f_artist, fill=(150, 152, 162))

        ix = self.card_x + self.card - int(26 * s)
        iy = ty + int(16 * s)
        for k in range(3):
            r = int(3.5 * s)
            cy = iy + (k - 1) * int(13 * s)
            d.ellipse([ix - r, cy - r, ix + r, cy + r], fill=(200, 200, 208))
        sx = ix - int(54 * s)
        pts = []
        for k in range(10):
            ang = -math.pi / 2 + k * math.pi / 5
            rad = (15 if k % 2 == 0 else 6.5) * s
            pts.append((sx + rad * math.cos(ang), iy + rad * math.sin(ang)))
        d.polygon(pts, outline=(200, 200, 208), width=max(1, int(2 * s)))

        # progress bar
        py = ty + int(132 * s)
        d.line([(self.card_x, py), (self.card_x + self.card, py)],
               fill=(90, 92, 100), width=max(2, int(4 * s)))
        frac = min(max(t / self.total, 0.0), 1.0) if self.total else 0.0
        px = self.card_x + int(self.card * frac)
        d.line([(self.card_x, py), (px, py)], fill=(255, 255, 255), width=max(2, int(4 * s)))
        knob = int(6 * s)
        d.ellipse([px - knob, py - knob, px + knob, py + knob], fill=(255, 255, 255))
        d.text((self.card_x, py + int(18 * s)), fmt_clock(t),
               font=self.f_time, fill=(140, 142, 152))
        d.text((self.card_x + self.card, py + int(18 * s)),
               "-" + fmt_clock(self.total - t), font=self.f_time,
               fill=(140, 142, 152), anchor="ra")

        # lyrics
        cx = int(1390 * s)
        base_y = int(500 * s)
        max_w = int(860 * s)
        ci = self.current_index(t)
        for off in range(-2, 4):
            j = ci + off
            if not (0 <= j < len(self.seq)):
                continue
            txt = self.seq[j][0]
            active = off == 0
            size = int((50 if active else 42) * s)
            font = load_font(size, bold=active,
                             font_path=self.args.font_bold if active else self.args.font)
            while font.getlength(txt) > max_w and size > int(22 * s):
                size -= max(1, int(2 * s))
                font = load_font(size, bold=active,
                                 font_path=self.args.font_bold if active else self.args.font)
            colour = (255, 255, 255) if active else (128, 130, 142)
            d.text((cx, base_y + off * int(92 * s)), txt,
                   font=font, fill=colour, anchor="mm")
        return img


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Spotify-style lyric video generator")
    ap.add_argument("--audio", required=True, help="song file (mp3/m4a/wav)")
    ap.add_argument("--lyrics", required=True, help=".srt or .lrc file")
    ap.add_argument("--cover", help="album art image (optional)")
    ap.add_argument("--title", default="Song Title")
    ap.add_argument("--artist", default="Artist")
    ap.add_argument("--out", default="lyric_video.mp4")
    ap.add_argument("--start", type=float, default=0.0, help="start time in seconds")
    ap.add_argument("--duration", type=float, default=None, help="length in seconds (default: whole song)")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--gap", type=float, default=2.5,
                    help="insert '...' when the gap between lines exceeds this (seconds)")
    ap.add_argument("--font", help="path to a regular .ttf")
    ap.add_argument("--font-bold", dest="font_bold", help="path to a bold .ttf")
    args = ap.parse_args()

    lines = parse_lyrics(args.lyrics)
    if not lines:
        sys.exit("No lyrics cues found in %s" % args.lyrics)

    total = audio_duration(args.audio)
    args.total = total or lines[-1][1]
    end = args.start + (args.duration if args.duration else max(0.0, args.total - args.start))

    if args.cover:
        cover = Image.open(args.cover).convert("RGB")
    else:
        cover = make_placeholder_cover(900, args.title, args.artist)

    r = Renderer(args, lines, cover)

    ff = ffmpeg_exe()
    tmp_audio = "_lyric_audio.wav"
    subprocess.run([ff, "-y", "-ss", str(args.start), "-t", str(end - args.start),
                    "-i", args.audio, "-ac", "2", "-ar", "44100", tmp_audio],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    cmd = [ff, "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{args.width}x{args.height}", "-r", str(args.fps), "-i", "-",
           "-i", tmp_audio,
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-threads", "2",
           "-c:a", "aac", "-b:a", "192k", "-shortest", args.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    frames = int(round((end - args.start) * args.fps))
    for i in range(frames):
        proc.stdin.write(r.frame(args.start + i / args.fps).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit(proc.stderr.read().decode()[-1500:])

    try:
        os.remove(tmp_audio)
    except OSError:
        pass
    print(f"done: {args.out}  ({frames} frames, {frames / args.fps:.1f}s)")


if __name__ == "__main__":
    main()
