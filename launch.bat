@echo off
title TOS Solver Launcher

echo ===================================================
echo        TOS Solver - Ultimate Launcher
echo ===================================================
echo.

rem 1. Check Administrator Privileges
net session >nul 2>&1
if %errorLevel% == 0 goto admin_ok

echo ===================================================
echo [WARNING] NOT RUNNING AS ADMINISTRATOR!
echo ===================================================
echo Notice:
echo This solver requires administrator privileges to register
echo global hotkeys (F1~F5) and simulate mouse drags inside emulators.
echo.
echo If hotkeys do not respond or mouse does not move, please
echo close this window, right-click launch.bat and select
echo "Run as administrator".
echo ===================================================
echo.
echo Attempting to start with standard privileges...
echo ---------------------------------------------------
goto admin_end

:admin_ok
echo [OK] Running with Administrator privileges.

:admin_end
echo.

rem 2. Detect Python Installation
set "PYTHON_CMD="

rem (A) Check system PATH
python --version >nul 2>&1
if %errorLevel% neq 0 goto check_local
python -c "import sys; print(sys.version)" >nul 2>&1
if %errorLevel% neq 0 goto check_local
set "PYTHON_CMD=python"
goto python_ok

:check_local
rem (B) Check Local AppData Python installation
if not exist "%LocalAppData%\Programs\Python" goto check_program_files
for /d %%D in ("%LocalAppData%\Programs\Python\Python*") do (
    if exist "%%D\python.exe" (
        set "PYTHON_CMD=%%D\python.exe"
        echo [OK] Found Python in Local AppData: "%%D\python.exe"
        goto python_ok
    )
)

:check_program_files
rem (C) Check Program Files Python installation
if not exist "C:\Program Files\Python" goto check_c_root
for /d %%D in ("C:\Program Files\Python\Python*") do (
    if exist "%%D\python.exe" (
        set "PYTHON_CMD=%%D\python.exe"
        echo [OK] Found Python in Program Files: "%%D\python.exe"
        goto python_ok
    )
)

:check_c_root
rem (D) Check old-style C:\Python installation
for /d %%D in ("C:\Python*") do (
    if exist "%%D\python.exe" (
        set "PYTHON_CMD=%%D\python.exe"
        echo [OK] Found Python in C:\: "%%D\python.exe"
        goto python_ok
    )
)

rem If Python is not found
echo [ERROR] Python was not found on your system!
echo Please download and install Python 3.8+ (3.10 or 3.12 recommended).
echo Download URL: https://www.python.org/downloads/
echo (Important: Check the "Add Python to PATH" box during installation)
echo.
pause
exit /b 1

:python_ok

rem 3. Install dependencies using --user
echo [INFO] Installing required libraries from requirements.txt...
"%PYTHON_CMD%" -m pip install --upgrade pip --user -q
"%PYTHON_CMD%" -m pip install -r requirements.txt --user
if %errorLevel% == 0 goto pip_success

echo.
echo [WARNING] Some dependencies failed to install, but we will try to start.
goto pip_end

:pip_success
echo [OK] Libraries are successfully installed and ready.

:pip_end
echo.
echo ===================================================
echo [START] Launching TOS Solver GUI, please wait...
echo ===================================================
echo.

rem 4. Run main program
"%PYTHON_CMD%" main.py

if %errorLevel% neq 0 (
    echo.
    echo [INFO] Program terminated with exit code: %errorLevel%
    pause
)
