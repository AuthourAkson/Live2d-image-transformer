@echo off
REM ============================================
REM  Live2D Image Transformer — WebUI 启动 (Windows)
REM ============================================
REM 双击此文件或在命令行运行:
REM   start_webui.bat
REM   start_webui.bat 9000
REM ============================================

setlocal enabledelayedexpansion

cd /d "%~dp0"

set PORT=8000
if not "%~1"=="" set PORT=%~1

REM 检查 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请安装 Python 3.10+
    pause
    exit /b 1
)

REM 检查 venv
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo [INFO] 虚拟环境已激活
)

echo.
echo ============================================
echo    Live2D Image Transformer - WebUI
echo    地址: http://localhost:%PORT%
echo    文档: http://localhost:%PORT%/docs
echo ============================================
echo.

python webui/app.py

pause
