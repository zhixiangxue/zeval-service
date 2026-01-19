"""Worker 集成测试

完整流程测试：
1. 上传文档
2. 创建评估任务
3. 启动 Worker（需手动）
4. 监控任务进度
5. 查看评估结果
"""

import time
import requests
from pathlib import Path


BASE_URL = "http://localhost:8000"


def upload_test_document():
    """上传测试文档"""
    print("\n" + "="*80)
    print("步骤 1: 上传测试文档")
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
    
    if response.status_code == 200:
        data = response.json()
        document_id = data["document_id"]
        print(f"\n✅ 文档上传成功")
        print(f"   Document ID: {document_id}")
        print(f"   文件名: {data['filename']}")
        print(f"   总页数: {data['total_pages']}")
        return document_id
    else:
        print(f"\n❌ 上传失败: {response.text}")
        return None


def create_evaluation_task(document_id: int):
    """创建评估任务"""
    print("\n" + "="*80)
    print("步骤 2: 创建评估任务")
    print("="*80)
    
    # 输入页码范围（可选）
    print("\n页码范围 (格式: 5-20，直接回车评估整个文档):")
    page_range = input("> ").strip()
    
    payload = {"document_id": document_id}
    
    if page_range and '-' in page_range:
        parts = page_range.split('-')
        payload["start_page"] = int(parts[0].strip())
        payload["end_page"] = int(parts[1].strip())
    
    response = requests.post(f"{BASE_URL}/api/tasks/create", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        task_id = data["task_id"]
        print(f"\n✅ 任务创建成功")
        print(f"   Task ID: {task_id}")
        print(f"   状态: {data['status']}")
        return task_id
    else:
        print(f"\n❌ 创建失败: {response.text}")
        return None


def monitor_task_progress(task_id: int, interval: int = 5):
    """监控任务进度"""
    print("\n" + "="*80)
    print("步骤 3: 监控任务进度")
    print("="*80)
    print(f"\n每 {interval} 秒刷新一次，按 Ctrl+C 停止监控\n")
    
    try:
        while True:
            response = requests.get(f"{BASE_URL}/api/tasks/{task_id}")
            
            if response.status_code != 200:
                print(f"❌ 查询失败: {response.text}")
                break
            
            task = response.json()
            status = task["status"]
            progress = task.get("progress", 0)
            
            # 显示进度
            progress_bar = "█" * (progress // 5) + "░" * (20 - progress // 5)
            print(f"\r[{progress_bar}] {progress}% | 状态: {status}", end="", flush=True)
            
            # 如果任务完成或失败，退出监控
            if status in ["completed", "failed"]:
                print("\n")
                
                if status == "completed":
                    print(f"✅ 任务完成！")
                    print(f"   平均分: {task.get('avg_score', 'N/A')}")
                    print(f"   报告路径: {task.get('result_path', 'N/A')}")
                    print(f"   数据集路径: {task.get('dataset_path', 'N/A')}")
                    
                    if task.get('metrics_summary'):
                        print(f"\n   各指标得分:")
                        for metric, score in task['metrics_summary'].items():
                            print(f"     - {metric}: {score:.2f}")
                else:
                    print(f"❌ 任务失败")
                    print(f"   错误: {task.get('error', 'Unknown error')}")
                
                break
            
            time.sleep(interval)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  监控已停止（任务仍在后台运行）")


def check_pending_tasks():
    """检查待处理任务队列"""
    print("\n" + "="*80)
    print("检查待处理任务队列")
    print("="*80)
    
    response = requests.get(f"{BASE_URL}/api/tasks/queue/pending?limit=10")
    
    if response.status_code == 200:
        data = response.json()
        total = data["total"]
        
        if total == 0:
            print("\n✅ 队列为空，无待处理任务")
        else:
            print(f"\n⏳ 待处理任务: {total} 个\n")
            for task in data["tasks"]:
                print(f"  - Task ID: {task['id']}")
                print(f"    文档: {task['document_filename']}")
                print(f"    状态: {task['status']}")
                print(f"    创建时间: {task['created_at']}")
                print()
    else:
        print(f"❌ 查询失败: {response.text}")


def main():
    """主流程"""
    print("\n" + "="*80)
    print("Worker 集成测试")
    print("="*80)
    
    print("\n⚠️  提示: 在继续之前，请确保 API 服务已启动！")
    print("   启动命令: ./scripts/start_server.sh")
    input("\n按回车键继续...")
    
    # 1. 上传文档
    document_id = upload_test_document()
    if not document_id:
        return
    
    # 2. 创建任务
    task_id = create_evaluation_task(document_id)
    if not task_id:
        return
    
    # 3. 检查待处理任务
    check_pending_tasks()
    
    # 4. 提示启动 Worker
    print("\n" + "="*80)
    print("步骤 3: 启动 Worker")
    print("="*80)
    print("\n请在另一个终端窗口启动 Worker:")
    print("   cd zeval-service")
    print("   ./scripts/start_worker.sh")
    print("\nWorker 启动后，它会自动拉取并处理任务。")
    input("\n按回车键开始监控任务进度...")
    
    # 5. 监控进度
    monitor_task_progress(task_id, interval=3)
    
    print("\n" + "="*80)
    print("✅ 测试完成！")
    print("="*80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
