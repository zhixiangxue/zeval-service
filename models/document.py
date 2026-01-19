"""Document 数据模型

Document 代表一个上传的 PDF 文件，可以被多次评估。
通过 file_hash 避免重复上传相同文件。
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Document:
    """文档模型
    
    一个文档可以对应多个评估任务（EvalTask）
    """
    id: int
    filename: str                # 原始文件名（如：mortgage_guidelines.pdf）
    file_path: str               # 存储路径（如：storage/uploads/doc_abc123.pdf）
    file_size: int               # 文件大小（字节）
    total_pages: int             # 总页数
    file_hash: str               # 文件 MD5 哈希（用于去重）
    uploaded_at: datetime        # 上传时间
    eval_count: int = 0          # 被评估次数（统计用）
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "filename": self.filename,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "total_pages": self.total_pages,
            "file_hash": self.file_hash,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "eval_count": self.eval_count
        }
