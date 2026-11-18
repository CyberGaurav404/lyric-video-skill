# Lyric Video Kit — Spotify style + Cinematic motivational style

Sab kuch isi folder mein hai: renderer scripts, design spec, prompts, sample assets,
aur step-by-step instructions. Kisi bhi chat mein ye folder bhej do aur bolo
"is kit se video banao" — kaam ho jayega.

---

## 1. Folder map

```
lyric_video_kit/
├── README.md                  ← ye file (setup + how-to)
├── PROMPTS.md                 ← copy-paste prompts (nayi chat ke liye)
├── requirements.txt
├── briefs/
│   └── Lyric_Video_Brief.md   ← full design spec + code (Spotify style)
├── scripts/
│   ├── spotify_lyrics.py          ← Spotify "now playing" style renderer (CLI)
│   ├── spotify_lyric_video.py     ← purana simple version (line-by-line, no scroll)
│   ├── motivational_render.py     ← cinematic style, Kalam font, word highlight
│   ├── cover_art.py               ← procedural album cover (Figma na ho to)
│   ├── gen_bg2.py                 ← procedural cinematic background
│   └── bake_bg.py                 ← bloom + teal-orange grade + vignette bake
├── assets/
│   ├── The_Spectre_Cover_Art.png  ← sample cover (1000x1000)
│   ├── Motivational_Background.png← sample cinematic plate (16:9)
│   └── fonts/Kalam-Bold.ttf       ← Hindi handwriting font (motivational style)
└── examples/
    ├── The_Spectre_Lyrics.srt     ← English sample SRT
    └── GodMode_Lyrics.srt         ← Hindi sample SRT
```

---

## 2. Install (ek baar)

```bash
pip install pillow imageio-ffmpeg
# optional but recommended (audio decode / duration):
pip install av
```

ffmpeg alag se install karne ki zaroorat nahi — `imageio-ffmpeg` apna binary laata hai.

---

## 3. Style A — Spotify "now playing" lyric video

**Kya chahiye:** gaana (mp3/m4a), cover (square ≥1000px), lyrics `.srt`.

```bash
python scripts/spotify_lyrics.py \
    --audio song.mp3 \
    --srt lyrics.srt \
    --cover cover.png \
    --title "Song (Nightcore)" \
    --artist "Artist Name" \
    --out lyric_video.mp4
```

20 second teaser (9.6s se):

```bash
python scripts/spotify_lyrics.py --audio song.mp3 --srt lyrics.srt --cover cover.png \
    --title "Song" --artist "Artist" --start 9.6 --duration 20 --out teaser.mp4
```

Lambe gaane chunk mein render karo (2 GB RAM par 45s se bada chunk mat rakho):

```bash
python scripts/spotify_lyrics.py ... --start 0   --duration 45 --out p1.mp4
python scripts/spotify_lyrics.py ... --start 45  --duration 45 --out p2.mp4
python scripts/spotify_lyrics.py ... --start 90  --duration 45 --out p3.mp4
python scripts/spotify_lyrics.py ... --start 135 --duration 30 --out p4.mp4

printf "file 'p1.mp4'\nfile 'p2.mp4'\nfile 'p3.mp4'\nfile 'p4.mp4'\n" > parts.txt
ffmpeg -f concat -safe 0 -i parts.txt -c copy full.mp4
```

**Design (yaad rakhna):** 1920x1080 / 30fps · card 600x600 at (150,120) radius 18 ·
title bold 40px white, artist 30px #9698A4 · progress track #50525C 4px, fill gold #F0C05A ·
lyrics column x=1370, active line y=520 · active 54px bold white, ±1 42px #9698A4,
±2 38px #696A76, ±3 34px #484954 · spacing 104px ·
scroll = `(i-1) + smoothstep((t - lineStart + 0.30)/0.60)` (continuous, jump nahi).

---

## 4. Style B — Cinematic motivational (Kalam font, word highlight)

**Kya chahiye:** gaana, lyrics `.srt`, ek cinematic background plate (photo/illustration,
**usme koi text na ho**).

Background banao (do raste):

1. **AI image (best):** Figma MCP ka `generate_image` — prompt example `PROMPTS.md` mein hai.
   16:9, 2048x1152 maango, aur prompt ke end mein `no text, no letters, no watermark` likho.
2. **Procedural:** `python scripts/gen_bg2.py` → `bg_motiv.png` (glow + rain + embers).

Phir grade/bloom bake karo (recommended):

```bash
# bake_bg.py ko edit karo ya bg file ka naam badal do, phir:
python scripts/bake_bg.py     # bg_cine.png -> bg_baked.png
```

Render:

```bash
export SRC=song.mp3
export SRT=lyrics.srt
export BG_IMG=bg_baked.png
export TOTAL=215.6            # gaane ki duration (seconds)

python scripts/motivational_render.py 0 45 p1.mp4
python scripts/motivational_render.py 45 90 p2.mp4
# ... aur aage

printf "file 'p1.mp4'\nfile 'p2.mp4'\n" > parts.txt
ffmpeg -f concat -safe 0 -i parts.txt -c copy full.mp4
```

Kya-kya milta hai: slow continuous camera (push-in + drift, interpolated — koi jump nahi),
2.35:1 letterbox bars (har frame par consistent), bloom/halation, teal-orange grade, vignette,
lyrics neeche-center mein Kalam Bold, line entry par slide-up + fade, aur **word-by-word
highlight** (bola ja raha shabd gold #F5C06E, ho chuka white, aane wala grey).

---

## 5. Lyrics + timing (SRT) kaise banao

SRT format:

```
1
00:00:09,600 --> 00:00:13,980
Hello, hello, can you hear me?
```

Agar SRT nahi hai:

1. **Official lyrics text** lo (user se ya verified source se). ASR ka text gaane mein galat aata hai.
2. **ASR with word timestamps:** `faster-whisper` (`word_timestamps=True`, `language="hi"`/`"en"`).
   2 GB RAM par 10s se bade chunk `mkl_malloc` error dete hain — 8–10s chunks mein todo, offset add karo.
3. **Align:** official words vs ASR words par `difflib.SequenceMatcher` (lowercase, punctuation strip).
   Match hue words ko ASR timing, baaki ko aage-peeche ke matched words ke beech proportionally baant do.
4. Line start = pehla word, end = aakhri word. ±0.2–0.4s tolerance normal hai.
5. Instrumental gap 6s se zyada ho to lyrics fade kar do — blank text mat chhodo.

---

## 6. Cover art

**Figma route (credits lagte hain):**
1. `whoami` → `planKey`
2. `create_new_file` (design)
3. `generate_vector_illustration` (1000x1000) ya `generate_image` (raster, zyada cinematic)
4. `use_figma` se compose: frame → illustration → gradient scrim → title (Inter Bold, letterspacing 7)
   → gold accent bar → subtitle
5. `get_screenshot` (1000x1000) → PNG

**Procedural fallback:** `python scripts/cover_art.py` → `cover_spectre.png`
(rings + glow + grain + typography; text `cover_art.py` ke neeche badal sakte ho).

---

## 7. QA checklist (deliver se pehle)

- [ ] duration = audio duration (±0.1s), 1920x1080, 30fps, audio stream maujood
- [ ] ek hi active line/word highlight, transition par jump nahi
- [ ] koi line clip nahi ho rahi (auto-shrink kaam kar raha hai)
- [ ] letterbox bars har frame par (agar use kar rahe ho)
- [ ] instrumental gap mein screen blank ya visualiser, par bars/grade consistent
- [ ] progress bar ka time = playback time, remaining sahi (`-2:33`)
- [ ] cover text card ke andar, icons title se overlap nahi

---

## 8. Troubleshooting

| Problem | Wajah | Fix |
|---|---|---|
| `mkl_malloc: failed to allocate memory` | 2 GB RAM, bada audio/model | audio 8–10s chunks, model `base`/`tiny`, ya `int8` |
| ffmpeg `Cannot allocate memory` | ek saath bahut frames | chunk 45s, `-threads 2`, `rc-lookahead=4` |
| `Kalam font not found` | font path | `assets/fonts/Kalam-Bold.ttf` rakho ya `FONT=/path` |
| Background jerky lagta hai | stepped keyframes | per-frame interpolation (kit ka code yahi karta hai) |
| Text kinare se cut | line bahut lambi | auto-shrink (`fit()` function) use karo |
| Render bahut slow | 2 core CPU | 1080p30 par ~1.7 video-sec per render-sec; chunks mein todo |

---

## 9. Speed ka andaza (2 core pod)

- 40s chunk @ 1080p30 ≈ 60–200s (content ke hisaab se)
- 3–4 minute ka gaana ≈ 5–6 chunks ≈ 15–25 min total
- 60fps karne par time double — sirf teaser ke liye karo
