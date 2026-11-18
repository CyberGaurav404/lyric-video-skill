#!/usr/bin/env python3
"""
auto_srt.py — build a timed .srt from an audio file and (optionally) plain lyrics text.

The agent never needs a hand-made SRT: give it the song and the lyrics text (typos are
fine) and this script produces the timings.

    python auto_srt.py --audio song.mp3 --lyrics lyrics.txt --out song.srt
    python auto_srt.py --audio song.mp3 --out song.srt          # no lyrics -> ASR text

How it works
  1. Speech recognition with Vosk (fast, offline) — the lyrics text, when supplied, is
     also fed in as a grammar so the recognizer prefers the words you actually wrote.
  2. Your lyric lines are aligned to the recognised words with fuzzy matching, so
     spelling mistakes, missing punctuation and small word differences still line up.
  3. Unmatched words get timings interpolated between their matched neighbours.
  4. One SRT cue per lyric line: start = first word, end = last word.

Requires: pip install vosk        (model downloads automatically on first run)
Optional: pip install av          (audio decode; otherwise ffmpeg is used)
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import urllib.request
import zipfile
from difflib import SequenceMatcher

MODELS = {
    "hi": ("vosk-model-small-hi-0.22", "https://alphacephei.com/vosk/models/vosk-model-small-hi-0.22.zip"),
    "en": ("vosk-model-small-en-us-0.15", "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"),
}


# --------------------------------------------------------------------------- #
# audio
# --------------------------------------------------------------------------- #
def ffmpeg_exe():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def audio_to_pcm(path, sr=16000):
    """Decode any audio file to raw 16 kHz mono s16 PCM bytes."""
    tmp = tempfile.NamedTemporaryFile(suffix=".raw", delete=False).name
    subprocess.run([ffmpeg_exe(), "-y", "-i", path, "-ac", "1", "-ar", str(sr),
                    "-f", "s16le", tmp],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    data = open(tmp, "rb").read()
    os.unlink(tmp)
    return data, sr


# --------------------------------------------------------------------------- #
# model
# --------------------------------------------------------------------------- #
def get_model(lang, cache_dir="models"):
    from vosk import Model
    name, url = MODELS.get(lang, MODELS["en"])
    target = os.path.join(cache_dir, name)
    if not os.path.isdir(target):
        os.makedirs(cache_dir, exist_ok=True)
        zip_path = os.path.join(cache_dir, name + ".zip")
        print(f"downloading speech model ({name}) ...", flush=True)
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(cache_dir)
        os.unlink(zip_path)
    return Model(target)


# --------------------------------------------------------------------------- #
# normalisation (tolerates typos / punctuation differences)
# --------------------------------------------------------------------------- #
def norm(tok):
    tok = unicodedata.normalize("NFC", tok).replace("\u093c", "").replace("\u200d", "")
    tok = re.sub(r"[।,.?!;:\"'’‘“”\-—()\[\]]", "", tok)
    return tok.strip().lower()


def similar(a, b):
    if a == b:
        return True
    if not a or not b:
        return False
    if a.startswith(b) or b.startswith(a):
        return True
    return SequenceMatcher(None, a, b).ratio() >= 0.62


# --------------------------------------------------------------------------- #
# recognition
# --------------------------------------------------------------------------- #
def recognise(pcm, sr, model, grammar_words=None):
    from vosk import KaldiRecognizer, SetLogLevel
    SetLogLevel(-1)
    rec = KaldiRecognizer(model, sr)
    rec.SetWords(True)
    if grammar_words:
        # constrained decoding: only the words the user actually wrote
        try:
            rec.SetGrammar(json.dumps(grammar_words, ensure_ascii=False))
        except Exception:
            pass
    words = []
    step = 8000
    for i in range(0, len(pcm), step):
        if rec.AcceptWaveform(pcm[i:i + step]):
            words += json.loads(rec.Result()).get("result", [])
    words += json.loads(rec.FinalResult()).get("result", [])
    return [{"w": w["word"], "s": float(w["start"]), "e": float(w["end"])} for w in words]


# --------------------------------------------------------------------------- #
# alignment
# --------------------------------------------------------------------------- #
def align(lines, asr_words):
    """lines: list of raw text lines. asr_words: [{'w','s','e'}]. -> list of word dicts per line."""
    flat = [(li, tok) for li, line in enumerate(lines) for tok in line.split()]
    canon = [norm(t) for _, t in flat]
    heard = [norm(w["w"]) for w in asr_words]

    times = [None] * len(canon)
    sm = SequenceMatcher(None, canon, heard, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                times[i1 + k] = (asr_words[j1 + k]["s"], asr_words[j1 + k]["e"])

    # second pass: fuzzy fill for near-miss blocks
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "delete") and (i2 - i1) and (j2 - j1):
            for k in range(min(i2 - i1, j2 - j1)):
                if times[i1 + k] is None and similar(canon[i1 + k], heard[j1 + k]):
                    times[i1 + k] = (asr_words[j1 + k]["s"], asr_words[j1 + k]["e"])

    # interpolate the rest
    n = len(canon)
    i = 0
    while i < n:
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < n and times[j] is None:
            j += 1
        prev = times[i - 1][1] if i > 0 else (asr_words[0]["s"] if asr_words else 0.0)
        nxt = times[j][0] if j < n else prev + 0.45 * (j - i)
        span = max(nxt - prev, 0.16 * (j - i))
        weights = [max(len(canon[k]), 2) for k in range(i, j)]
        total = sum(weights)
        t = prev
        for k in range(i, j):
            d = span * weights[k - i] / total
            times[k] = (t, t + d)
            t += d
        i = j

    out, idx = [], 0
    for li, line in enumerate(lines):
        n_tok = len(line.split())
        out.append([{"w": tok, "s": round(times[idx + k][0], 3), "e": round(times[idx + k][1], 3)}
                    for k, tok in enumerate(line.split())])
        idx += n_tok
    return out


def cues_from_asr(asr_words, max_words=6, max_gap=0.7):
    """No lyrics supplied: chop the recognised stream into readable cues."""
    cues, cur = [], []
    for w in asr_words:
        if cur and (len(cur) >= max_words or w["s"] - cur[-1]["e"] > max_gap):
            cues.append(cur)
            cur = []
        cur.append(w)
    if cur:
        cues.append(cur)
    return cues


# --------------------------------------------------------------------------- #
# srt
# --------------------------------------------------------------------------- #
def ts(sec):
    h, rem = divmod(max(sec, 0), 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"


def write_srt(cues, path):
    out = []
    for i, cue in enumerate(cues, 1):
        if not cue:
            continue
        text = " ".join(w["w"] for w in cue)
        out += [str(i), f"{ts(cue[0]['s'])} --> {ts(cue[-1]['e'])}", text, ""]
    open(path, "w", encoding="utf-8").write("\n".join(out))
    return len(out) // 4


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="audio (+ lyrics text) -> timed .srt")
    ap.add_argument("--audio", required=True)
    ap.add_argument("--lyrics", help="plain text file, one lyric line per line (typos ok)")
    ap.add_argument("--out", default="lyrics.srt")
    ap.add_argument("--lang", default="hi", choices=sorted(MODELS))
    ap.add_argument("--model-dir", default="models")
    args = ap.parse_args()

    lines = []
    if args.lyrics:
        lines = [l.strip() for l in open(args.lyrics, encoding="utf-8-sig").read().splitlines() if l.strip()]

    pcm, sr = audio_to_pcm(args.audio)
    model = get_model(args.lang, args.model_dir)

    grammar = None
    if lines:
        seen, grammar = set(), []
        for line in lines:
            clause = re.sub(r"[।,.?!]+$", "", line).strip()
            if clause and clause not in seen:
                seen.add(clause)
                grammar.append(clause)

    words = recognise(pcm, sr, model, grammar)
    print(f"recognised {len(words)} words", flush=True)
    if not words:
        sys.exit("no speech recognised — try another --lang or pass --lyrics")

    if lines:
        cues = align(lines, words)
    else:
        cues = cues_from_asr(words)

    n = write_srt(cues, args.out)
    print(f"wrote {n} cues -> {args.out}")


if __name__ == "__main__":
    main()
