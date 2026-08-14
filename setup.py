#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup and Build Script for Virtual Printer
Run this to:
1. Install dependencies
2. Build exe with PyInstaller
3. Install virtual printer on Windows
"""

import subprocess
import sys
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent


def run(cmd, **kwargs):
    print(f"\n>>> {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    return subprocess.run(cmd, **kwargs)


def install_dependencies():
    print("\n" + "="*50)
    print("📦 Installing Python dependencies...")
    print("="*50)
    packages = [
        "PyQt6",
        "PyInstaller",
        "PyPDF2",
    ]
    for pkg in packages:
        result = run([sys.executable, "-m", "pip", "install", pkg])
        if result.returncode != 0:
            print(f"⚠️  Warning: Failed to install {pkg}")


def build_exe():
    print("\n" + "="*50)
    print("🔨 Building executable with PyInstaller...")
    print("="*50)

    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None
src_dir = Path(SPECPATH)

a = Analysis(
    [str(src_dir / 'main.py')],
    pathex=[str(src_dir)],
    binaries=[],
    datas=[
        (str(src_dir / 'resources'), 'resources'),
    ],
    hiddenimports=[
        'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
        'PyQt6.sip',
        'settings_manager', 'print_engine', 'hebrew_date',
        'printer_installer', 'ui_components',
        'PyPDF2',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VirtualPrinter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    version_file=None,
    uac_admin=False,
)
'''

    spec_path = SCRIPT_DIR / "VirtualPrinter.spec"
    spec_path.write_text(spec_content, encoding='utf-8')

    result = run([
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        str(spec_path)
    ], cwd=str(SCRIPT_DIR))

    if result.returncode == 0:
        exe_path = SCRIPT_DIR / "dist" / "VirtualPrinter.exe"
        if exe_path.exists():
            print(f"\n✅ Executable built successfully!")
            print(f"   Location: {exe_path}")
            return str(exe_path)
        else:
            print("\n⚠️  Exe not found at expected path, check dist/ folder")
            return None
    else:
        print("\n❌ Build failed!")
        return None


def install_printer(exe_path):
    print("\n" + "="*50)
    print("🖨️  Installing Virtual Printer on Windows...")
    print("="*50)

    try:
        from printer_installer import PrinterInstaller

        if not PrinterInstaller.is_admin():
            print("⚠️  Not running as Administrator.")
            print("   The printer installation requires Admin rights.")
            print("   Attempting to re-launch with elevation...")
            PrinterInstaller.request_admin_and_install(exe_path)
            return

        if PrinterInstaller.is_installed():
            print("ℹ️  Virtual printer already installed.")
            return

        success, msg = PrinterInstaller.install(exe_path)
        if success:
            print(f"✅ {msg}")
        else:
            print(f"❌ Installation failed: {msg}")
            print("\n   Manual installation instructions:")
            print_manual_instructions(exe_path)

    except ImportError:
        print("⚠️  Could not import installer. Running on non-Windows?")
        print_manual_instructions(exe_path)


def print_manual_instructions(exe_path=None):
    print("""
╔══════════════════════════════════════════════════════════╗
║          הוראות התקנה ידנית של המדפסת הווירטואלית         ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  כדי להתקין את המדפסת הווירטואלית:                        ║
║                                                          ║
║  1. פתח PowerShell כמנהל מערכת (Run as Administrator)    ║
║  2. הרץ את הפקודות הבאות:                                ║
║                                                          ║
║  Add-PrinterPort -Name "VirtualPrinterPort:"             ║
║  Add-Printer -Name "מדפסת וירטואלית" \                   ║
║    -DriverName "Microsoft Print To PDF" \                ║
║    -PortName "VirtualPrinterPort:"                       ║
║                                                          ║
║  3. המדפסת תופיע בכל האפליקציות.                         ║
║                                                          ║
║  לשליחת קובץ ישירות לתוכנה:                              ║
║  גרור קובץ לחלון התוכנה, או בחר קובץ מתוך ממשק התוכנה.  ║
╚══════════════════════════════════════════════════════════╝
""")


def create_install_bat():
    """Create a Windows batch file for easy installation"""
    bat_content = r'''@echo off
title Virtual Printer - Installation
echo.
echo  ====================================
echo   Installing Virtual Printer...
echo  ====================================
echo.

:: Check for admin rights
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb runas"
    exit /b
)

echo Running as Administrator - OK
echo.

:: Run Python installer
python "%~dp0setup.py" --install-only
if errorlevel 1 (
    echo.
    echo Alternative: Manual printer install
    powershell -ExecutionPolicy Bypass -Command ^
      "Add-PrinterPort -Name 'VirtualPrinterPort:' -ErrorAction SilentlyContinue; ^
       Add-Printer -Name 'Virtual Printer' -DriverName 'Microsoft Print To PDF' ^
       -PortName 'VirtualPrinterPort:' -ErrorAction SilentlyContinue; ^
       Write-Host 'Done! Printer installed.'"
)

echo.
echo  ====================================
echo   Installation complete!
echo   The printer is now available in
echo   Word, Chrome, and all other apps.
echo  ====================================
echo.
pause
'''
    bat_path = SCRIPT_DIR / "INSTALL_PRINTER.bat"
    bat_path.write_text(bat_content, encoding='cp1255')
    print(f"\n✅ Created: {bat_path}")


def create_readme():
    readme = """# מדפסת וירטואלית - Virtual Printer

## 📋 תוכן התיקייה

| קובץ | תיאור |
|------|-------|
| `VirtualPrinter.exe` | האפליקציה הראשית |
| `INSTALL_PRINTER.bat` | התקנת המדפסת הווירטואלית |
| `setup.py` | סקריפט בנייה (למפתחים) |

---

## 🚀 התקנה מהירה

### שלב 1: הפעל את התוכנה
לחץ פעמיים על `VirtualPrinter.exe`

### שלב 2: התקן את המדפסת הווירטואלית
לחץ פעמיים על `INSTALL_PRINTER.bat` ואשר הרשאות מנהל.

לאחר ההתקנה, המדפסת **"מדפסת וירטואלית"** תופיע ב:
- Microsoft Word ✅
- Google Chrome ✅  
- Adobe Reader ✅
- כל תוכנה אחרת ✅

---

## 🖨️ שימוש

### שליחת מסמך להדפסה
1. בכל תוכנה, לחץ **הדפס** (Ctrl+P)
2. בחר **"מדפסת וירטואלית"** מרשימת המדפסות
3. לחץ הדפס — חלון התוכנה ייפתח עם אפשרויות ההדפסה
4. בחר את סוג ההדפסה הרצוי ולחץ **"הדפס עכשיו"**

### פתיחה ישירה
- גרור קובץ לחלון התוכנה
- או לחץ **"בחר קובץ"** בחלון הפתוח

---

## ⚙️ הגדרות
לחץ על ⚙️ בחלון הראשי לגישה להגדרות.  
הגדרות מוגנות בסיסמה ברירת מחדל: **1234**

---

## 🔧 דרישות מערכת
- Windows 10 / 11
- Python 3.10+ (רק לבנייה מקוד מקור)

---

## ❓ שאלות נפוצות

**ש: המדפסת לא מופיעה ב-Word?**  
ת: הפעל את `INSTALL_PRINTER.bat` כמנהל מערכת

**ש: שכחתי את הסיסמה להגדרות?**  
ת: הסיסמה ברירת מחדל היא 1234

**ש: כיצד להסיר את התוכנה?**  
ת: פתח PowerShell כמנהל והרץ: `Remove-Printer -Name "מדפסת וירטואלית"`
"""
    readme_path = SCRIPT_DIR / "README.md"
    readme_path.write_text(readme, encoding='utf-8')
    print(f"✅ Created: {readme_path}")


def main():
    print("""
╔═══════════════════════════════════════════╗
║      מדפסת וירטואלית - Setup & Build      ║
╚═══════════════════════════════════════════╝
""")

    if "--install-only" in sys.argv:
        from printer_installer import PrinterInstaller
        exe = Path(sys.argv[0]).parent / "dist" / "VirtualPrinter.exe"
        PrinterInstaller.install(str(exe))
        return

    # 1. Install deps
    install_dependencies()

    # 2. Build exe
    exe_path = build_exe()

    # 3. Create helper files
    create_install_bat()
    create_readme()

    # 4. Offer to install printer
    if exe_path:
        print("\n" + "="*50)
        resp = input("🖨️  Install virtual printer now? (requires Admin) [y/n]: ").strip().lower()
        if resp in ('y', 'yes', 'כן', 'כ'):
            install_printer(exe_path)

    print("""
╔═══════════════════════════════════════════════╗
║              ✅ Build Complete!                ║
║                                               ║
║  Files ready:                                 ║
║  📦 dist/VirtualPrinter.exe  ← Main app       ║
║  🖨️  INSTALL_PRINTER.bat     ← Install printer ║
║  📄 README.md                ← Instructions   ║
╚═══════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
