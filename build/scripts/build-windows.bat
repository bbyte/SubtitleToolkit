@echo off
REM Windows build script for SubtitleToolkit
REM This script creates a Windows executable using PyInstaller

echo ========================================
echo SubtitleToolkit Windows Build Script
echo ========================================

REM Set script directory
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%\..\..
set BUILD_DIR=%PROJECT_ROOT%\build
set DIST_DIR=%PROJECT_ROOT%\dist
set SPEC_FILE=%BUILD_DIR%\subtitletoolkit-windows.spec

echo Project root: %PROJECT_ROOT%
echo Build directory: %BUILD_DIR%
echo Distribution directory: %DIST_DIR%
echo Spec file: %SPEC_FILE%

REM Change to project root
cd /d "%PROJECT_ROOT%"

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not available in PATH
    echo Please install Python 3.8+ and ensure it's in your PATH
    pause
    exit /b 1
)

echo Python version:
python --version

REM Check if PyInstaller is available
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install PyInstaller
        pause
        exit /b 1
    )
)

REM Install project dependencies
echo.
echo Installing project dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install project dependencies
    pause
    exit /b 1
)

REM Clean previous builds
echo.
echo Cleaning previous builds...
if exist "%DIST_DIR%" (
    rmdir /s /q "%DIST_DIR%"
)
if exist "build\SubtitleToolkit" (
    rmdir /s /q "build\SubtitleToolkit"
)

REM Run pre-build validation
echo.
echo Running pre-build validation...
python -c "import sys; sys.path.insert(0, 'app'); import main; print('✓ Main module imports successfully')"
if %errorlevel% neq 0 (
    echo ERROR: Pre-build validation failed
    pause
    exit /b 1
)

REM Build the application
echo.
echo Building Windows executable...
echo Command: pyinstaller --clean "%SPEC_FILE%"
pyinstaller --clean "%SPEC_FILE%"

if %errorlevel% neq 0 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

REM Verify the build
set EXE_PATH=%DIST_DIR%\SubtitleToolkit.exe
if not exist "%EXE_PATH%" (
    echo ERROR: Executable not found at %EXE_PATH%
    pause
    exit /b 1
)

echo.
echo Build completed successfully!
echo Executable location: %EXE_PATH%

REM Get file size
for %%A in ("%EXE_PATH%") do (
    set FILE_SIZE=%%~zA
)
echo File size: %FILE_SIZE% bytes

REM Run post-build tests
echo.
echo Running post-build smoke test...
call "%BUILD_DIR%\scripts\test-package-windows.bat"

if %errorlevel% neq 0 (
    echo WARNING: Post-build tests failed
    echo The executable was created but may have issues
) else (
    echo ✓ Post-build tests passed
)

echo.
echo ========================================
echo Windows build complete!
echo ========================================
echo.
echo Next steps:
echo 1. Test the executable: %EXE_PATH%
echo 2. Create installer (optional): Use Inno Setup or similar
echo 3. Sign executable (optional): Use signtool.exe
echo.

pause