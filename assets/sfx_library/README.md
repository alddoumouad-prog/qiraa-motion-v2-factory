# Qiraa Tactile UI SFX

**120 original tactile UI sounds for vertical video, interfaces and motion design.**  
No stock samples. No copied reference audio. Every sound is synthesized deterministically from original code.

## Library

- **120 sounds / 12 families / 10 variations per family**
- **48 kHz, 24-bit PCM WAV** plus **192 kbps MP3**
- Mix-ready peak: **-15 dBFS**
- Mono tactile sounds and stereo movement/transition sounds
- Durations: **100–885 ms**
- MIT licensed audio and code
- Interactive browser player with search, filters and downloads

## Families

| Family | Count | Typical use |
|---|---:|---|
| Taps | 10 | Small UI touches and markers |
| Clicks | 10 | Mechanical tactile feedback |
| Presses | 10 | Weighted buttons and press/release |
| Toggles | 10 | On/off and state changes |
| Text Reveal | 10 | Headlines, words and numbers |
| Cards | 10 | Bento cards and panels |
| Swipes | 10 | Low-passed motion under 500 Hz |
| Notifications | 10 | Messages and subtle notices |
| Success | 10 | Save, ready and complete |
| Alerts | 10 | Muted warning, cancel and retry |
| Keyboard | 10 | Editing and typing sequences |
| Transitions | 10 | Scenes, macro moves and logo outro |

## Listen and browse

Open `index.html` after downloading the repository. The player works locally without a build step and is ready for GitHub Pages.

A short compilation is included at `demo/Qiraa_Tactile_Demo.mp3`.

## Quick use

Use WAV in editing software. Use MP3 for web previews and lightweight sharing. Metadata is available in `library.json`, `library.csv`, and `manifest.sha256`.

For the Qiraa Apple Pro template, place text sounds on title reveals, card sounds on Bento entrances, and low-passed swipes on scene transitions. The source remains at -3 dB, SFX at approximately -15 dBFS, and optional music at -24 dB.

## Regenerate

```bash
python -m pip install -r requirements.txt
# FFmpeg must be available in PATH, or set FFMPEG to its full path.
python src/generate_library.py
python tools/validate_library.py
```

The generator uses a fixed SHA-256-derived seed for every asset. Rebuilding the same version reproduces the same sound designs.

## Repository contents

- `audio/` — WAV and MP3 files, grouped by family
- `src/generate_library.py` — original procedural synthesizer
- `tools/validate_library.py` — technical and uniqueness checks
- `index.html` + `library.js` — interactive library browser
- `library.json` / `library.csv` — searchable metadata
- `manifest.sha256` — integrity hashes
- `docs/` — usage, sound design and reference notes
- `.github/workflows/` — validation, Pages and release automation

## License

MIT for audio and code. See `LICENSE`. Attribution is appreciated, not required beyond the MIT notice.

## العربية

مكتبة **قراءة ثانية Tactile UI SFX** تتضمن 120 مؤثرًا أصليًا مناسبًا للنقرات والبطاقات والنصوص والانتقالات في تيك توك وReels. جميع الأصوات مولدة برمجيًا ولا تتضمن تسجيلات أو مقاطع من الأمثلة المرجعية.

- التشغيل التجريبي: افتح `index.html`.
- التوثيق العربي: `docs/USAGE_AR.md`.
- النشر على GitHub: `PUBLISH_AR.md`.
- الترخيص: MIT للأصوات والكود.
