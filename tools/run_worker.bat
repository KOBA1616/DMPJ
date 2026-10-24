@echo off
rem Run the local worker once (called from Task Scheduler). Keep this file ASCII-only: cmd.exe misreads UTF-8.
rem Log: %USERPROFILE%\.dmpj-worker\log.txt
set "PYTHONUTF8=1"
set "XDG_DATA_HOME=%USERPROFILE%\.dmpj-worker\xdg"
set "XDG_CONFIG_HOME=%USERPROFILE%\.dmpj-worker\xdg-config"
cd /d "%~dp0.."
if not exist "%USERPROFILE%\.dmpj-worker" mkdir "%USERPROFILE%\.dmpj-worker"
set "PY=python"
where python >nul 2>nul || set "PY=py -3"
rem One line with "& exit /b": cmd parses it fully first, so a self-update of this file mid-run is safe.
%PY% tools\local_worker.py run --once >> "%USERPROFILE%\.dmpj-worker\log.txt" 2>&1 & exit /b
