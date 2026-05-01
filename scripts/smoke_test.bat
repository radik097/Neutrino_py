@echo off
setlocal
cd /d "%~dp0\.."
python -m unittest discover -s tests
python -m neutrino_py doctor

