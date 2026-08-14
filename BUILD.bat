@echo off
chcp 65001 >nul
title Building VirtualPrinter.exe...
echo.
echo ================================================
echo   Building VirtualPrinter.exe (standalone)
echo ================================================
echo.
cd /d "%~dp0"

echo Step 1: Installing dependencies...
pip install PyQt6 PyMuPDF PyPDF2 PyInstaller --quiet
echo.

echo Step 2: Building EXE...
python -m PyInstaller ^
  --onefile ^
  --windowed ^
  --name VirtualPrinter ^
  --icon NONE ^
  --add-data "install_printer.py;." ^
  --add-data "hebrew_date.py;." ^
  --add-data "settings_manager.py;." ^
  --add-data "print_engine.py;." ^
  --add-data "ui_components.py;." ^
  --add-data "printer_installer.py;." ^
  --add-data "preview_dialog.py;." ^
  --hidden-import PyQt6 ^
  --hidden-import PyQt6.QtCore ^
  --hidden-import PyQt6.QtGui ^
  --hidden-import PyQt6.QtWidgets ^
  --hidden-import fitz ^
  --hidden-import PyPDF2 ^
  --noconfirm ^
  main.py

echo.
if exist dist\VirtualPrinter.exe (
    echo ================================================
    echo   SUCCESS! File: dist\VirtualPrinter.exe
    echo   Copy it anywhere and run it standalone.
    echo ================================================
) else (
    echo   BUILD FAILED - check errors above
)
echo.
pause
