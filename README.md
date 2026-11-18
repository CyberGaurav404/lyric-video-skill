# lyric-video-skill

Turn **a song + a cover image + lyrics text** into a finished lyric video.
No SRT needed — timings are generated automatically, and typos in the lyrics are tolerated.

| Spotify "now playing" | Cinematic motivational |
|---|---|
| ![Spotify style](docs/preview-spotify.jpg) | ![Cinematic style](docs/preview-cinematic.jpg) |

---

## Quick start

```bash
git clone https://github.com/CyberGaurav404/lyric-video-skill
cd lyric-video-skill
pip install pillow imageio-ffmpeg vosk     # ffmpeg ships with imageio-ffmpeg

python scripts/make_video.py \
    --audio song.mp3 \
    --cover cover.png \
    --lyrics lyrics.txt \
    --title "Song Name" --artist "Artist Name" \
    --style spotify \
    --out lyric_video.mp4
```

One command does everything: speech recognition → alignment with your lyrics → SRT →
chunked render → concatenation → `lyric_video.mp4`.

### Common variants

```bash
# 20 second teaser
python scripts/make_video.py --audio song.mp3 --cover art.png --lyrics lyrics.txt \
    --start 9.6 --duration 20 --out teaser.mp4

# cinematic style with your own background plate (no text in it)
python scripts/make_video.py --audio song.mp3 --cover art.png --lyrics lyrics.txt \
    --style cinematic --bg plate.png --out video.mp4

# no lyrics file at all — the recogniser writes the text too
python scripts/make_video.py --audio song.mp3 --cover art.png --out video.mp4

# English song
python scripts/make_video.py --audio song.mp3 --cover art.png --lyrics lyrics.txt --lang en
```

---

## Why no SRT?

Hand-timed subtitles are the slowest part of making a lyric video, and agents usually
cannot ask the user to produce them. `scripts/auto_srt.py` closes that gap:

1. **Offline ASR (Vosk)** — fast, no GPU, ~40–80 MB model downloaded once.
2. **Grammar hint** — when lyrics text exists, its lines are fed to the recogniser as a
   grammar, so it prefers the words you actually wrote.
3. **Fuzzy alignment** — both sides are normalised (punctuation, nukta, case) and matched
   with `difflib` plus a similarity ratio, so `कोलम्बस`/`कोलंबस` or `आईंस्टीन`/`आइंस्टाइन`
   still line up.
4. **Interpolation** — anything still unmatched is spread proportionally between its
   matched neighbours, so timing never collapses.
5. **One cue per lyric line** — start = first word, end = last word.

Want the SRT on its own?

```bash
python scripts/auto_srt.py --audio song.mp3 --lyrics lyrics.txt --out song.srt --lang hi
```

---

## What's inside

```
SKILL.md                     agent-facing skill definition (when/how to use)
README.md                    this file
PROMPTS.md                   copy-paste prompts for new chats
briefs/Lyric_Video_Brief.md  design spec + self-contained renderer
scripts/
  make_video.py              end-to-end orchestrator (audio+cover+lyrics -> mp4)
  auto_srt.py                audio (+ lyrics text) -> timed .srt
  spotify_lyrics.py          Spotify "now playing" renderer
  motivational_render.py     cinematic renderer (Kalam font, word highlight)
  cover_art.py               procedural album cover (--title/--artist/--out)
  gen_bg2.py                 procedural cinematic background
  bake_bg.py                 bloom + teal-orange grade + vignette
assets/
  fonts/                     Kalam Bold + Noto Sans Devanagari (Bold/Regular)
  The_Spectre_Cover_Art.png  sample cover
  Motivational_Background.png sample plate
examples/                    sample SRTs + a lyrics .txt
docs/                        preview frames
```

---

## Design tokens (Spotify style)

| Element | Value |
|---|---|
| Canvas | 1920×1080, 30 fps, h264 CRF 19, AAC 192k |
| Background | cover 1.25×, 58 px blur, 66% dark overlay |
| Album card | 600×600 at (150,120), radius 18, shadow blur 22 |
| Title / artist | bold 40 px white / 30 px `#9698A4` |
| Progress | track `#50525C` 4 px, fill `#F0C05A`, knob 12 px |
| Lyrics | column x=1370, active line y=520 |
| Type scale | active 54 px bold, ±1 42, ±2 38, ±3 34; spacing 104 px |
| Scroll | `scroll = (i-1) + smoothstep((t - lineStart + 0.30)/0.60)` |

Cinematic style: full-bleed plate, 2.35:1 bars, bloom/halation, teal-orange grade,
slow continuous push-in, lyrics bottom-centre in Kalam Bold with word-by-word gold highlight.

---

## Requirements & performance

- Python 3.10+, `pillow`, `imageio-ffmpeg`, `vosk` (system `ffmpeg` also works)
- Rendering is CPU-bound: ~1.7 s of render time per second of video at 1080p30 on two
  cores; `make_video.py` chunks automatically to stay under 2 GB RAM.
- First run downloads the speech model into `models/` (git-ignored).

## License

MIT — see [LICENSE](LICENSE).
