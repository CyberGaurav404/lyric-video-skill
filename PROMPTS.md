# Copy-paste prompts

## A. One-shot (this repo attached)

```
Is repo ke scripts/make_video.py se lyric video banao — mujhe SRT nahi dena hai,
tum khud timings nikaal lo.

Attached: song.mp3, cover.png, lyrics.txt (isme spelling mistakes ho sakti hain,
fuzzy alignment handle kar lega).

Full song, Spotify style, 1920x1080, 30fps:
python scripts/make_video.py --audio song.mp3 --cover cover.png --lyrics lyrics.txt \
    --title "<song>" --artist "<artist>" --style spotify --out video.mp4

Deliver: video.mp4 + ek 20s teaser (--start <chorus time> --duration 20).
Render se pehle 2-3 frames nikaal ke check karo ki text clip nahi ho raha aur
font sahi hai (Devanagari ke liye assets/fonts use karo).
```

## B. Spotify style from scratch (no repo)

```
Spotify app ke full-screen "lyrics" view jaisa lyric video banao. 1920x1080, 30fps.

Background: cover 1.25x, 58px blur, 66% dark overlay (#08090E).
Left: 600x600 rounded album card at (150,120) radius 18 + soft shadow; bold 40px white
title, 30px #9698A4 artist, star + 3-dot icons; progress bar (track #50525C 4px,
fill #F0C05A, 12px knob) with "0:42" left and "-2:03" right in 21px #9698A2.
Right: lyrics column centre x=1370, active line y=520 — active 54px bold white,
±1 42px #9698A4, ±2 38px #696A76, ±3 34px #484954, spacing 104px.
Motion: continuous eased scroll, scroll = (i-1) + smoothstep((t - lineStart + 0.30)/0.60).

Timings: main sirf audio + lyrics text dunga — tum khud ASR (vosk/whisper) se word timings
nikaalo, lyrics ko fuzzy-align karo (typos allowed), aur SRT bana lo. SRT mujhse mat maango.
Output: full song ka mp4 + 20s teaser.
```

## C. Cinematic motivational (Kalam font, word highlight)

```
Cinematic motivational lyric video — full-bleed background, background mein koi text/logo
nahi, sirf lyrics. 1920x1080, 30fps, 2.35:1 letterbox bars har frame par.

Background: dramatic cinematic plate (silhouette figure + broken pocket watch + sparks +
rain, orange rim light, no text). Figma generate_image (2048x1152) se banao, phir
bloom + teal-orange grade + vignette bake karo.
Camera: continuous slow push-in (1.00 -> 1.14) + halka drift, per-frame interpolated.
Lyrics: Kalam Bold, white, neeche-center (~y=852), slide-up + fade entry,
word-by-word gold highlight (#F5C06E), lambi lines auto-shrink.

Timings khud nikaalo (audio + lyrics text se), SRT mat maango.
```

## D. Vertical reels

```
Wahi style, lekin 1080x1920 vertical: card/top area upar, lyrics neeche-center,
progress sabse neeche. Baaki sab same.
```

## E. Cover art only

```
Is gaane ke liye 1000x1000 album cover banao — cinematic, minimal, sirf title + artist
typography. Deliver PNG.
```
