# Five Nights at the Boys'

A small Pygame night-shift horror game. The game code is split into focused modules:

- `main.py` — application entry point.
- `game.py` — game loop, input and mode transitions.
- `entities.py` — player controls, cameras and animatronic behavior.
- `ui.py` — office, CRT/VHS treatment, camera tablet, menu and scare rendering.
- `audio_manager.py` — optional file-backed sound playback with silent fallback.

## Run from source

```bash
python -m pip install -r requirements.txt
python main.py
```

Controls: **A/D** doors, **Q/E** lights, **Space** raise/lower cameras, **1–0** select feeds.
The first keypress or click starts a night. Missing optional audio files are logged and do
not prevent the game from running; supported filenames are documented in `assets/audio/README.md`.
Run the lightweight gameplay tests with `python -m unittest discover -s tests -v`.

## Build a Windows release

With Python and PyInstaller installed on Windows, run `pyinstaller main.spec`. The spec
bundles the complete `assets/` directory so the executable can load the relocated images
and optional sounds. The generated executable is written to `dist/main.exe`.
