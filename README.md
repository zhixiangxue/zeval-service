# zeval-service

Mortgage RAG 评估服务 - 基于 zeval-ai 框架的业务实现

## 项目简介

zeval-service 是针对 Mortgage 领域 RAG 系统的评估服务，提供端到端的评估流程。

## 核心功能

- **MortgageRAGEvaluator**: 核心评估器，完成 PDF → 评估报告的完整流程
- **Worker**: 定时任务执行器，从数据库拉取任务并执行评估
- **API**: 文件上传和任务状态查询接口

## 快速开始

### 安装依赖

```bash
# 创建虚拟环境
python3.12 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# 安装 zeval-ai 核心库（可编辑模式）
cd ../zeval-ai
pip install -e .

# 安装 zeval-service 依赖
cd ../zeval-service
pip install -r requirements.txt
```

### 启动服务

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 LLM_API_KEY

# 2. 启动 API 服务（包含 Web UI）
./scripts/start_server.ps1  # Windows
# or
./scripts/start_server.sh  # Linux/Mac

# 3. 访问 Web UI
# http://localhost:8001/ui

# 4. 启动 Worker（另一个终端）
./scripts/start_worker.ps1  # Windows
# or
./scripts/start_worker.sh  # Linux/Mac
```

### Web UI 使用

1. 访问 http://localhost:8001/ui
2. 上传 PDF 文档
3. 创建评估任务
4. 查看评估结果

### API 文档

- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## 项目结构

```
zeval-service/
├── api/                # HTTP 接口
│   ├── routers/        # 路由模块
│   ├── main.py         # FastAPI 应用
│   └── webui.py        # Gradio Web UI
├── database/           # 数据库操作
├── evaluator/          # 核心评估器
├── models/             # 数据模型
├── worker/             # 定时任务
├── scripts/            # 启动脚本
└── .env.example        # 配置模板
```

## 配置选项

在 `.env` 文件中配置：

```bash
# LLM 配置
LLM_URI=openai/gpt-4o-mini
LLM_API_KEY=your_api_key

# 任务配置
NUM_TEST_CASES=50

# Web UI 配置
ENABLE_WEBUI=true  # Worker 模式下设为 false
```

## 依赖

- zeval-ai: 评估框架（核心库）
- Python 3.12+
