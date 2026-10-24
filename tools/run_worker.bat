@echo off
rem タスクスケジューラから呼ぶ。ワーカーを1回だけ実行し、ログを %USERPROFILE%\.dmpj-worker\log.txt に追記する。
rem デスクトップアプリのDBと食い違うため、CLI 専用の保存先を使う（無料モデルは匿名で動く）
set "XDG_DATA_HOME=%USERPROFILE%\.dmpj-worker\xdg"
set "XDG_CONFIG_HOME=%USERPROFILE%\.dmpj-worker\xdg-config"
cd /d "%~dp0.."
if not exist "%USERPROFILE%\.dmpj-worker" mkdir "%USERPROFILE%\.dmpj-worker"
python tools\local_worker.py run --once >> "%USERPROFILE%\.dmpj-worker\log.txt" 2>&1
