"""JSON-backed interface localization with a safe English fallback."""
from __future__ import annotations

import json
import sys
from pathlib import Path


SUPPORTED_LANGUAGES = ("en", "ru")


def resource_path(relative: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return root / relative


class LocalizationManager:
    def __init__(self, language: str = "en") -> None:
        self.language = "en"
        self._strings: dict[str, str] = {}
        self._english: dict[str, str] = {}
        for code in SUPPORTED_LANGUAGES:
            try:
                with resource_path(f"locales/{code}.json").open(encoding="utf-8") as source:
                    data = json.load(source)
                if not isinstance(data, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in data.items()):
                    raise ValueError("locale file must contain string keys and values")
                if code == "en":
                    self._english = data
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                print(f"[localization] Could not load {code}.json: {exc}")
        self.set_language(language)

    def set_language(self, language: str) -> None:
        code = language.lower()
        if code not in SUPPORTED_LANGUAGES:
            code = "en"
        try:
            with resource_path(f"locales/{code}.json").open(encoding="utf-8") as source:
                data = json.load(source)
            if not isinstance(data, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in data.items()):
                raise ValueError("locale file must contain string keys and values")
            self._strings = data
            self.language = code
        except (OSError, json.JSONDecodeError, ValueError):
            self._strings = self._english
            self.language = "en"

    def get(self, key: str, **values: object) -> str:
        text = self._strings.get(key, self._english.get(key, key))
        try:
            return text.format(**values)
        except (KeyError, ValueError):
            return text
