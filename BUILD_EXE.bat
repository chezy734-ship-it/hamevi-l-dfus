@echo off
setlocal
cd /d "%~dp0"
echo.
echo ================================================
echo   HaMevi LaDfus - Building EXE
echo ================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (echo ERROR: Python not found & pause & exit /b 1)

echo Installing / updating dependencies...
pip install PyQt6 PyMuPDF PyPDF2 PyInstaller --quiet

echo.
echo Building VirtualPrinter.exe ...
echo (this takes 1-3 minutes)
echo.

pyinstaller --onefile --windowed --name VirtualPrinter ^
  --add-data "install_printer.py;." ^
  --add-data "printer_installer.py;." ^
  --add-data "settings_manager.py;." ^
  --add-data "print_engine.py;." ^
  --add-data "ui_components.py;." ^
  --add-data "hebrew_date.py;." ^
  --add-data "preview_dialog.py;." ^
  --hidden-import PyQt6.QtCore ^
  --hidden-import PyQt6.QtGui ^
  --hidden-import PyQt6.QtWidgets ^
  --hidden-import fitz ^
  --hidden-import PyPDF2 ^
  main.py

if exist dist\VirtualPrinter.exe (
    echo.
    echo ================================================
    echo   SUCCESS!
    echo   dist\VirtualPrinter.exe is ready.
    echo   Copy it to any folder and run it.
    echo ================================================
) else (
    echo.
    echo   BUILD FAILED - check errors above
)
echo.
pause
