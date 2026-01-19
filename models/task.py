"""EvalTask 数据模型

EvalTask 代表对某个 Document 的一次评估任务。
同一个 Document 可以有多个 EvalTask（不同页码范围、不同配置）。
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"       # 待处理
    RUNNING = "running"       # 执行中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败


@dataclass
class EvalTask:
    """评估任务模型
    
    每个任务关联一个 Document，记录评估配置和结果
    """
    id: int
    document_id: int             # 关联的文档 ID
    
    # 评估配置
    start_page: int | None       # 起始页码（None = 全文档）
    end_page: int | None         # 结束页码
    llm_uri: str                 # 使用的模型（如：openai/gpt-4o-mini）
    num_test_cases: int          # 测试用例数
    
    # 任务状态
    status: TaskStatus
    created_at: datetime
    progress: int = 0                # 进度（0-100）
    started_at: datetime | None = None
    completed_at: datetime | None = None
    
    # 评估结果
    result_path: str | None = None       # 报告路径（Excel）
    dataset_path: str | None = None      # 数据集路径（JSON）
    avg_score: float | None = None       # 平均分
    metrics_summary: dict | None = None  # 各指标得分（JSON）
    error: str | None = None             # 错误信息
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "start_page": self.start_page,
            "end_page": self.end_page,
            "llm_uri": self.llm_uri,
            "num_test_cases": self.num_test_cases,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "progress": self.progress,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result_path": self.result_path,
            "dataset_path": self.dataset_path,
            "avg_score": self.avg_score,
            "metrics_summary": self.metrics_summary,
            "error": self.error
        }
