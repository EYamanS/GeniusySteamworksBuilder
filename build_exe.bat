@echo off
REM Build GENIUS Steamworks Builder into a single .exe (dist\)
cd /d "%~dp0"
echo ============================================
echo   Building GENIUS Steamworks Builder .exe
echo ============================================
python -m PyInstaller --noconfirm --clean "GENIUS.spec"
if %errorlevel% neq 0 (
    echo.
    echo BUILD FAILED.
    pause
    exit /b 1
)
echo.
echo ============================================
echo   DONE.  ->  dist\GENIUS Steamworks Builder.exe
echo ============================================
pause
