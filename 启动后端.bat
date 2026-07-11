@echo off
chcp 65001 >nul
set "PYDIR=C:\Users\11\python312"
set "PYTHONUTF8=1"

echo ========================================
echo   股票数据后端服务 (免安装版 Python)
echo ========================================
echo.

if not exist "%PYDIR%\python.exe" (
    echo [错误] 找不到 Python: %PYDIR%\python.exe
    echo 请确认免安装版 Python 仍在该目录。
    pause
    exit /b 1
)

echo 服务地址: http://localhost:8000
echo API文档:  http://localhost:8000/docs
echo 按 Ctrl+C 停止服务
echo.

REM 2秒后自动打开前端页面
start "" cmd /c "timeout /t 2 /nobreak >nul && start "" "%~dp0kline-replay.html""

"%PYDIR%\python.exe" "%~dp0backend.py"

pause
