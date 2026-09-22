@echo off
echo ========================================================
echo   Starting Job Portal Multi-Gateway API Architecture
echo ========================================================

IF EXIST "..\new\venv\Scripts\python.exe" (
    SET "PY_CMD=..\new\venv\Scripts\python.exe"
) ELSE IF EXIST "venv\Scripts\python.exe" (
    SET "PY_CMD=venv\Scripts\python.exe"
) ELSE (
    SET "PY_CMD=python"
)

%PY_CMD% run.py
pause
