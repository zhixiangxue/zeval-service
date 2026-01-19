"""FastAPI 应用入口

Mortgage RAG Evaluator API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import documents, tasks
from database import init_database


# 初始化数据库
init_database()

# 创建 FastAPI 应用
app = FastAPI(
    title="Mortgage RAG Evaluator API",
    description="评估 Mortgage 领域 RAG 系统性能的 API 服务",
    version="1.0.0"
)

# CORS 配置（开发环境）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(tasks.router, prefix="/api", tags=["tasks"])


@app.get("/")
def root():
    """根路径"""
    return {
        "message": "Mortgage RAG Evaluator API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
