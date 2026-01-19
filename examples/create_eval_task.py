"""创建评估任务 - 用于测试 Worker

简单脚本：上传文档 → 创建评估任务 → 退出
Worker 会自动拉取并处理任务

Usage:
    python examples/create_eval_task.py
"""
import requests
import json
from pathlib import Path


BASE_URL = "http://localhost:8000"


def upload_document(file_path: str) -> int | None:
    """上传文档"""
    print("\n📤 上传文档...")
    
    if not Path(file_path).exists():
        print(f"❌ 文件不存在: {file_path}")
        return None
    
    with open(file_path, "rb") as f:
        files = {"file": (Path(file_path).name, f, "application/pdf")}
        response = requests.post(f"{BASE_URL}/api/documents/upload", files=files)
    
    if response.status_code == 200:
        data = response.json()
        document_id = data["document_id"]
        print(f"✅ 文档上传成功")
        print(f"   Document ID: {document_id}")
        print(f"   文件名: {data['filename']}")
        print(f"   总页数: {data['total_pages']}")
        return document_id
    else:
        print(f"❌ 上传失败: {response.text}")
        return None


def create_task(document_id: int, start_page: int = None, end_page: int = None) -> int | None:
    """创建评估任务"""
    print("\n📋 创建评估任务...")
    
    payload = {"document_id": document_id}
    if start_page:
        payload["start_page"] = start_page
    if end_page:
        payload["end_page"] = end_page
    
    response = requests.post(f"{BASE_URL}/api/tasks/create", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        task_id = data["task_id"]
        print(f"✅ 任务创建成功")
        print(f"   Task ID: {task_id}")
        print(f"   状态: {data['status']}")
        if start_page or end_page:
            print(f"   页码范围: {start_page or 1} - {end_page or '最后一页'}")
        return task_id
    else:
        print(f"❌ 创建失败: {response.text}")
        return None


def main():
    """主流程"""
    print("="*80)
    print("创建评估任务 - Worker 测试")
    print("="*80)
    
    # 1. 输入 PDF 文件路径
    print("\n请输入 PDF 文件路径:")
    file_path = input("> ").strip().strip('"').strip("'")
    
    # 2. 上传文档
    document_id = upload_document(file_path)
    if not document_id:
        return
    
    # 3. 输入页码范围（可选）
    print("\n请输入页码范围 (格式: 起始-结束，如 10-20，直接回车评估整个文档):")
    page_range = input("> ").strip()
    
    start_page = None
    end_page = None
    if page_range and '-' in page_range:
        parts = page_range.split('-')
        start_page = int(parts[0].strip())
        end_page = int(parts[1].strip())
    
    # 4. 创建任务
    task_id = create_task(document_id, start_page, end_page)
    if not task_id:
        return
    
    # 5. 完成
    print("\n" + "="*80)
    print("✅ 任务已创建！")
    print("="*80)
    print("\nWorker 会自动拉取并处理这个任务。")
    print("你可以通过以下方式查看任务状态：")
    print(f"  1. 查看 Worker 日志")
    print(f"  2. 访问 API: GET {BASE_URL}/api/tasks/{task_id}")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  已取消")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
