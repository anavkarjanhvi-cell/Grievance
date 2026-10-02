@echo off
REM ============================================================
REM  SIH26 GrievanceAI - Local Deployment Script (Windows)
REM ============================================================
cd /d "%~dp0backend"

if not exist venv (
    echo Creating Python virtual environment...
    python -m venv venv
)

call venv\Scripts\activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo Dependencies installed.

echo.
echo ========================================
echo   Server starting at: http://localhost:8000
echo   API Docs:           http://localhost:8000/docs
echo   Citizen Portal:     http://localhost:8000/
echo ========================================
echo.

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
