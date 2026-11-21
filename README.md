# Five Nights at the Boys'

A first-person Pygame night-shift horror game. The office is a hand-drawn 2.5D panorama with mouse-look parallax, and surveillance feeds are static 2D scenes with photo-based animatronics and VHS interference. No OpenGL or external models are used. The game code is split into focused modules:

- `main.py` — application entry point.
- `game.py` — game loop, input and mode transitions.
- `entities.py` — player controls, cameras and animatronic behavior.
- `office_render.py` — native-Pygame office panorama, static surveillance-room scenes and photo alpha preparation.
- `ui.py` — HUD, CRT/VHS treatment, first-person camera tablet, menus and scare rendering.
- `audio_manager.py` — optional file-backed sound playback with silent fallback.
- `localization.py` and `locales/` — English/Russian UI strings.
- `settings.py` — validated preferences and persistent `config.json` storage.

## Run from source

```bash
python -m pip install -r requirements.txt
python main.py
```

Controls: **Mouse / ← / →** look around, **A/D** doors, **Q/E** lights, **Space** raise/lower cameras, **1–0** select feeds.
Open **Settings** from the title screen (or press **S**) to switch RU/EN, adjust master
volume, and toggle fullscreen. Preferences are saved to `config.json` next to the game,
with a per-user config fallback if that directory is not writable. Missing optional audio
files are logged and do not prevent the game from running; supported filenames are
documented in `assets/audio/README.md`.
Run the lightweight gameplay tests with `python -m unittest discover -s tests -v`.

## Build a Windows release

With Python and PyInstaller installed on Windows, run `pyinstaller main.spec`. The spec
bundles the complete `assets/` directory so the executable can load the relocated images
and optional sounds. The generated executable is written to `dist/main.exe`. The GitHub Actions workflow also
builds on pushes to `main` and version tags (`v*`), runs the tests, and publishes a downloadable
`five-nights-at-the-boys-windows` artifact.
