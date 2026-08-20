@echo off
title YTFlow Downloader Runner
echo =====================================================================
echo                 YTFLOW MEDIA DOWNLOADER RUNNER
echo =====================================================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3 is not installed or not added to system PATH.
    echo Please download and install Python 3.11+ from https://www.python.org/
    echo Remember to check "Add Python.exe to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: Check and create venv
if not exist .venv (
    echo [INFO] Virtual environment not found. Creating one in '.venv'...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [INFO] Virtual environment created successfully.
)

:: Activate venv
echo [INFO] Activating virtual environment...
call .venv\Scripts\activate.bat

:: Install requirements
echo [INFO] Verification / Installation of dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install required libraries.
    echo Please check your internet connection and try running again.
    pause
    exit /b 1
)

:: Start browser and FastAPI app
echo.
echo ========================================
echo         YTFLOW SERVER RUNNING
echo        http://127.0.0.1:8000/
echo ========================================
echo.

echo [INFO] Opening downloader webpage...
start http://127.0.0.1:8000
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
