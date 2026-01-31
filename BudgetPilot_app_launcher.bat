@echo off
cd /d "%~dp0"

".venv\Scripts\python.exe" "src\budgetpilot\app.py"

echo.
echo --- El programa ha terminado. Pulsa una tecla para cerrar ---
pause >nul