@echo off
title Port-Wise Trade Analytics - One-Click Setup
echo =======================================================================
echo     PORT-WISE TRADE ANALYTICS - SYSTEM SETUP
echo =======================================================================
echo.

:: Check Python environment and select best version (preferring 3.12 for pre-compiled library wheels)
set PYTHON_CMD=
py -3.12 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py -3.12
    echo Found Python 3.12. Using it to avoid library compile issues.
    goto venv_creation
)
py -3.13 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py -3.13
    echo Found Python 3.13. Using it to avoid library compile issues.
    goto venv_creation
)
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    echo Using default system Python.
    goto venv_creation
)

echo [ERROR] Python is not installed or not in system PATH.
echo Please install Python 3.12 or 3.13 and try again.
pause
exit /b 1

:venv_creation
:: Clean up old virtual environment if it exists
if exist .venv (
    echo Cleaning up old virtual environment...
    rmdir /s /q .venv
)

:: Step 1: Create Virtual Environment
echo [1/4] Creating virtual environment (.venv) using %PYTHON_CMD%...
%PYTHON_CMD% -m venv .venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)
echo      Virtual environment created successfully.
echo.

:: Step 2: Install dependencies
echo [2/4] Installing dependencies...
call .venv\Scripts\activate

echo      Installing ETL requirements...
pip install -r etl/requirements.txt

echo      Installing Backend requirements...
pip install -r backend/requirements.txt

echo      Installing Frontend requirements...
pip install -r frontend/requirements.txt

if %errorlevel% neq 0 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)
echo      All packages installed successfully.
echo.

:: Step 3: Run ETL Pipeline
echo [3/4] Running ETL Pipeline (Generating Database)...
.venv\Scripts\python.exe etl/etl_pipeline.py
if %errorlevel% neq 0 (
    echo [ERROR] ETL pipeline execution failed.
    pause
    exit /b 1
)
echo.

:: Step 4: Complete
echo [4/4] Setup complete!
echo =======================================================================
echo  To run the services, open two terminal windows and execute:
echo.
echo  TERMINAL 1 (Start API Backend):
echo     .venv\Scripts\activate
echo     uvicorn backend.main:app --reload --port 8000
echo.
echo  TERMINAL 2 (Start Streamlit Dashboard):
echo     .venv\Scripts\activate
echo     streamlit run frontend/app.py
echo.
echo  Note: The UI will run even if the API isn't running by falling back
echo  directly to the SQLite database.
echo =======================================================================
echo.
pause
