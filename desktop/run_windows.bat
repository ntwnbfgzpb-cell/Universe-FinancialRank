@echo off
cd /d %~dp0
python desktop_app.py
if errorlevel 1 pause
