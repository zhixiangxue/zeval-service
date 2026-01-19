"""数据库 CRUD 操作

提供 Document 和 EvalTask 的增删改查功能。
"""
import json
from datetime import datetime
from typing import Optional
from models import Document, EvalTask, TaskStatus
from .connection import get_db_connection


# ============================================================
# Document 操作
# ============================================================

def create_document(
    filename: str,
    file_path: str,
    file_size: int,
    total_pages: int,
    file_hash: str
) -> int:
    """创建文档记录
    
    Args:
        filename: 原始文件名
        file_path: 存储路径
        file_size: 文件大小（字节）
        total_pages: 总页数
        file_hash: 文件 MD5 哈希
    
    Returns:
        document_id: 创建的文档 ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO documents (filename, file_path, file_size, total_pages, file_hash)
        VALUES (?, ?, ?, ?, ?)
    """, (filename, file_path, file_size, total_pages, file_hash))
    
    document_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return document_id


def get_document_by_id(document_id: int) -> Optional[Document]:
    """根据 ID 查询文档"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return Document(
        id=row["id"],
        filename=row["filename"],
        file_path=row["file_path"],
        file_size=row["file_size"],
        total_pages=row["total_pages"],
        file_hash=row["file_hash"],
        uploaded_at=datetime.fromisoformat(row["uploaded_at"]),
        eval_count=row["eval_count"]
    )


def get_document_by_hash(file_hash: str) -> Optional[Document]:
    """根据文件哈希查询文档（用于去重）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM documents WHERE file_hash = ?", (file_hash,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return Document(
        id=row["id"],
        filename=row["filename"],
        file_path=row["file_path"],
        file_size=row["file_size"],
        total_pages=row["total_pages"],
        file_hash=row["file_hash"],
        uploaded_at=datetime.fromisoformat(row["uploaded_at"]),
        eval_count=row["eval_count"]
    )


def get_all_documents(limit: int = 100) -> list[Document]:
    """查询所有文档列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM documents 
        ORDER BY uploaded_at DESC 
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        Document(
            id=row["id"],
            filename=row["filename"],
            file_path=row["file_path"],
            file_size=row["file_size"],
            total_pages=row["total_pages"],
            file_hash=row["file_hash"],
            uploaded_at=datetime.fromisoformat(row["uploaded_at"]),
            eval_count=row["eval_count"]
        )
        for row in rows
    ]


def increment_eval_count(document_id: int):
    """增加文档的评估次数"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE documents 
        SET eval_count = eval_count + 1 
        WHERE id = ?
    """, (document_id,))
    
    conn.commit()
    conn.close()


# ============================================================
# EvalTask 操作
# ============================================================

def create_task(
    document_id: int,
    llm_uri: str,
    num_test_cases: int,
    start_page: Optional[int] = None,
    end_page: Optional[int] = None
) -> int:
    """创建评估任务
    
    Args:
        document_id: 关联的文档 ID
        llm_uri: 使用的模型
        num_test_cases: 测试用例数
        start_page: 起始页码（可选）
        end_page: 结束页码（可选）
    
    Returns:
        task_id: 创建的任务 ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO eval_tasks (
            document_id, start_page, end_page, llm_uri, num_test_cases, status
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (document_id, start_page, end_page, llm_uri, num_test_cases, TaskStatus.PENDING.value))
    
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # 增加文档的评估次数
    increment_eval_count(document_id)
    
    return task_id


def get_task_by_id(task_id: int) -> Optional[EvalTask]:
    """根据 ID 查询任务"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM eval_tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return _row_to_task(row)


def get_all_tasks(
    document_id: Optional[int] = None,
    status: Optional[TaskStatus] = None,
    limit: int = 100
) -> list[EvalTask]:
    """查询任务列表
    
    Args:
        document_id: 过滤文档 ID（可选）
        status: 过滤状态（可选）
        limit: 返回数量限制
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM eval_tasks WHERE 1=1"
    params = []
    
    if document_id is not None:
        query += " AND document_id = ?"
        params.append(document_id)
    
    if status is not None:
        query += " AND status = ?"
        params.append(status.value if isinstance(status, TaskStatus) else status)
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [_row_to_task(row) for row in rows]


def get_pending_tasks(limit: int = 10) -> list[EvalTask]:
    """获取待处理任务（Worker 使用）"""
    return get_all_tasks(status=TaskStatus.PENDING, limit=limit)


def claim_next_pending_task() -> Optional[EvalTask]:
    """原子性获取下一个 pending 任务并立即更新为 running
    
    使用数据库事务保证原子性，避免并发冲突。
    多个 Worker 并发运行时，每个 Worker 只会获取不同的任务。
    
    Returns:
        EvalTask: 获取到的任务，如果没有待处理任务则返回 None
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 开启事务（SQLite 默认自动开启）
        # 1. 查询一个 pending 任务
        cursor.execute("""
            SELECT * FROM eval_tasks 
            WHERE status = ? 
            ORDER BY created_at ASC 
            LIMIT 1
        """, (TaskStatus.PENDING.value,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        
        task_id = row["id"]
        
        # 2. 立即更新为 running，记录开始时间
        cursor.execute("""
            UPDATE eval_tasks 
            SET status = ?, started_at = ?, progress = 0
            WHERE id = ?
        """, (TaskStatus.RUNNING.value, datetime.now().isoformat(), task_id))
        
        conn.commit()
        
        # 3. 返回任务对象
        task = _row_to_task(row)
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        task.progress = 0
        
        return task
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def update_task_progress(task_id: int, progress: int):
    """更新任务进度（快速方法）
    
    Args:
        task_id: 任务 ID
        progress: 进度百分比（0-100）
    """
    update_task_status(task_id, progress=progress)


def update_task_status(
    task_id: int,
    status: Optional[TaskStatus] = None,
    progress: Optional[int] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
    result_path: Optional[str] = None,
    dataset_path: Optional[str] = None,
    avg_score: Optional[float] = None,
    metrics_summary: Optional[dict] = None,
    error: Optional[str] = None
):
    """更新任务状态和结果
    
    只更新提供的字段，None 表示不更新
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if status is not None:
        updates.append("status = ?")
        params.append(status.value if isinstance(status, TaskStatus) else status)
    
    if progress is not None:
        updates.append("progress = ?")
        params.append(progress)
    
    if started_at is not None:
        updates.append("started_at = ?")
        params.append(started_at.isoformat())
    
    if completed_at is not None:
        updates.append("completed_at = ?")
        params.append(completed_at.isoformat())
    
    if result_path is not None:
        updates.append("result_path = ?")
        params.append(result_path)
    
    if dataset_path is not None:
        updates.append("dataset_path = ?")
        params.append(dataset_path)
    
    if avg_score is not None:
        updates.append("avg_score = ?")
        params.append(avg_score)
    
    if metrics_summary is not None:
        updates.append("metrics_summary = ?")
        params.append(json.dumps(metrics_summary))
    
    if error is not None:
        updates.append("error = ?")
        params.append(error)
    
    if not updates:
        conn.close()
        return
    
    query = f"UPDATE eval_tasks SET {', '.join(updates)} WHERE id = ?"
    params.append(task_id)
    
    cursor.execute(query, params)
    conn.commit()
    conn.close()


def _row_to_task(row) -> EvalTask:
    """将数据库行转换为 EvalTask 对象"""
    return EvalTask(
        id=row["id"],
        document_id=row["document_id"],
        start_page=row["start_page"],
        end_page=row["end_page"],
        llm_uri=row["llm_uri"],
        num_test_cases=row["num_test_cases"],
        status=TaskStatus(row["status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        progress=row["progress"] if "progress" in row.keys() else 0,
        started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
        completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        result_path=row["result_path"],
        dataset_path=row["dataset_path"],
        avg_score=row["avg_score"],
        metrics_summary=json.loads(row["metrics_summary"]) if row["metrics_summary"] else None,
        error=row["error"]
    )
