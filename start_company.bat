@echo off
echo Starting Company Gateway (Port 8002)...
IF EXIST "..\new\venv\Scripts\python.exe" (
    SET "PY_CMD=..\new\venv\Scripts\python.exe"
) ELSE IF EXIST "venv\Scripts\python.exe" (
    SET "PY_CMD=venv\Scripts\python.exe"
) ELSE (
    SET "PY_CMD=python"
)
%PY_CMD% run_company.py
pause
