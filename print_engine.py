#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print Engine - handles actual printing on Windows"""

import subprocess, os, sys, tempfile
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000


class PrintEngine:
    def __init__(self, settings):
        self.settings = settings

    @staticmethod
    def get_system_printers():
        try:
            result = subprocess.run(
                ["powershell", "-NonInteractive", "-Command",
                 "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;"
                 "Get-Printer | Select-Object -ExpandProperty Name"],
                capture_output=True, creationflags=CREATE_NO_WINDOW, timeout=10
            )
            out = result.stdout.decode("utf-8","replace").strip()
            printers = [p.strip() for p in out.splitlines() if p.strip()]
            if printers: return printers
        except: pass
        try:
            result = subprocess.run(["wmic","printer","get","name"],
                capture_output=True, creationflags=CREATE_NO_WINDOW, timeout=10)
            out = result.stdout.decode("utf-8","replace")
            printers = [l.strip() for l in out.splitlines()[1:] if l.strip()]
            if printers: return printers
        except: pass
        return ["Default Printer"]

    def count_pages(self, file_path):
        try:
            import fitz
            doc = fitz.open(file_path)
            return len(doc)
        except: pass
        try:
            import PyPDF2
            with open(file_path,"rb") as f:
                return len(PyPDF2.PdfReader(f).pages)
        except: pass
        return 0

    def print_file(self, file_path, option, printer_name, copies=1, toggles=None):
        """Send file to real printer with correct settings."""
        if toggles is None: toggles = {}
        ext    = Path(file_path).suffix.lower()
        opt_id = option.get("id","normal")
        printer = (printer_name or "").strip()

        # Try SumatraPDF (best quality, supports n-up, booklet, duplex)
        sumatra = self._find_sumatra()
        if sumatra and ext == ".pdf":
            return self._print_sumatra(sumatra, file_path, printer, copies, opt_id, toggles)

        # Fallback: PowerShell / WScript print to specific printer
        return self._print_powershell(file_path, printer, copies)

    def _find_sumatra(self):
        candidates = [
            Path(sys.executable).parent / "SumatraPDF.exe",  # bundled with EXE
            Path(__file__).parent / "SumatraPDF.exe",
            Path(os.environ.get("PROGRAMFILES","C:/Program Files")) / "SumatraPDF/SumatraPDF.exe",
            Path(os.environ.get("LOCALAPPDATA","")) / "SumatraPDF/SumatraPDF.exe",
        ]
        for p in candidates:
            if p.exists(): return str(p)
        try:
            r = subprocess.run(["where","SumatraPDF"], capture_output=True,
                               creationflags=CREATE_NO_WINDOW, text=True)
            if r.returncode == 0: return r.stdout.strip().splitlines()[0]
        except: pass
        return None

    def _print_sumatra(self, sumatra, file_path, printer, copies, opt_id, toggles):
        cmd = [sumatra, "-print-to", printer]
        parts = []
        if copies > 1: parts.append(f"copies={copies}")

        # Duplex settings
        duplex = toggles.get("duplex",False) or opt_id in ("duplex","booklet_he","booklet_en")
        flip   = toggles.get("flip",False)
        if duplex: parts.append("duplexshort" if flip else "duplexlong")

        # Orientation
        if opt_id == "landscape" or toggles.get("landscape",False): parts.append("landscape")

        # N-up
        if opt_id == "two_up":  parts.append("nup=2")
        if opt_id == "four_up": parts.append("nup=4")

        # Booklet (A5 content on A4 paper, 2 pages per sheet)
        if opt_id in ("booklet_he","booklet_en"):
            parts.append("booklet")
            parts.append("nup=2")

        if parts: cmd += ["-print-settings", ",".join(parts)]
        cmd.append(str(file_path))

        try:
            r = subprocess.run(cmd, capture_output=True,
                               creationflags=CREATE_NO_WINDOW, timeout=120)
            if r.returncode != 0:
                # Sumatra קיים אך נכשל — נופל לגיבוי PowerShell
                print(f"SumatraPDF failed (rc={r.returncode}), falling back to PowerShell")
                return self._print_powershell(file_path, printer, copies)
            return True
        except Exception as e:
            print(f"SumatraPDF error: {e}")
            return self._print_powershell(file_path, printer, copies)

    def _print_powershell(self, file_path, printer, copies):
        """
        Print to a SPECIFIC printer using PowerShell.
        Sets the target printer as default temporarily, prints, then restores.
        """
        fp = str(file_path).replace("\\","\\\\").replace('"','\\"')
        pr = printer.replace("\\","\\\\").replace('"','\\"')
        copies_code = ""
        if copies > 1:
            copies_code = f"""
for ($i=1; $i -le {copies}; $i++) {{
    Start-Process -FilePath "{fp}" -Verb PrintTo -ArgumentList "{pr}" -Wait
}}
"""
        else:
            copies_code = f'Start-Process -FilePath "{fp}" -Verb PrintTo -ArgumentList "{pr}" -Wait'

        ps = f"""
$ErrorActionPreference = 'Stop'
$printerName = "{pr}"
$file = "{fp}"

# Verify printer exists
$p = Get-Printer -Name $printerName -ErrorAction SilentlyContinue
if (-not $p) {{
    Write-Output "PRINTER_NOT_FOUND: $printerName"
    exit 1
}}

{copies_code}
Write-Output "PRINT_OK"
exit 0
"""
        ps_path = Path(tempfile.gettempdir()) / "hamevi_print.ps1"
        ps_path.write_bytes(b"\xef\xbb\xbf" + ps.encode("utf-8"))
        try:
            r = subprocess.run(
                ["powershell","-NonInteractive","-ExecutionPolicy","Bypass",
                 "-WindowStyle","Hidden","-File",str(ps_path)],
                capture_output=True, creationflags=CREATE_NO_WINDOW, timeout=120
            )
            out = r.stdout.decode("utf-8","replace")
            return r.returncode == 0 and "PRINT_OK" in out
        except Exception as e:
            print(f"Print error: {e}")
            return False
        finally:
            try: ps_path.unlink()
            except: pass
