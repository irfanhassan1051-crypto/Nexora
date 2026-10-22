@echo off
set "APP_DIR=%~dp0"
if exist "%APP_DIR%dist_final\Nexora\Nexora.exe" (
    start "" "%APP_DIR%dist_final\Nexora\Nexora.exe"
    exit /b
)
if exist "%APP_DIR%dist\Nexora\Nexora.exe" (
    start "" "%APP_DIR%dist\Nexora\Nexora.exe"
    exit /b
)
if exist "%APP_DIR%.venv\Scripts\python.exe" (
    "%APP_DIR%.venv\Scripts\python.exe" "%APP_DIR%desktop_app.py"
    exit /b
)
python "%APP_DIR%desktop_app.py"
