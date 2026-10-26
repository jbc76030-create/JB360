@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Ejecute primero INSTALAR_WINDOWS.cmd.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" iniciar.py
pause
