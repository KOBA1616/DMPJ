@echo off
rem タスクスケジューラから呼ぶ。ワーカーを1回だけ実行し、ログを %USERPROFILE%\.dmpj-worker\log.txt に追記する。
cd /d "%~dp0.."
if not exist "%USERPROFILE%\.dmpj-worker" mkdir "%USERPROFILE%\.dmpj-worker"
python tools\local_worker.py run --once >> "%USERPROFILE%\.dmpj-worker\log.txt" 2>&1
