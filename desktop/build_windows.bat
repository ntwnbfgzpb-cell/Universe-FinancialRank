@echo off
cd /d %~dp0
python -m pip install --upgrade pyinstaller pillow
python -m PyInstaller --noconfirm --clean --windowed --name SixFinancialRank --add-data "../project-assets;project-assets" --add-data "config;config" desktop_app.py
if errorlevel 1 pause
