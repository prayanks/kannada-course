# Teaching notes

## Learner
- Prayank — Bengaluru resident
- Hindi + English base; absolute beginner in Kannada (knew only *Namaskara*)
- Accent target: natural Bengaluru spoken Kannada

## Preferences (locked)
- English instructions
- Hindi grammar / politeness parallels on every phrase card
- Full phrase cards: EN · HI · word-by-word · grammar · register
- ≤8–12 new words per lesson
- One grammar pattern, dialogue, production, role-play, review + real-world task
- Roman only

## Audio (lessons)
- Clips: `assets/audio/*.mp3` driven by `assets/audio/manifest.json`
- TTS: edge-tts `kn-IN-SapnaNeural` (Kannada script in manifest; UI stays Roman)
- Words → one clip; sentences/dialogue → `_slow` + `_nat`
- Generate: `python3 assets/generate_audio.py` (idempotent; `--force` to redo)
- After new lesson content: `python3 assets/build_manifest.py` then generate, then `python3 assets/retrofit_audio.py`
- Always label audio as machine-generated on each lesson page

## Pedagogy
- Build storage strength via retrieval (quizzes) not just re-reading
- Always tie back to neighbour / street use
