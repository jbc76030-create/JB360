@echo off
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  set "PYTHON_LAUNCHER=py -3"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Instale Python 3.11 o posterior antes de continuar.
    pause
    exit /b 1
  )
  set "PYTHON_LAUNCHER=python"
)
if not exist ".venv\Scripts\python.exe" %PYTHON_LAUNCHER% -m venv .venv
if errorlevel 1 (pause & exit /b 1)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (pause & exit /b 1)
echo Instalacion lista. Se abrira el servidor y se pedira la clave solo al crear la base.
".venv\Scripts\python.exe" iniciar.py
pause
