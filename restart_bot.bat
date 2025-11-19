@echo off
echo Stopping all Python processes...
taskkill /F /IM python.exe 2>nul
timeout /t 3 /nobreak >nul
echo Starting bot...
cd /d "%~dp0"
python bot/main.py
