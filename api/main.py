"""FastAPI 应用入口

Mortgage RAG Evaluator API
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import documents, tasks
from database import init_database


# 初始化数据库
init_database()

# 创建 FastAPI 应用
app = FastAPI(
    title="Mortgage RAG Evaluator API",
    description="RAG evaluation service layer built on top of Zeval framework",
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
app.include_router(documents.router, tags=["documents"])
app.include_router(tasks.router, tags=["tasks"])


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


# ============================================================
# 挂载 Gradio WebUI（可选）
# ============================================================

# 只有在非 Worker 模式下才挂载 WebUI
if os.getenv("ENABLE_WEBUI", "true").lower() == "true":
    try:
        import gradio as gr
        from api.webui import app as gradio_app
        
        # 将 Gradio 挂载到 /ui 路径
        app = gr.mount_gradio_app(app, gradio_app, path="/ui")
        
        print("✓ Web UI 已挂载到 /ui 路径")
        print("  访问地址: http://localhost:8001/ui")
    except ImportError:
        print("⚠ Gradio 未安装，Web UI 不可用")
    except Exception as e:
        print(f"⚠ Web UI 挂载失败: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
