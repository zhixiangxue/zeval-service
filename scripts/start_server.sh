#!/bin/bash
# 启动 Mortgage RAG Evaluator API 服务

set -e

echo "=========================================="
echo "Mortgage RAG Evaluator API"
echo "=========================================="
echo ""

# 检查是否在项目根目录
if [ ! -f "api/main.py" ]; then
    echo "错误: 请在 zeval-service 项目根目录下运行此脚本"
    exit 1
fi

# 查找虚拟环境（最多向上查找3层）
VENV_PATH=""
for i in 0 1 2 3; do
    prefix=""
    for j in $(seq 1 $i); do
        prefix="../$prefix"
    done
    
    if [ -d "${prefix}.venv" ]; then
        VENV_PATH="${prefix}.venv"
        break
    fi
done

if [ -z "$VENV_PATH" ]; then
    echo "错误: 未找到虚拟环境 .venv（已查找当前目录及上3层）"
    echo "请先创建虚拟环境: python3.12 -m venv .venv"
    echo "然后安装依赖: source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# 激活虚拟环境
echo "✓ 激活虚拟环境: $VENV_PATH"
source "$VENV_PATH/bin/activate"

# 加载环境变量（如果存在 .env 文件）
if [ -f ".env" ]; then
    echo "✓ 加载环境变量从 .env 文件"
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "⚠ 未找到 .env 文件，使用默认配置"
    echo "  提示: 复制 .env.example 为 .env 并配置"
fi

# 初始化数据库
echo ""
echo "初始化数据库..."
PYTHONPATH=. "$VENV_PATH/bin/python" scripts/init_db.py

# 启动 API 服务
echo ""
echo "启动 API 服务..."
echo "  - API 文档: http://localhost:8000/docs"
echo "  - 健康检查: http://localhost:8000/health"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

"$VENV_PATH/bin/uvicorn" api.main:app --host 0.0.0.0 --port 8000 --reload
