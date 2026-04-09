@echo off
:: YouTube Factory — Eenmalige remote fix voor Windows
:: Dubbelklik dit bestand als install.bat nog naar de oude repo wijst.
:: Na deze fix kan je install.bat normaal gebruiken voor updates.

echo.
echo   ================================
echo     YouTube Factory Remote Fix
echo   ================================
echo.

set APP_DIR=%USERPROFILE%\youtube-factory

if not exist "%APP_DIR%\.git" (
    echo   Geen bestaande installatie gevonden in:
    echo   %APP_DIR%
    echo.
    echo   Draai eerst install.bat om de app te installeren.
    pause
    exit /b 1
)

cd /d "%APP_DIR%"

echo   Huidige remote:
git remote -v
echo.

echo   Remote aanpassen naar Primadetaautomation/youtube-factory...
git remote set-url origin https://github.com/Primadetaautomation/youtube-factory.git
if errorlevel 1 (
    echo   Kon remote niet aanpassen.
    pause
    exit /b 1
)

echo   Updates ophalen...
git pull origin main
if errorlevel 1 (
    echo.
    echo   git pull is mislukt. Mogelijk lokale wijzigingen of conflict.
    echo   Vraag om hulp.
    pause
    exit /b 1
)

echo.
echo   ================================
echo     Klaar! Remote is gefixt.
echo   ================================
echo.
echo   Vanaf nu kan je install.bat dubbelklikken voor updates.
echo.
pause
