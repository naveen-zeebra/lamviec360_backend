@echo off
echo Starting Job Seeker Gateway (Port 8001)...
IF EXIST "..\new\venv\Scripts\python.exe" (
    SET "PY_CMD=..\new\venv\Scripts\python.exe"
) ELSE IF EXIST "venv\Scripts\python.exe" (
    SET "PY_CMD=venv\Scripts\python.exe"
) ELSE (
    SET "PY_CMD=python"
)
%PY_CMD% run_jobseeker.py
pause
