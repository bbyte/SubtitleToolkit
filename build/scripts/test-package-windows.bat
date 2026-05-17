@echo off
REM Windows-specific package testing script

echo ========================================
echo SubtitleToolkit Windows Package Test
echo ========================================

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%\..\..
set DIST_DIR=%PROJECT_ROOT%\dist

cd /d "%PROJECT_ROOT%"

REM Find the executable
set EXECUTABLE_PATH=%DIST_DIR%\SubtitleToolkit.exe
if not exist "%EXECUTABLE_PATH%" (
    echo ERROR: Executable not found at %EXECUTABLE_PATH%
    echo Please run the build script first
    pause
    exit /b 1
)

echo Testing executable: %EXECUTABLE_PATH%
echo.

REM Run the test framework
python "%SCRIPT_DIR%\test-package.py" --executable "%EXECUTABLE_PATH%" --verbose

if %errorlevel% neq 0 (
    echo.
    echo ❌ Package tests failed
    pause
    exit /b 1
)

echo.
echo ✅ Package tests passed
echo.

REM Additional Windows-specific tests
echo Running Windows-specific tests...

REM Test if executable runs without console window
echo Testing GUI mode...
start /wait "" "%EXECUTABLE_PATH%" --version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ GUI mode test passed
) else (
    echo ❌ GUI mode test failed
)

REM Test file associations (if available)
echo Testing file associations...
assoc .srt >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ SRT file association available
) else (
    echo ℹ️  SRT file association not configured
)

REM Check for required DLLs
echo Checking for required DLLs...
dumpbin /dependents "%EXECUTABLE_PATH%" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Executable dependencies check completed
) else (
    echo ℹ️  Could not check dependencies (dumpbin not available)
)

echo.
echo ========================================
echo Windows package testing complete
echo ========================================

pause