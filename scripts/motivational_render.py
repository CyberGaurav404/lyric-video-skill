import sys, math, subprocess
"""
motivational_render.py — cinematic "motivational" lyric video (Kalam font, word highlight).

Config (edit these three lines):
    SRC      = audio file
    SRT      = lyrics with timings (.srt)
    BG_IMG   = background plate (photo/illustration, no text)

Usage:
    python motivational_render.py <start> <end> <out.mp4>
    e.g. python motivational_render.py 0 45 part1.mp4      # chunked
         ffmpeg -f concat -safe 0 -i parts.txt -c copy full.mp4

If a word-level JSON is not available, word timings are derived from the SRT by
splitting each line's duration across its words (proportional to word length).
"""
import os, json, re

SRC = os.environ.get("SRC", "/scratch/input/song.mp3")
SRT = os.environ.get("SRT", "lyrics.srt")
BG_IMG = os.environ.get("BG_IMG", "bg_baked.png")
TOTAL = float(os.environ.get("TOTAL", "0")) or None

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio_ffmpeg

W, H, FPS = 1920, 1080, 30
BARS = 92                      # cinematic letterbox bars
GOLD = (245, 200, 110)

def _ts(x):
    x = x.strip().replace(',', '.')
    h, m, sec = x.split(':')
    return int(h) * 3600 + int(m) * 60 + float(sec)


def load_lines(srt_path):
    """SRT -> list of lines, each a list of {w, s, e} word dicts."""
    raw = open(srt_path, encoding='utf-8-sig').read().replace('\r\n', '\n')
    out = []
    for blk in re.split(r'\n\s*\n', raw.strip()):
        rows = [r for r in blk.split('\n') if r.strip()]
        idx = 1 if rows and re.fullmatch(r'\d+', rows[0].strip()) else 0
        if len(rows) <= idx or '-->' not in rows[idx]:
            continue
        a, b = rows[idx].split('-->')
        text = ' '.join(r.strip() for r in rows[idx + 1:]).strip()
        if not text:
            continue
        start, end = _ts(a), _ts(b)
        toks = text.split()
        weights = [max(len(t), 2) for t in toks]
        span = max(end - start, 0.25 * len(toks))
        t = start
        ws = []
        for tok, wgt in zip(toks, weights):
            d = span * wgt / sum(weights)
            ws.append({'w': tok, 's': t, 'e': t + d})
            t += d
        out.append(ws)
    return out


sents = load_lines(SRT)
if TOTAL is None:
    TOTAL = sents[-1][-1]['e'] if sents else 1.0

# ---- smooth camera move: interpolate between small pre-rendered frames ----
SRC_IMG = Image.open(BG_IMG).convert('RGB')
NV = 60                      # keyframes across the whole clip
SW, SH = 960, 540            # small size -> cheap blends
ZOOM0, ZOOM1 = 1.0, 1.14
VAR = []
for i in range(NV + 1):
    p = i / NV
    z = ZOOM0 + (ZOOM1 - ZOOM0) * p
    cw, ch = int(W / z), int(H / z)
    cx = W / 2 + math.sin(p * 6.0) * 26
    cy = H / 2 + math.cos(p * 5.0) * 18
    x0 = int(min(max(cx - cw / 2, 0), W - cw))
    y0 = int(min(max(cy - ch / 2, 0), H - ch))
    VAR.append(SRC_IMG.crop((x0, y0, x0 + cw, y0 + ch)).resize((SW, SH), Image.BILINEAR))

_HERE = os.path.dirname(os.path.abspath(__file__))
_FONT_CANDIDATES = [
    os.environ.get("FONT", ""),
    os.path.join(_HERE, "..", "assets", "fonts", "Kalam-Bold.ttf"),
    os.path.join(_HERE, "fonts", "Kalam-Bold.ttf"),
    "/usr/share/fonts/truetype/kalam/Kalam-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
FONT_PATH = next((p for p in _FONT_CANDIDATES if p and os.path.exists(p)), None)
if FONT_PATH is None:
    raise SystemExit("Kalam font not found - put Kalam-Bold.ttf in assets/fonts/ or set FONT=/path/to/font.ttf")

FB = lambda s: ImageFont.truetype(FONT_PATH, s)
MAXW = 1620
_C = {}
def fit(text, start=80, lo=42):
    size = start
    f = FB(size)
    while f.getlength(text) > MAXW and size > lo:
        size -= 2
        f = FB(size)
    return size, f

def tile(text, colour, size, fnt):
    k = (text, colour, size)
    t = _C.get(k)
    if t is None:
        pad = 18
        wpx = int(fnt.getlength(text)) + pad*2
        asc, desc = fnt.getmetrics()
        im = Image.new('RGBA', (max(wpx, 1), asc + desc + pad*2), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.text((pad+3, pad+4), text, font=fnt, fill=(0, 0, 0, 220))
        d.text((pad, pad), text, font=fnt, fill=colour + (255,))
        t = (im, pad)
        _C[k] = t
    return t

def active(t):
    for i, s in enumerate(sents):
        if s[0]['s'] <= t <= s[-1]['e']:
            return i
    for i, s in enumerate(sents):
        if s[0]['s'] > t:
            return i
    return len(sents)-1

def cam(t):
    pos = min(max(t / TOTAL, 0.0), 1.0) * NV
    i = int(pos)
    f = pos - i
    a = VAR[min(i, NV)]
    b = VAR[min(i + 1, NV)]
    im = Image.blend(a, b, f) if f > 0.01 else a
    return im.resize((W, H), Image.BILINEAR)

def frame(t):
    img = cam(t)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, BARS], fill=(0, 0, 0))
    d.rectangle([0, H - BARS, W, H], fill=(0, 0, 0))
    idx = active(t)
    s = sents[idx]
    start, end = s[0]['s'], s[-1]['e']
    nxt = sents[idx+1][0]['s'] if idx+1 < len(sents) else TOTAL

    # fade in / out
    fin = min(max((t - start) / 0.30, 0.0), 1.0)
    fout = 1.0
    if t > end and nxt - end > 3.0:
        fout = max(0.0, 1.0 - (t - end) / 1.0)
    alpha = fin * fout
    if alpha <= 0.02:
        return img

    # build the line as words with per-word colour
    parts = []
    for w in s:
        if t >= w['e']:
            col = (255, 255, 255)
        elif t >= w['s']:
            col = GOLD
        else:
            col = (176, 176, 186)
        parts.append((w['w'], col))

    text = ' '.join(p[0] for p in parts)
    size, fnt = fit(text)
    total_w = fnt.getlength(text)
    x = (W - total_w) / 2
    y = 852 - size * 0.55 - int((1 - fin) * 26)          # slide-up on entry
    for wtext, col in parts:
        scaled = tuple(int(c * (0.45 + 0.55 * alpha)) for c in col)
        tm, pad = tile(wtext, scaled, size, fnt)
        img.paste(tm, (int(x) - pad, int(y) - pad), tm)
        x += fnt.getlength(wtext + ' ')

    return img

a0, a1, out = float(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
ff = imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run([ff, '-y', '-ss', str(a0), '-t', str(a1-a0), '-i', SRC, '-ac', '2', '-ar', '44100', 'm2.wav'],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
cmd = [ff, '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
       '-i', 'm2.wav', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '21',
       '-x264-params', 'rc-lookahead=4:sync-lookahead=0', '-pix_fmt', 'yuv420p', '-threads', '2',
       '-c:a', 'aac', '-b:a', '192k', '-shortest', out]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=open(out+'.log','wb'))
for i in range(int(round((a1-a0)*FPS))):
    p.stdin.write(frame(a0 + i/FPS).tobytes())
p.stdin.close()
print(out, 'rc', p.wait())
