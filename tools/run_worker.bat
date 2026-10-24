@echo off
rem タスクスケジューラから呼ぶ。ワーカーを1回だけ実行し、ログを %USERPROFILE%\.dmpj-worker\log.txt に追記する。
rem デスクトップアプリのDBと食い違うため、CLI 専用の保存先を使う（無料モデルは匿名で動く）
set "XDG_DATA_HOME=%USERPROFILE%\.dmpj-worker\xdg"
set "XDG_CONFIG_HOME=%USERPROFILE%\.dmpj-worker\xdg-config"
cd /d "%~dp0.."
if not exist "%USERPROFILE%\.dmpj-worker" mkdir "%USERPROFILE%\.dmpj-worker"
set "PY=python"
where python >nul 2>nul || set "PY=py -3"
%PY% tools\local_worker.py run --once >> "%USERPROFILE%\.dmpj-worker\log.txt" 2>&1
