# Contributing

Contributions must be original procedural sound designs or improvements to code, metadata, accessibility and documentation.

Do not submit copied samples, operating-system sounds, copyrighted recordings, or derivatives of reference videos.

Before opening a pull request:

1. Add or modify the synthesis in `src/generate_library.py`.
2. Regenerate the library.
3. Run `python tools/validate_library.py`.
4. Update `library.json`, `library.csv`, `manifest.sha256`, and the changelog.
5. Preserve 48 kHz / 24-bit WAV and the -15 dBFS peak target unless a versioned revision is proposed.

Naming: `QT_CATEGORY_###_DescriptiveName.wav`.
