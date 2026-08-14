#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""printer_installer.py — used by main app for file watcher path."""

import os
from pathlib import Path

PRINTER_NAME = "המביא לדפוס"

class PrinterInstaller:
    @staticmethod
    def get_output_dir() -> Path:
        return Path(os.environ.get("LOCALAPPDATA","C:/Temp")) / "HaMeviBLaDfus" / "incoming"
