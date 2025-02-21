@echo off
chcp 65001 > nul
title ComfyUI Node Translator - Startup Script

:: Check if Python is installed
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not found. Please install Python 3.7 or higher.
    pause
    exit /b
)

:: Check if virtual environment exists
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b
    )
)

:: Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b
)

:: Check for required dependencies
echo [INFO] Checking dependencies...
pip list > installed_packages.txt 2>&1

setlocal enabledelayedexpansion
set "missing_packages="

:: Read requirements.txt and check each package
for /f "tokens=1,2 delims==" %%a in (requirements.txt) do (
    findstr /i /c:"%%a" installed_packages.txt > nul
    if errorlevel 1 (
        echo [INFO] Installing %%a...
        pip install %%a
        if errorlevel 1 (
            echo [ERROR] Failed to install %%a.
            set "missing_packages=1"
        )
    )
)

:: Clean up temporary files
del installed_packages.txt

:: If there were missing packages, exit
if defined missing_packages (
    echo [ERROR] Some packages could not be installed. Please check the error messages above.
    deactivate
    pause
    exit /b
)

:: Start the main program
echo [INFO] Starting the program...
python main.py

:: If the program crashes, pause to show the error message
if errorlevel 1 (
    echo.
    echo [ERROR] The program has crashed.
    pause
)

:: Deactivate the virtual environment before exiting
deactivate 