import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from localization import LocalizationManager
from settings import SettingsStore


class SettingsLocalizationTests(unittest.TestCase):
    def test_language_switch_and_missing_key_fallback(self):
        loc = LocalizationManager("en")
        self.assertEqual(loc.get("menu_start"), "START NIGHT")
        loc.set_language("ru")
        self.assertEqual(loc.get("menu_start"), "НАЧАТЬ НОЧЬ")
        self.assertEqual(loc.get("not_a_key"), "not_a_key")

    def test_missing_or_corrupt_config_uses_defaults_and_round_trips(self):
        with tempfile.TemporaryDirectory() as temp:
            portable = Path(temp) / "config.json"
            fallback = Path(temp) / "user" / "config.json"
            with patch("settings._portable_config_path", return_value=portable), patch(
                "settings._user_config_path", return_value=fallback
            ):
                store = SettingsStore()
                self.assertEqual(store.values, {"language": "en", "volume": 0.75, "fullscreen": False})
                store.set("language", "ru")
                store.set("volume", 1.4)
                store.set("fullscreen", True)
                self.assertTrue(store.save())
                loaded = SettingsStore()
                self.assertEqual(loaded.values, {"language": "ru", "volume": 1.0, "fullscreen": True})

                portable.write_text("not-json", encoding="utf-8")
                broken = SettingsStore()
                self.assertEqual(broken.values, {"language": "en", "volume": 0.75, "fullscreen": False})


if __name__ == "__main__":
    unittest.main()
