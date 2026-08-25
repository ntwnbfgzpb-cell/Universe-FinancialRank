#!/bin/bash
set -e
cd "$(dirname "$0")"
python3 -m pip install --upgrade pyinstaller pillow
python3 -m PyInstaller --noconfirm --clean --windowed --name SixFinancialRank --add-data "../project-assets:project-assets" --add-data "config:config" desktop_app.py
echo "完成：desktop/dist/SixFinancialRank.app"
