@echo off
rem Install-Joinguard.cmd — replace WSL /bin/bash with the joinguard wrapper
rem (real bash diverted to /bin/bash.dist via dpkg-divert, package-safe).
rem Fixes: bash.exe stub -> '/bin/bash -c "/bin/bash -c \"CMD\""' outer
rem expansion eating $VAR/$(...) in every devin exec command.
rem No UAC needed: root inside WSL via `wsl -u root`.
rem Undo: Uninstall-Joinguard.cmd
setlocal
set SRC=%~dp0wsl-joinguard.py
if not exist "%SRC%" (
    echo [joinguard] source not found: %SRC%
    exit /b 1
)
wsl.exe -u root tr -d "\r" < "%~dp0wsl-joinguard.py" > /tmp/.joinguard.install
if errorlevel 1 ( echo [joinguard] stage failed & exit /b 1 )
wsl.exe -u root chmod 755 /tmp/.joinguard.install
wsl.exe -u root sh -c "if [ ! -e /bin/bash.dist ]; then dpkg-divert --divert /bin/bash.dist --rename --add /bin/bash; fi"
wsl.exe -u root cp /tmp/.joinguard.install /bin/bash
wsl.exe -u root chmod 755 /bin/bash
wsl.exe -u root rm -f /tmp/.joinguard.install
echo.
echo [joinguard] verify - expect literal $HOME inside the quotes:
C:\Windows\System32\bash.exe -c "echo VERIFY_SQ:'$HOME':END"
echo   VERIFY_SQ:$HOME:END      = fixed
echo   VERIFY_SQ:/home/...:END  = still broken
echo.
echo [joinguard] done. To remove: Uninstall-Joinguard.cmd
