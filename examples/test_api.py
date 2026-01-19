"""API 测试脚本

测试文档上传、任务创建、任务查询等功能

Usage:
    # 先启动 API 服务
    uvicorn api.main:app --reload --port 8000
    
    # 然后运行测试
    python -m examples.test_api
"""
import requests
import json
from pathlib import Path


BASE_URL = "http://localhost:8000"


def test_health():
    """测试健康检查"""
    print("\n" + "="*80)
    print("测试 1: 健康检查")
    print("="*80)
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200


def test_upload_document():
    """测试文档上传"""
    print("\n" + "="*80)
    print("测试 2: 文档上传")
    print("="*80)
    
    # 提示用户输入文件路径
    print("\n请输入要上传的 PDF 文件路径:")
    file_path = input("> ").strip().strip('"').strip("'")
    
    if not Path(file_path).exists():
        print(f"文件不存在: {file_path}")
        return None
    
    with open(file_path, "rb") as f:
        files = {"file": (Path(file_path).name, f, "application/pdf")}
        response = requests.post(f"{BASE_URL}/api/documents/upload", files=files)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    if response.status_code == 200:
        document_id = response.json()["document_id"]
        print(f"\n✅ 文档上传成功，document_id: {document_id}")
        return document_id
    else:
        print("\n❌ 文档上传失败")
        return None


def test_list_documents():
    """测试文档列表"""
    print("\n" + "="*80)
    print("测试 3: 查询文档列表")
    print("="*80)
    
    response = requests.get(f"{BASE_URL}/api/documents?limit=10")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total: {data['total']}")
        for doc in data['documents']:
            print(f"  - ID: {doc['id']}, Filename: {doc['filename']}, Pages: {doc['total_pages']}")
    else:
        print(f"Error: {response.text}")


def test_create_task(document_id: int):
    """测试创建任务"""
    print("\n" + "="*80)
    print("测试 4: 创建评估任务")
    print("="*80)
    
    # 输入页码范围（可选）
    print("\n页码范围 (格式: 5-20，直接回车评估整个文档):")
    page_range = input("> ").strip()
    
    payload = {"document_id": document_id}
    
    if page_range:
        if '-' in page_range:
            parts = page_range.split('-')
            payload["start_page"] = int(parts[0].strip())
            payload["end_page"] = int(parts[1].strip())
    
    response = requests.post(f"{BASE_URL}/api/tasks/create", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    if response.status_code == 200:
        task_id = response.json()["task_id"]
        print(f"\n✅ 任务创建成功，task_id: {task_id}")
        return task_id
    else:
        print("\n❌ 任务创建失败")
        return None


def test_get_task(task_id: int):
    """测试查询任务详情"""
    print("\n" + "="*80)
    print("测试 5: 查询任务详情")
    print("="*80)
    
    response = requests.get(f"{BASE_URL}/api/tasks/{task_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")


def test_list_pending_tasks():
    """测试查询待处理任务队列"""
    print("\n" + "="*80)
    print("测试 6: 查询待处理任务队列")
    print("="*80)
    
    response = requests.get(f"{BASE_URL}/api/tasks/queue/pending?limit=10")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total: {data['total']}")
        for task in data['tasks']:
            print(f"  - Task ID: {task['id']}, Status: {task['status']}, "
                  f"Document: {task['document_filename']}")
    else:
        print(f"Error: {response.text}")


def test_update_task(task_id: int):
    """测试更新任务状态"""
    print("\n" + "="*80)
    print("测试 7: 更新任务状态")
    print("="*80)
    
    payload = {
        "status": "running",
        "started_at": "2026-01-15T10:30:00"
    }
    
    response = requests.patch(f"{BASE_URL}/api/tasks/{task_id}", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")


def main():
    """主测试流程"""
    print("\n" + "="*80)
    print("Mortgage RAG Evaluator - API 测试")
    print("="*80)
    
    try:
        # 1. 健康检查
        test_health()
        
        # 2. 上传文档
        document_id = test_upload_document()
        if not document_id:
            print("\n测试中止：文档上传失败")
            return
        
        # 3. 查询文档列表
        test_list_documents()
        
        # 4. 创建任务
        task_id = test_create_task(document_id)
        if not task_id:
            print("\n测试中止：任务创建失败")
            return
        
        # 5. 查询任务详情
        test_get_task(task_id)
        
        # 6. 查询待处理任务
        test_list_pending_tasks()
        
        # 7. 更新任务状态
        test_update_task(task_id)
        
        # 8. 再次查询任务详情
        test_get_task(task_id)
        
        print("\n" + "="*80)
        print("✅ 所有测试完成！")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
