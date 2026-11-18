#!/usr/bin/env python3
"""
make_video.py — one command, finished lyric video.

Give it an audio file, a cover image and (optionally) the lyrics as plain text.
No SRT needed: timings are generated automatically. Typos in the lyrics are fine.

    python make_video.py --audio song.mp3 --cover art.png --out video.mp4
    python make_video.py --audio song.mp3 --cover art.png --lyrics lyrics.txt \\
        --title "Song" --artist "Artist" --style spotify --out video.mp4
    python make_video.py ... --style cinematic --bg plate.png

Pipeline
  1. lyrics .srt given?  use it.
     lyrics .txt given?  -> auto_srt.py (ASR + fuzzy alignment) -> .srt
     nothing given?      -> auto_srt.py (ASR text)              -> .srt
  2. render in chunks (keeps memory low) with the chosen style
  3. concatenate chunks into the final mp4
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def sh(cmd):
    print("$", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def duration(path):
    out = subprocess.run([ffmpeg(), "-i", path], capture_output=True).stderr.decode()
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.?\d*)", out)
    if not m:
        sys.exit("could not read audio duration")
    h, mi, se = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(se)


def ensure_srt(audio, lyrics, out_srt, lang, model_dir):
    if lyrics and lyrics.lower().endswith(".srt"):
        return lyrics
    cmd = [sys.executable, os.path.join(HERE, "auto_srt.py"),
           "--audio", audio, "--out", out_srt, "--lang", lang, "--model-dir", model_dir]
    if lyrics:
        cmd += ["--lyrics", lyrics]
    sh(cmd)
    return out_srt


def ensure_cover(cover, title, out_png):
    if cover:
        return cover
    sh([sys.executable, os.path.join(HERE, "cover_art.py"), "--out", out_png,
        "--title", title])
    return out_png


def main():
    ap = argparse.ArgumentParser(description="audio + cover (+ lyrics text) -> lyric video")
    ap.add_argument("--audio", required=True)
    ap.add_argument("--cover", help="square cover image (optional; generated if missing)")
    ap.add_argument("--lyrics", help=".txt (plain lines) or .srt — optional")
    ap.add_argument("--title", default="Song Title")
    ap.add_argument("--artist", default="Artist")
    ap.add_argument("--style", default="spotify", choices=["spotify", "cinematic"])
    ap.add_argument("--bg", help="cinematic style: background plate (no text)")
    ap.add_argument("--out", default="lyric_video.mp4")
    ap.add_argument("--lang", default="hi", help="ASR language: hi or en")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--chunk", type=float, default=45.0)
    ap.add_argument("--model-dir", default="models")
    args = ap.parse_args()

    work = tempfile.mkdtemp(prefix="lyricvid_")
    try:
        total = duration(args.audio)
        end = args.start + (args.duration if args.duration else max(0.0, total - args.start))

        srt = ensure_srt(args.audio, args.lyrics, os.path.join(work, "lyrics.srt"),
                         args.lang, args.model_dir)
        cover = ensure_cover(args.cover, args.title, os.path.join(work, "cover.png"))

        parts, t = [], args.start
        i = 0
        while t < end - 0.05:
            seg = min(args.chunk, end - t)
            out = os.path.join(work, f"part{i:02d}.mp4")
            if args.style == "spotify":
                sh([sys.executable, os.path.join(HERE, "spotify_lyrics.py"),
                    "--audio", args.audio, "--srt", srt, "--cover", cover,
                    "--title", args.title, "--artist", args.artist,
                    "--start", str(t), "--duration", str(seg), "--out", out])
            else:
                bg = args.bg or os.path.join(work, "plate.png")
                if not args.bg:
                    sh([sys.executable, os.path.join(HERE, "gen_bg2.py"), "--out", bg])
                env = dict(os.environ, SRC=args.audio, SRT=srt, BG_IMG=bg, TOTAL=str(total))
                subprocess.run([sys.executable, os.path.join(HERE, "motivational_render.py"),
                                str(t), str(t + seg), out], check=True, env=env)
            parts.append(out)
            t += seg
            i += 1

        listfile = os.path.join(work, "parts.txt")
        with open(listfile, "w") as f:
            for p in parts:
                f.write(f"file '{p}'\n")
        sh([ffmpeg(), "-y", "-f", "concat", "-safe", "0", "-i", listfile,
            "-c", "copy", args.out])
        print(f"\ndone: {args.out}")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
