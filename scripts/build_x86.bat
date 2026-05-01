@echo off
setlocal
cd /d "%~dp0\.."
if not exist .venv-win7-x86 (
  py -3.8-32 -m venv .venv-win7-x86
)
call .venv-win7-x86\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel pyinstaller
python -m pip install -e .
pyinstaller --onefile --name neutrino-py-x86 src\neutrino_py\__main__.py

