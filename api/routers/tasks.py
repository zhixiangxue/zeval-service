"""任务管理接口

提供评估任务的创建、查询、更新等功能
"""
import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models import TaskStatus
import database


router = APIRouter()


# ============================================================
# Request/Response 模型
# ============================================================

class CreateTaskRequest(BaseModel):
    """创建任务请求"""
    document_id: int
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    llm_uri: Optional[str] = None
    num_test_cases: Optional[int] = None


class UpdateTaskRequest(BaseModel):
    """更新任务请求"""
    status: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result_path: Optional[str] = None
    dataset_path: Optional[str] = None
    avg_score: Optional[float] = None
    metrics_summary: Optional[dict] = None
    error: Optional[str] = None


# ============================================================
# API 端点
# ============================================================

@router.post("/tasks/create")
def create_task(req: CreateTaskRequest):
    """创建评估任务
    
    创建一个新的评估任务，关联到指定的文档
    """
    # 1. 检查文档是否存在
    document = database.get_document_by_id(req.document_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    # 2. 验证页码范围
    if req.start_page is not None or req.end_page is not None:
        start = req.start_page or 1
        end = req.end_page or document.total_pages
        
        if start < 1 or end > document.total_pages:
            raise HTTPException(
                status_code=400,
                detail=f"页码范围无效，文档共 {document.total_pages} 页"
            )
        
        if start > end:
            raise HTTPException(
                status_code=400,
                detail="起始页不能大于结束页"
            )
    
    # 3. 使用默认配置（如果未提供）
    llm_uri = req.llm_uri or os.getenv("LLM_URI", "openai/gpt-4o-mini")
    num_test_cases = req.num_test_cases or int(os.getenv("NUM_TEST_CASES", "50"))
    
    # 4. 创建任务
    task_id = database.create_task(
        document_id=req.document_id,
        llm_uri=llm_uri,
        num_test_cases=num_test_cases,
        start_page=req.start_page,
        end_page=req.end_page
    )
    
    return {
        "task_id": task_id,
        "document_id": req.document_id,
        "status": "pending",
        "message": "评估任务创建成功"
    }


@router.get("/tasks/queue/pending")
def list_pending_tasks(limit: int = 10):
    """查询待处理任务队列
    
    专门用于 Worker 拉取待处理任务
    """
    tasks = database.get_pending_tasks(limit=limit)
    
    # 获取文档信息
    doc_map = {}
    if tasks:
        doc_ids = list(set(task.document_id for task in tasks))
        for doc_id in doc_ids:
            doc = database.get_document_by_id(doc_id)
            if doc:
                doc_map[doc_id] = doc.filename
    
    return {
        "total": len(tasks),
        "tasks": [
            {
                **task.to_dict(),
                "document_filename": doc_map.get(task.document_id, "Unknown")
            }
            for task in tasks
        ]
    }


@router.get("/tasks/{task_id}")
def get_task(task_id: int):
    """查询任务详情"""
    task = database.get_task_by_id(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 获取关联的文档信息
    document = database.get_document_by_id(task.document_id)
    
    result = task.to_dict()
    if document:
        result["document_filename"] = document.filename
    
    return result


@router.get("/tasks")
def list_tasks(
    document_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100
):
    """查询任务列表
    
    Args:
        document_id: 过滤文档 ID（可选）
        status: 过滤状态（可选）: pending, running, completed, failed
        limit: 返回数量限制
    """
    # 验证 status
    task_status = None
    if status:
        try:
            task_status = TaskStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的状态值，支持: {[s.value for s in TaskStatus]}"
            )
    
    tasks = database.get_all_tasks(
        document_id=document_id,
        status=task_status,
        limit=limit
    )
    
    # 获取文档信息（用于显示文件名）
    doc_map = {}
    if tasks:
        doc_ids = list(set(task.document_id for task in tasks))
        for doc_id in doc_ids:
            doc = database.get_document_by_id(doc_id)
            if doc:
                doc_map[doc_id] = doc.filename
    
    return {
        "total": len(tasks),
        "tasks": [
            {
                **task.to_dict(),
                "document_filename": doc_map.get(task.document_id, "Unknown")
            }
            for task in tasks
        ]
    }


@router.patch("/tasks/{task_id}")
def update_task(task_id: int, req: UpdateTaskRequest):
    """更新任务状态和结果
    
    支持部分更新，只更新提供的字段
    """
    # 1. 检查任务是否存在
    task = database.get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 2. 验证 status
    task_status = None
    if req.status:
        try:
            task_status = TaskStatus(req.status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的状态值，支持: {[s.value for s in TaskStatus]}"
            )
    
    # 3. 解析时间字段
    started_at = None
    if req.started_at:
        try:
            started_at = datetime.fromisoformat(req.started_at)
        except ValueError:
            raise HTTPException(status_code=400, detail="started_at 格式错误")
    
    completed_at = None
    if req.completed_at:
        try:
            completed_at = datetime.fromisoformat(req.completed_at)
        except ValueError:
            raise HTTPException(status_code=400, detail="completed_at 格式错误")
    
    # 4. 更新任务
    database.update_task_status(
        task_id=task_id,
        status=task_status,
        started_at=started_at,
        completed_at=completed_at,
        result_path=req.result_path,
        dataset_path=req.dataset_path,
        avg_score=req.avg_score,
        metrics_summary=req.metrics_summary,
        error=req.error
    )
    
    return {
        "task_id": task_id,
        "status": req.status or task.status.value,
        "message": "任务状态更新成功"
    }
