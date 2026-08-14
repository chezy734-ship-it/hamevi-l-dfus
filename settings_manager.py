#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Settings Manager - manages all application configuration"""

import json
import os
from pathlib import Path
from copy import deepcopy


CONFIG_DIR = Path.home() / ".virtual_printer"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_OPTIONS = [
    {
        "id": "normal",
        "name_he": "רגיל",
        "name_en": "Normal",
        "desc_he": "עמוד בודד",
        "desc_en": "Single page",
        "icon": "📄",
        "toggles": [],
        "printer_override": ""
    },
    {
        "id": "booklet_he",
        "name_he": "חוברת עברית",
        "name_en": "Hebrew Booklet",
        "desc_he": "ימין-שמאל",
        "desc_en": "Right-to-left",
        "icon": "📖",
        "toggles": ["duplex", "rtl"],
        "printer_override": ""
    },
    {
        "id": "booklet_a5",
        "name_he": "חוברת A5",
        "name_en": "A5 Booklet",
        "desc_he": "חוברת עברית A5 על A4",
        "desc_en": "Hebrew booklet A5 on A4",
        "icon": "📖",
        "toggles": ["duplex","rtl"],
        "printer_override": "",
        "visible": True
    },
    {
        "id": "duplex",
        "name_he": "דו-צדדי",
        "name_en": "Duplex",
        "desc_he": "שני צדדים",
        "desc_en": "Both sides",
        "icon": "🔄",
        "toggles": ["duplex", "flip"],
        "printer_override": ""
    },
    {
        "id": "two_up",
        "name_he": "2 בעמוד",
        "name_en": "2-up",
        "desc_he": "חיסכון בנייר",
        "desc_en": "Paper saving",
        "icon": "📋",
        "toggles": [],
        "printer_override": ""
    },
    {
        "id": "landscape",
        "name_he": "לרוחב",
        "name_en": "Landscape",
        "desc_he": "אופקי",
        "desc_en": "Horizontal",
        "icon": "🖼️",
        "toggles": [],
        "printer_override": ""
    },
    {
        "id": "booklet_en",
        "name_he": "חוברת לועזית",
        "name_en": "LTR Booklet",
        "desc_he": "שמאל-ימין",
        "desc_en": "Left-to-right",
        "icon": "📖",
        "toggles": ["duplex"],
        "printer_override": "",
        "visible": True
    },
    {
        "id": "four_up",
        "name_he": "4 בעמוד",
        "name_en": "4-up",
        "desc_he": "מגדיל חיסכון",
        "desc_en": "Max saving",
        "icon": "🗂️",
        "toggles": [],
        "printer_override": ""
    },
]

DEFAULT_TOGGLES = [
    {"id": "duplex",    "name_he": "דו-צדדי",          "name_en": "Duplex"},
    {"id": "flip",      "name_he": "היפוך",             "name_en": "Flip"},
    {"id": "rtl",       "name_he": "ימין-שמאל",         "name_en": "Right-to-left"},
    {"id": "color",     "name_he": "צבעוני",            "name_en": "Color"},
    {"id": "fit_page",  "name_he": "התאם לעמוד",        "name_en": "Fit to page"},
    {"id": "booklet_ltr", "name_he": "חוברת שמאל-ימין", "name_en": "Booklet LTR"},
]

DEFAULT_CONFIG = {
    "language": "he",
    "dark_mode": False,
    "password_enabled": True,
    "password": "1234",
    "default_printer": "",
    "show_printer_selector": True,
    "show_gregorian_date": False,
    "show_date": True,
    "date_mode": "hebrew",
    "show_time": True,
    "time_24h": True,
    "show_settings_btn": True,
    "settings_shortcut": "F8",
    "start_with_windows": False,
    "first_run": True,   # "hebrew" | "gregorian" | "both"
    "options": DEFAULT_OPTIONS,
    "toggles": DEFAULT_TOGGLES,
}


class SettingsManager:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._config = {}
        self.load()

    def load(self):
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self._config = {**deepcopy(DEFAULT_CONFIG), **loaded}
                # Ensure defaults for options/toggles if missing
                if not self._config.get("options"):
                    self._config["options"] = deepcopy(DEFAULT_OPTIONS)
                if not self._config.get("toggles"):
                    self._config["toggles"] = deepcopy(DEFAULT_TOGGLES)
            else:
                self._config = deepcopy(DEFAULT_CONFIG)
                self.save()
        except Exception as e:
            print(f"Error loading config: {e}")
            self._config = deepcopy(DEFAULT_CONFIG)

    def save(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key, default=None):
        return self._config.get(key, default)

    def set(self, key, value):
        self._config[key] = value

    def get_options(self):
        return self._config.get("options", deepcopy(DEFAULT_OPTIONS))

    def set_options(self, options):
        self._config["options"] = options

    def get_toggles(self):
        return self._config.get("toggles", deepcopy(DEFAULT_TOGGLES))

    def set_toggles(self, toggles):
        self._config["toggles"] = toggles

    def get_option_printer(self, option_id):
        opts = self.get_options()
        for o in opts:
            if o["id"] == option_id:
                return o.get("printer_override", "")
        return ""

    def reset_to_defaults(self):
        self._config = deepcopy(DEFAULT_CONFIG)
        self.save()
