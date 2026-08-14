@echo off
setlocal

net session >nul 2>&1
if %errorLevel% NEQ 0 (
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo.
echo Installing "HaMevi LaDfus" Virtual Printer...
echo.

powershell -NonInteractive -ExecutionPolicy Bypass -Command "$n='HaMevi LaDfus'; $port='HaMeviPort:'; $drv='Microsoft Print To PDF'; $out=[System.IO.Path]::Combine($env:LOCALAPPDATA,'HaMeviBLaDfus','incoming'); [System.IO.Directory]::CreateDirectory($out) | Out-Null; $f=[System.IO.Path]::Combine($out,'job.pdf'); Remove-Printer -Name $n -ErrorAction SilentlyContinue; Remove-PrinterPort -Name $port -ErrorAction SilentlyContinue; Add-PrinterPort -Name $f -ErrorAction SilentlyContinue; Add-Printer -Name $n -DriverName $drv -PortName $f; $p=Get-Printer -Name $n -ErrorAction SilentlyContinue; if($p){Write-Host 'SUCCESS - Printer installed!'} else {Write-Host 'FAILED'}"

echo.
echo Done. The printer "HaMevi LaDfus" is now available in Word, Chrome, etc.
echo.
pause
