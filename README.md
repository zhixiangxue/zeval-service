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
source .venv/bin/activate

# 安装 zeval-ai 核心库（可编辑模式）
cd ../zeval-ai
pip install -e .

# 安装 zeval-service 依赖
cd ../zeval-service
pip install -r requirements.txt

# 注意：requirements.txt 会自动升级 PyTorch 到 2.5+，解决与 docling 的兼容性问题
```

### 单文件评估

```bash
# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 OPENAI_API_KEY

# 运行评估脚本（注意：必须在 zeval-service 目录下执行）
python -m examples.eval_single
```

### 配置

在 `.env` 文件中配置：
```
OPENAI_API_KEY=your_api_key
```

## 项目结构

```
zeval-service/
├── evaluator/          # 核心评估器
├── worker/             # 定时任务
├── api/                # HTTP 接口
├── models/             # 数据模型
├── storage/            # 文件存储
└── examples/           # 使用示例
```

## 依赖

- zeval-ai: 评估框架（核心库）
- Python 3.12+
