#!/bin/bash

echo "========================================"
echo "股票数据后端服务启动脚本"
echo "========================================"
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "[错误] 未找到Python，请先安装Python 3.8+"
    exit 1
fi

PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo "[1/3] 检查依赖..."
if ! $PYTHON_CMD -c "import fastapi" 2>/dev/null; then
    echo "[提示] 正在安装依赖包..."
    $PYTHON_CMD -m pip install -r requirements.txt
else
    echo "[OK] 依赖已安装"
fi

echo ""
echo "[2/3] 启动后端服务..."
echo ""
echo "========================================"
echo "服务地址: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"
echo "========================================"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

$PYTHON_CMD backend.py
