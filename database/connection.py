"""数据库连接管理

使用 SQLite 作为数据库，提供连接管理和表初始化功能。
"""
import sqlite3
import os
from pathlib import Path


def get_db_path() -> str:
    """获取数据库文件路径
    
    从环境变量读取，默认为 .data/evaluations.db
    """
    return os.getenv("DB_PATH", ".data/evaluations.db")


def get_db_connection() -> sqlite3.Connection:
    """获取数据库连接
    
    自动创建数据库文件和父目录（如果不存在）
    """
    db_path = get_db_path()
    
    # 确保父目录存在
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    # 创建连接
    conn = sqlite3.Connection(db_path)
    conn.row_factory = sqlite3.Row  # 支持按列名访问
    return conn


def init_database():
    """初始化数据库表结构
    
    创建 documents 和 eval_tasks 两张表
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 创建 documents 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL UNIQUE,
            file_size INTEGER NOT NULL,
            total_pages INTEGER NOT NULL,
            file_hash TEXT NOT NULL UNIQUE,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            eval_count INTEGER DEFAULT 0
        )
    """)
    
    # 创建 file_hash 索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_file_hash 
        ON documents(file_hash)
    """)
    
    # 创建 eval_tasks 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eval_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            
            -- 评估配置
            start_page INTEGER,
            end_page INTEGER,
            llm_uri TEXT NOT NULL,
            num_test_cases INTEGER NOT NULL,
            
            -- 任务状态
            status TEXT NOT NULL,
            progress INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            
            -- 评估结果
            result_path TEXT,
            dataset_path TEXT,
            avg_score REAL,
            metrics_summary TEXT,
            error TEXT,
            
            FOREIGN KEY (document_id) REFERENCES documents(id)
        )
    """)
    
    # 创建索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_document_id 
        ON eval_tasks(document_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_status 
        ON eval_tasks(status)
    """)
    
    conn.commit()
    conn.close()
    
    print(f"✅ 数据库初始化完成: {get_db_path()}")


if __name__ == "__main__":
    # 直接运行此文件可初始化数据库
    init_database()
