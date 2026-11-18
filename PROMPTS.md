# Copy-paste prompts

## A. Spotify style (agar ye kit saath hai)

```
Is kit ke scripts/spotify_lyrics.py se Spotify "now playing" style lyric video banao.
Attached: song.mp3, cover.png, lyrics.srt.
Full song, 1920x1080, 30fps. 45 second chunks mein render karke ffmpeg se concat karo.
Same design: blurred cover background, left album card + title/artist + progress bar
(elapsed aur remaining), right side lyrics with smooth eased scroll (jump nahi),
active line white bold, ±1/±2 dim aur chhoti.
SRT ki timing use karo; na ho to audio se transcribe + align karo (official lyrics text).
Deliver: full mp4 + ek 20 second teaser (--start 9.6 --duration 20).
```

## B. Spotify style (bina kit, sirf spec se)

```
Spotify app ke full-screen "lyrics" view jaisa lyric video banao. 1920x1080, 30fps, h264+AAC.

Background: cover art 1.25x scale, 58px gaussian blur, 66% dark overlay (#08090E).
Left: 600x600 rounded album card at (150,120) radius 18 with soft shadow; neeche bold 40px
white title, 30px #9698A4 artist, star + 3-dot icons right edge; uske neeche progress bar
(track #50525C 4px, fill gold #F0C05A, 12px knob) with left elapsed "0:42" and right
remaining "-2:03" (21px #9698A2).
Right: lyrics column centre x=1370, active line y=520. Active 54px bold white, ±1 line 42px
#9698A4, ±2 38px #696A76, ±3 34px #484954, spacing 104px.
Motion: continuous eased scroll — scroll = (activeIndex-1) + smoothstep((t - lineStart + 0.30)/0.60).
Koi jump nahi.

Lyrics ke timings .srt se; na mile to audio se transcribe + word-level align karke banao
(official lyrics text use karo, ASR sirf timing ke liye).
Cover na ho to Figma se generate karke pehle dikhao.
Output: full song ka mp4 + 20s teaser. 45s chunks mein render karke concat karna.
```

## C. Cinematic motivational style (Kalam font, word highlight)

```
Cinematic motivational lyric video banao — full-bleed background, koi title/logo/text
background mein nahi, sirf lyrics.

Background: ek dramatic cinematic plate (silhouette figure + broken pocket watch + sparks +
rain, orange rim light, black shadows, no text), 16:9. Isse Figma generate_image se banao
(2048x1152), phir bloom/halation + teal-orange grade + vignette bake karo.

Render: 1920x1080, 30fps, 2.35:1 letterbox bars (har frame par consistent).
Camera: continuous slow push-in (1.00 -> 1.14) + halka drift, per-frame interpolated — jump nahi.
Lyrics: Kalam Bold, white, neeche-center (~y=852), line entry par slide-up + fade,
word-by-word highlight (bola ja raha shabd gold #F5C06E, ho chuka white, aane wala grey),
lambi lines auto-shrink.
Attached: song.mp3, lyrics.srt.
45s chunks mein render karke ffmpeg concat.
```

## D. Vertical reels version

```
Wahi style, lekin 1080x1920 vertical: card/top area upar, lyrics neeche-center,
progress bar sabse neeche. Baaki sab same (fonts, colors, motion).
```

## E. Sirf cover art

```
Is gaane ke liye 1000x1000 album cover banao — Figma mein, cinematic style,
koi text image ke andar nahi except title + artist typography.
Deliver PNG.
```
