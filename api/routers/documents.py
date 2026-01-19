"""文档管理接口

提供文档上传、查询等功能
"""
import hashlib
import os
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from PyPDF2 import PdfReader
import database


router = APIRouter()


def get_upload_dir() -> Path:
    """获取上传目录"""
    upload_dir = Path(os.getenv("UPLOAD_DIR", ".data/uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def calculate_file_hash(file_content: bytes) -> str:
    """计算文件的 MD5 哈希"""
    return hashlib.md5(file_content).hexdigest()


def get_pdf_page_count(file_path: str) -> int:
    """获取 PDF 页数"""
    try:
        reader = PdfReader(file_path)
        return len(reader.pages)
    except Exception as e:
        raise ValueError(f"无法读取 PDF 文件: {e}")


@router.post("/documents")
async def create_document(file: UploadFile = File(...)):
    """创建文档（上传 PDF）
    
    如果文件已存在（相同 hash），返回已有文档信息
    """
    # 1. 检查文件类型
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="只支持 PDF 文件")
    
    # 2. 读取文件内容
    file_content = await file.read()
    file_size = len(file_content)
    
    # 检查文件大小限制
    max_size_mb = int(os.getenv("MAX_UPLOAD_SIZE_MB", "100"))
    if file_size > max_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制 ({max_size_mb}MB)"
        )
    
    # 3. 计算文件哈希
    file_hash = calculate_file_hash(file_content)
    
    # 4. 检查文件是否已存在
    existing_doc = database.get_document_by_hash(file_hash)
    if existing_doc:
        return {
            "document_id": existing_doc.id,
            "filename": existing_doc.filename,
            "file_size": existing_doc.file_size,
            "total_pages": existing_doc.total_pages,
            "file_hash": existing_doc.file_hash,
            "message": "文档已存在，无需重复上传"
        }
    
    # 5. 保存文件
    upload_dir = get_upload_dir()
    # 使用原文件名 + hash 前8位（便于查找）
    name_without_ext = Path(file.filename).stem
    ext = Path(file.filename).suffix
    safe_filename = f"{name_without_ext}_{file_hash[:8]}{ext}"
    file_path = upload_dir / safe_filename
    
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    # 6. 获取 PDF 页数
    try:
        total_pages = get_pdf_page_count(str(file_path))
    except ValueError as e:
        # 删除无效文件
        file_path.unlink()
        raise HTTPException(status_code=400, detail=str(e))
    
    # 7. 创建文档记录
    document_id = database.create_document(
        filename=file.filename,
        file_path=str(file_path),
        file_size=file_size,
        total_pages=total_pages,
        file_hash=file_hash
    )
    
    return {
        "document_id": document_id,
        "filename": file.filename,
        "file_path": str(file_path),
        "file_size": file_size,
        "total_pages": total_pages,
        "file_hash": file_hash,
        "message": "文档上传成功"
    }


@router.get("/documents")
def list_documents(limit: int = 50):
    """查询文档列表"""
    documents = database.get_all_documents(limit=limit)
    
    return {
        "total": len(documents),
        "documents": [doc.to_dict() for doc in documents]
    }


@router.get("/documents/{document_id}")
def get_document(document_id: int):
    """查询文档详情"""
    document = database.get_document_by_id(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    # 查询该文档的所有评估任务
    tasks = database.get_all_tasks(document_id=document_id)
    
    return {
        **document.to_dict(),
        "eval_tasks": [
            {
                "task_id": task.id,
                "start_page": task.start_page,
                "end_page": task.end_page,
                "status": task.status.value,
                "avg_score": task.avg_score,
                "created_at": task.created_at.isoformat()
            }
            for task in tasks
        ]
    }
