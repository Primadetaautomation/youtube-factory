@echo off
:: YouTube Factory — Windows Installer
echo.
echo   ================================
echo     YouTube Factory Installer
echo   ================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo   Python niet gevonden.
    echo   Download Python 3.10+ van https://python.org/downloads
    echo   Vink "Add Python to PATH" aan tijdens installatie.
    pause
    exit /b 1
)
echo   Python gevonden.

:: Check FFmpeg
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo   FFmpeg niet gevonden.
    echo   Download van https://ffmpeg.org/download.html
    echo   Voeg toe aan je PATH.
    pause
    exit /b 1
)
echo   FFmpeg gevonden.

:: Create app directory
set APP_DIR=%USERPROFILE%\youtube-factory
if not exist "%APP_DIR%" mkdir "%APP_DIR%"

:: Download of updaten
if exist "%APP_DIR%\.git" (
    echo   App updaten...
    cd /d "%APP_DIR%"
    git pull origin main
) else (
    echo   Downloaden...
    git clone https://github.com/Primadetaautomation/youtube-factory.git "%APP_DIR%"
    if errorlevel 1 (
        echo   Git niet gevonden. Installeer git of download handmatig.
        pause
        exit /b 1
    )
    cd /d "%APP_DIR%"
)

:: Virtual environment
echo   Virtual environment aanmaken...
python -m venv .venv
call .venv\Scripts\activate.bat

:: Install deps
echo   Packages installeren...
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
pip install --quiet --upgrade yt-dlp

echo.
echo   ================================
echo     Installatie voltooid!
echo   ================================
echo.
echo   Start met: start.bat
echo.
pause
