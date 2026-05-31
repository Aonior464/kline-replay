@echo off
chcp 65001 >nul
echo ========================================
echo 股票数据后端服务启动脚本
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo [1/3] 检查依赖...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖包...
    pip install -r requirements.txt
) else (
    echo [OK] 依赖已安装
)

echo.
echo [2/3] 启动后端服务...
echo.
echo ========================================
echo 服务地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo ========================================
echo.
echo 按 Ctrl+C 停止服务
echo.

REM 2秒后自动打开网页
start "" cmd /c "timeout /t 2 /nobreak >nul && start "" "%~dp0kline-replay.html""

python backend.py

pause
