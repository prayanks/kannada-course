# Spoken Kannada Course

Personal course for everyday Bengaluru Kannada — Roman transliteration only, Hindi bridges, short lessons with machine-generated audio.

**Live site:** https://prayanks.github.io/kannada-course/

## Contents

- `index.html` — course home
- `lessons/` — lesson pages (HTML + embedded audio players)
- `reference/` — cheat sheets
- `assets/lesson.css` — shared styles
- `assets/audio/` — MP3 clips + `manifest.json`
- `assets/build_manifest.py` / `generate_audio.py` / `retrofit_audio.py` — regenerate audio after new lessons

## Audio

Clips are generated with Microsoft edge-tts (`kn-IN-SapnaNeural`). Each lesson labels audio as machine-generated — use neighbours’ speech as ground truth when they differ.

```bash
python3 assets/build_manifest.py
python3 assets/generate_audio.py          # skips existing files
python3 assets/retrofit_audio.py          # wire players into lesson HTML
```

## Local preview

```bash
cd kannada-course
python3 -m http.server 8788 --bind 127.0.0.1
# open http://127.0.0.1:8788/
```

## GitHub Pages

This repo deploys from the `main` branch root. After push, the site is at:

`https://prayanks.github.io/kannada-course/`
