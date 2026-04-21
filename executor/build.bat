@echo off
echo ====================================
echo   PC Executor Build Tool
echo   Supports PC and Android modes
echo ====================================
echo.

echo [1/4] Checking Python...
python --version
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)
echo [OK] Python installed
echo.

echo [2/4] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed
echo.

echo [3/4] Checking tkinter...
python -c "import tkinter"
if errorlevel 1 (
    echo [WARNING] tkinter not found, GUI may not work
    echo Please install Python with tcl/tk support
    echo.
) else (
    echo [OK] tkinter installed
    echo.
)

echo [4/4] Building...
echo Installing pyinstaller...
pip install pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install pyinstaller
    pause
    exit /b 1
)
echo.

echo Starting build...
python -m PyInstaller PCExecutor.spec --clean
if errorlevel 1 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)

echo.
echo ====================================
echo  Build Complete!
echo  Output: dist\PCExecutor.exe
echo ====================================
echo.
echo Usage:
echo   Double-click: Config dialog to select mode
echo   Command line:
echo     PCExecutor.exe -t pc      - Start PC automation
echo     PCExecutor.exe -t android - Start Android automation
echo     PCExecutor.exe --no-gui   - Run without GUI
echo.
pause
