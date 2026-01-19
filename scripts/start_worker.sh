#!/bin/bash

# Evaluation Worker 启动脚本
# 启动评估任务 Worker，定时拉取并处理待评估任务

set -e  # 遇到错误立即退出

echo "🚀 启动 Evaluation Worker..."

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
    echo "❌ 错误: 未找到虚拟环境 (.venv)"
    echo "请在项目根目录创建虚拟环境: python -m venv .venv"
    exit 1
fi

echo "✓ 找到虚拟环境: $VENV_PATH"

# 激活虚拟环境
source "$VENV_PATH/bin/activate"

# 加载环境变量
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
    echo "✓ 加载环境变量: .env"
fi

# 切换到 zeval-service 目录
cd "$(dirname "$0")/.."

# 初始化数据库（如果需要）
echo "✓ 初始化数据库..."
PYTHONPATH=. "$VENV_PATH/bin/python" scripts/init_db.py

# 启动 Worker
echo ""
echo "================================"
echo "  Evaluation Worker 启动中..."
echo "================================"
echo ""

PYTHONPATH=. "$VENV_PATH/bin/python" -m worker.worker

echo ""
echo "Worker 已停止"
