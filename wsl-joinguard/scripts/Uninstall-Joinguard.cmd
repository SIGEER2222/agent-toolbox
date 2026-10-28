@echo off
rem Uninstall-Joinguard.cmd — restore the real /bin/bash (undo dpkg-divert)
wsl.exe -u root sh -c "if [ -e /bin/bash.dist ]; then rm -f /bin/bash; dpkg-divert --rename --remove /bin/bash; fi"
wsl.exe -u root head -c 20 /bin/bash
echo.
echo [joinguard] /bin/bash restored to package binary.
