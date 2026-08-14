#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install_printer.py
Works both as standalone script AND when bundled inside EXE via PyInstaller.
Usage: python install_printer.py [install|uninstall]
Auto-elevates to Administrator.
"""

import subprocess, os, sys, tempfile, ctypes
from pathlib import Path

PRINTER_NAME     = "המביא לדפוס"
DRIVER_NAME      = "Microsoft Print To PDF"
CREATE_NO_WINDOW = 0x08000000


def is_admin():
    try:    return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except: return False


def get_port_path():
    d = Path(os.environ.get("LOCALAPPDATA","C:/Temp")) / "HaMeviBLaDfus" / "incoming"
    d.mkdir(parents=True, exist_ok=True)
    return str(d / "job.pdf")


def run_ps(code: str, timeout=120):
    """Write UTF-8-BOM PS1 file and run PowerShell — hidden window."""
    ps = Path(tempfile.gettempdir()) / "hamevi_ps.ps1"
    ps.write_bytes(b"\xef\xbb\xbf" + code.encode("utf-8"))
    result = subprocess.run(
        ["powershell", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-WindowStyle", "Hidden", "-File", str(ps)],
        capture_output=True,
        creationflags=CREATE_NO_WINDOW,
        timeout=timeout
    )
    try: ps.unlink()
    except: pass
    out = result.stdout.decode("utf-8","replace")
    err = result.stderr.decode("utf-8","replace")
    return result.returncode, out, err


def is_installed():
    """Check if printer is in Windows printer list."""
    try:
        rc, out, err = run_ps(
            f'[Console]::OutputEncoding=[System.Text.Encoding]::UTF8\n'
            f'$p = Get-Printer -Name "{PRINTER_NAME}" -ErrorAction SilentlyContinue\n'
            f'if ($p) {{ Write-Output "FOUND" }} else {{ Write-Output "NOT_FOUND" }}'
        , timeout=10)
        # "FOUND" הוא תת-מחרוזת של "NOT_FOUND" — חייבים לבדוק את שניהם
        return "FOUND" in out and "NOT_FOUND" not in out
    except:
        return False


def install():
    port = get_port_path().replace("\\", "\\\\")

    ps = f"""
$ErrorActionPreference = 'Continue'
$pName = "{PRINTER_NAME}"
$pPort = "{port}"
$pDrv  = "{DRIVER_NAME}"

Write-Output "STEP1: Removing old printer..."
Remove-Printer -Name $pName -ErrorAction SilentlyContinue

Write-Output "STEP2: Creating output directory..."
$dir = [System.IO.Path]::GetDirectoryName($pPort)
if (-not (Test-Path $dir)) {{ New-Item -ItemType Directory -Force -Path $dir | Out-Null }}

Write-Output "STEP3: Restarting Print Spooler..."
Stop-Service -Name Spooler -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Start-Service -Name Spooler -ErrorAction Stop
Start-Sleep -Seconds 2

Write-Output "STEP4: Removing old port..."
Remove-PrinterPort -Name $pPort -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

Write-Output "STEP5: Adding printer port..."
try {{
    Add-PrinterPort -Name $pPort -ErrorAction Stop
    Write-Output "PORT_OK"
}} catch {{
    Write-Output "PORT_REG: Using registry method..."
    $reg = "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Print\\Monitors\\Local Port\\Ports"
    if (-not (Test-Path $reg)) {{ New-Item -Path $reg -Force | Out-Null }}
    New-ItemProperty -Path $reg -Name $pPort -Value "" -PropertyType String -Force | Out-Null
    Stop-Service -Name Spooler -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Start-Service -Name Spooler
    Start-Sleep -Seconds 2
    Write-Output "PORT_REG_DONE"
}}

Write-Output "STEP6: Checking driver..."
$drv = Get-PrinterDriver -Name $pDrv -ErrorAction SilentlyContinue
if (-not $drv) {{
    Write-Output "Installing driver..."
    Add-PrinterDriver -Name $pDrv -ErrorAction Stop
}}
Write-Output "DRIVER_OK"

Write-Output "STEP7: Installing printer..."
Add-Printer -Name $pName -DriverName $pDrv -PortName $pPort -ErrorAction Stop
Start-Sleep -Seconds 1

Write-Output "STEP8: Verifying..."
$check = Get-Printer -Name $pName -ErrorAction SilentlyContinue
if ($check) {{
    Write-Output "SUCCESS"
    exit 0
}} else {{
    Write-Output "FAILED: not found after install"
    exit 1
}}
"""
    rc, out, err = run_ps(ps)
    full = out + ("\nERRORS:\n" + err if err.strip() else "")
    success = rc == 0 and "SUCCESS" in out
    return success, full


def uninstall():
    port = get_port_path().replace("\\","\\\\")
    ps = f"""
Remove-Printer -Name "{PRINTER_NAME}" -ErrorAction SilentlyContinue
Remove-PrinterPort -Name "{port}" -ErrorAction SilentlyContinue
Write-Output "REMOVED"
"""
    rc, out, err = run_ps(ps, timeout=30)
    return rc == 0, out


def elevate_and_install(action="install"):
    """Launch this script (or the bundled EXE) as Administrator."""
    # When bundled as EXE, sys.executable is the EXE itself
    # We pass a special argument to trigger installer mode
    exe = sys.executable
    if getattr(sys, 'frozen', False):
        # Running as compiled EXE
        params = f'--install-action {action}'
    else:
        script = os.path.abspath(__file__)
        params = f'"{script}" {action}'

    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", exe, params, None, 1
    )


def main():
    action = "install"
    for i, arg in enumerate(sys.argv[1:]):
        if arg in ("install", "uninstall"):
            action = arg
        elif arg == "--install-action" and i+1 < len(sys.argv)-1:
            action = sys.argv[i+2]

    if not is_admin():
        print("Not admin — requesting elevation...")
        elevate_and_install(action)
        sys.exit(0)

    if action == "uninstall":
        ok, msg = uninstall()
        print(msg)
    else:
        ok, msg = install()
        print(msg)

    if not getattr(sys, 'frozen', False):
        input("\nPress Enter to close...")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
