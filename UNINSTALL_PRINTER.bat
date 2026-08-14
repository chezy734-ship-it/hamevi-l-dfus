@echo off
chcp 65001 >nul
title Virtual Printer - הסרת מדפסת

net session >nul 2>&1
if %errorLevel% NEQ 0 (
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo.
echo  מסיר המביא לדפוס...
echo.

powershell -ExecutionPolicy Bypass -Command ^
    "Remove-Printer -Name 'המביא לדפוס' -ErrorAction SilentlyContinue; ^
     Remove-PrinterPort -Name 'VirtualPrinterPort:' -ErrorAction SilentlyContinue; ^
     Write-Host 'Done. Printer removed.' -ForegroundColor Green"

echo.
pause
