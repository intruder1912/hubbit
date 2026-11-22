@echo off
rem Helper for the double-click launchers in this folder.
rem Runs "uv run <arguments>" from the project folder and keeps the window open.
rem Set LEGO_BOOST_NO_PAUSE=1 to skip the final pause (used by CI).
setlocal
cd /d "%~dp0.."
where uv >nul 2>nul
if errorlevel 1 (
    echo uv was not found. Install it as described in docs\setup-windows.md,
    echo then sign out of Windows and back in.
    set RC=1
    goto end
)
uv run %*
set RC=%ERRORLEVEL%
:end
if not defined LEGO_BOOST_NO_PAUSE pause
exit /b %RC%
