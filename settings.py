"""Persistent, validated user preferences with safe first-run defaults."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from localization import SUPPORTED_LANGUAGES

DEFAULTS = {"language": "en", "volume": 0.75, "fullscreen": False}


def _user_config_path() -> Path:
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA", Path.home()))
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "FiveNightsAtTheBoys" / "config.json"


def _portable_config_path() -> Path:
    root = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    return root / "config.json"


class SettingsStore:
    def __init__(self) -> None:
        self.paths = (_portable_config_path(), _user_config_path())
        self.values = dict(DEFAULTS)
        self.load()

    def load(self) -> dict:
        self.values = dict(DEFAULTS)
        for path in self.paths:
            try:
                with path.open(encoding="utf-8") as source:
                    data = json.load(source)
                if not isinstance(data, dict):
                    continue
                language = data.get("language", DEFAULTS["language"])
                if not isinstance(language, str) or language.lower() not in SUPPORTED_LANGUAGES:
                    language = DEFAULTS["language"]
                try:
                    volume = max(0.0, min(1.0, float(data.get("volume", DEFAULTS["volume"]))))
                except (TypeError, ValueError):
                    volume = DEFAULTS["volume"]
                fullscreen = data.get("fullscreen", DEFAULTS["fullscreen"])
                self.values = {
                    "language": language.lower(),
                    "volume": volume,
                    "fullscreen": fullscreen if isinstance(fullscreen, bool) else DEFAULTS["fullscreen"],
                }
                return self.values
            except FileNotFoundError:
                continue
            except (OSError, json.JSONDecodeError) as exc:
                print(f"[settings] Ignoring unreadable {path}: {exc}")
        return self.values

    def save(self) -> bool:
        payload = json.dumps(self.values, ensure_ascii=False, indent=2) + "\n"
        for path in self.paths:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = path.with_suffix(".json.tmp")
                temporary.write_text(payload, encoding="utf-8")
                temporary.replace(path)
                return True
            except OSError as exc:
                print(f"[settings] Could not save {path}: {exc}")
        return False

    def set(self, key: str, value) -> None:
        if key not in DEFAULTS:
            raise KeyError(key)
        if key == "language":
            value = value.lower() if isinstance(value, str) else DEFAULTS[key]
            if value not in SUPPORTED_LANGUAGES:
                value = DEFAULTS[key]
        elif key == "volume":
            try:
                value = max(0.0, min(1.0, float(value)))
            except (TypeError, ValueError):
                value = DEFAULTS[key]
        elif key == "fullscreen" and not isinstance(value, bool):
            value = DEFAULTS[key]
        self.values[key] = value
