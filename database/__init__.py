"""数据库操作"""
from .connection import get_db_connection, init_database
from .operations import (
    # Document 操作
    create_document,
    get_document_by_id,
    get_document_by_hash,
    get_all_documents,
    increment_eval_count,
    
    # EvalTask 操作
    create_task,
    get_task_by_id,
    get_all_tasks,
    get_pending_tasks,
    claim_next_pending_task,
    update_task_status,
    update_task_progress,
)

__all__ = [
    "get_db_connection",
    "init_database",
    # Document
    "create_document",
    "get_document_by_id",
    "get_document_by_hash",
    "get_all_documents",
    "increment_eval_count",
    # EvalTask
    "create_task",
    "get_task_by_id",
    "get_all_tasks",
    "get_pending_tasks",
    "claim_next_pending_task",
    "update_task_status",
    "update_task_progress",
]
