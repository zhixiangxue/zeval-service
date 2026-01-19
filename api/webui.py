"""RAG评估系统 Web UI

使用 Gradio 构建的交互式界面，让非技术人员也能轻松使用评估系统

集成模式（推荐）：
    启动 API 服务时自动挂载到 /ui 路径
    访问地址：http://localhost:8001/ui
    
独立运行模式：
    python api/webui.py
    访问地址：http://localhost:7860
"""
import os
import time
from datetime import datetime
import gradio as gr
import httpx
from pathlib import Path


# API 配置
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001")


def upload_document(file):
    """上传文档"""
    if file is None:
        return [["错误", "请先选择文件"]], None, None
    
    try:
        # 读取文件
        file_path = Path(file.name)
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "application/pdf")}
            
            # 调用API
            response = httpx.post(
                f"{API_BASE_URL}/documents",
                files=files,
                timeout=60.0
            )
            response.raise_for_status()
            
        result = response.json()
        
        # 返回表格数据
        table_data = [
            ["状态", "上传成功"],
            ["文件名", result['filename']],
            ["文档ID", result['document_id']],
            ["页数", result['total_pages']],
            ["大小", f"{result['file_size'] / 1024:.1f} KB"],
            ["哈希", result['file_hash'][:16] + "..."]
        ]
        
        return table_data, result['document_id'], result['total_pages']
        
    except httpx.HTTPError as e:
        return [["错误", f"上传失败: {str(e)}"]], None, None
    except Exception as e:
        return [["错误", f"错误: {str(e)}"]], None, None


def create_evaluation_task(doc_id, start_page, end_page, num_cases):
    """创建评估任务"""
    if doc_id is None or doc_id == 0:
        return [["错误", "请先上传文档"]], None
    
    # 验证页码
    if start_page is not None and start_page != 0:
        if start_page < 1 or not isinstance(int(start_page), int):
            return [["错误", "起始页必须是正整数"]], None
    
    if end_page is not None and end_page != 0:
        if end_page < 1 or not isinstance(int(end_page), int):
            return [["错误", "结束页必须是正整数"]], None
    
    if start_page and end_page and start_page > end_page:
        return [["错误", "起始页不能大于结束页"]], None
    
    try:
        # 构建请求
        payload = {
            "document_id": int(doc_id),
            "num_test_cases": int(num_cases)
        }
        
        # 只有当页码不为0时才添加
        if start_page and start_page > 0:
            payload["start_page"] = int(start_page)
        if end_page and end_page > 0:
            payload["end_page"] = int(end_page)
        
        # 调用API
        response = httpx.post(
            f"{API_BASE_URL}/tasks",
            json=payload,
            timeout=10.0
        )
        response.raise_for_status()
        
        result = response.json()
        
        # 返回表格数据
        table_data = [[
            "任务ID",
            result['task_id']
        ], [
            "文档ID",
            result['document_id']
        ], [
            "状态",
            result['status']
        ], [
            "测试用例数",
            num_cases
        ], [
            "提示",
            "任务已加入队列，Worker会自动处理"
        ]]
        
        return table_data, result['task_id']
        
    except httpx.HTTPError as e:
        return [["错误", f"创建任务失败: {str(e)}"]], None
    except Exception as e:
        return [["错误", f"错误: {str(e)}"]], None


def get_task_status(task_id):
    """查询任务状态"""
    if task_id is None or task_id == "" or task_id == 0:
        return [["错误", "请输入任务ID"]], None, None
    
    try:
        response = httpx.get(
            f"{API_BASE_URL}/tasks/{int(task_id)}",
            timeout=10.0
        )
        response.raise_for_status()
        
        task = response.json()
        
        # 格式化时间
        created_at = datetime.fromisoformat(task['created_at']).strftime("%Y-%m-%d %H:%M:%S")
        
        # 构建表格数据
        table_data = [
            ["任务ID", task['id']],
            ["文档ID", task['document_id']],
            ["文档名", task.get('document_filename', 'N/A')],
            ["状态", task['status']],
            ["创建时间", created_at],
            ["测试用例数", task['num_test_cases']],
        ]
        
        # 页码范围
        if task.get('start_page') or task.get('end_page'):
            page_range = f"{task.get('start_page', 1)} - {task.get('end_page', 'end')}"
            table_data.append(["页码范围", page_range])
        
        # 运行时间
        if task['status'] == 'running' and task.get('started_at'):
            try:
                started = datetime.fromisoformat(task['started_at']).strftime("%Y-%m-%d %H:%M:%S")
                table_data.append(["开始时间", started])
                
                # 计算已运行时长
                started_dt = datetime.fromisoformat(task['started_at'])
                elapsed = datetime.now() - started_dt
                elapsed_minutes = int(elapsed.total_seconds() / 60)
                elapsed_seconds = int(elapsed.total_seconds() % 60)
                table_data.append(["已运行时长", f"{elapsed_minutes}分{elapsed_seconds}秒"])
            except (ValueError, TypeError, AttributeError):
                table_data.append(["开始时间", "时间格式错误"])
        
        # 完成信息
        excel_file = None
        md_file = None
        if task['status'] == 'completed':
            if task.get('completed_at'):
                try:
                    completed = datetime.fromisoformat(task['completed_at']).strftime("%Y-%m-%d %H:%M:%S")
                    table_data.append(["完成时间", completed])
                    
                    # 计算总运行时长
                    if task.get('started_at'):
                        started_dt = datetime.fromisoformat(task['started_at'])
                        completed_dt = datetime.fromisoformat(task['completed_at'])
                        total_time = completed_dt - started_dt
                        total_minutes = int(total_time.total_seconds() / 60)
                        total_seconds = int(total_time.total_seconds() % 60)
                        table_data.append(["总运行时长", f"{total_minutes}分{total_seconds}秒"])
                except (ValueError, TypeError, AttributeError):
                    table_data.append(["完成时间", "时间格式错误"])
            
            if task.get('avg_score') is not None:
                table_data.append(["平均分数", f"{task['avg_score']:.2f}"])
            
            if task.get('metrics_summary'):
                for metric, score in task['metrics_summary'].items():
                    table_data.append([f"指标-{metric}", f"{score:.2f}"])
            
            # 检查报告文件是否存在
            if task.get('result_path'):
                from pathlib import Path
                excel_path = Path(task['result_path'])
                if excel_path.exists():
                    excel_file = str(excel_path)
                    table_data.append(["报告状态", "可下载"])
                    
                    # 尝试查找 Markdown 报告
                    md_path = excel_path.parent / "evaluation_report.md"
                    if md_path.exists():
                        md_file = str(md_path)
                else:
                    table_data.append(["报告状态", "文件不存在"])
        
        # 错误信息
        if task['status'] == 'failed' and task.get('error'):
            table_data.append(["错误信息", task['error']])
        
        return table_data, excel_file, md_file
        
    except httpx.HTTPError as e:
        return [["错误", f"查询失败: {str(e)}"]], None, None
    except Exception as e:
        return [["错误", f"错误: {str(e)}"]], None, None


def list_recent_documents():
    """查询最近的文档 - 返回表格数据"""
    try:
        response = httpx.get(
            f"{API_BASE_URL}/documents?limit=10",
            timeout=10.0
        )
        response.raise_for_status()
        
        result = response.json()
        
        if result['total'] == 0:
            return [], "暂无文档"
        
        # 构建表格数据 [ID, 文件名, 页数, 大小, 上传时间]
        table_data = []
        for doc in result['documents']:
            uploaded = datetime.fromisoformat(doc['uploaded_at']).strftime("%Y-%m-%d %H:%M")
            file_size_kb = doc['file_size'] / 1024
            table_data.append([
                doc['id'],
                doc['filename'],
                doc['total_pages'],
                f"{file_size_kb:.1f} KB",
                uploaded
            ])
        
        status_msg = f"共 {result['total']} 个文档"
        return table_data, status_msg
        
    except Exception as e:
        return [], f"查询失败: {str(e)}"


def get_task_files_for_download(evt: gr.SelectData):
    """从任务列表中选中一行，获取报告文件"""
    if evt.index is None or evt.index[0] is None:
        return None, None, "请选择一个任务"
    
    # evt.value 是点击的单元格的值
    # evt.index[0] 是行索引
    row_index = evt.index[0]
    
    try:
        # 重新查询任务列表，获取完整数据
        response = httpx.get(
            f"{API_BASE_URL}/tasks?limit=20",
            timeout=10.0
        )
        response.raise_for_status()
        result = response.json()
        
        if row_index >= len(result['tasks']):
            return None, None, "任务不存在"
        
        task = result['tasks'][row_index]
        
        # 只有已完成的任务才有报告
        if task['status'] != 'completed':
            return None, None, f"任务状态: {task['status']}，还没有报告"
        
        if not task.get('result_path'):
            return None, None, "任务已完成，但未找到报告路径"
        
        # 检查文件是否存在
        from pathlib import Path
        excel_path = Path(task['result_path'])
        
        excel_file = None
        md_file = None
        
        if excel_path.exists():
            excel_file = str(excel_path)
            
            # 查找 Markdown 报告
            md_path = excel_path.parent / "evaluation_report.md"
            if md_path.exists():
                md_file = str(md_path)
            
            return excel_file, md_file, f"任务 {task['id']} - 报告可下载"
        else:
            return None, None, "报告文件不存在"
        
    except Exception as e:
        return None, None, f"错误: {str(e)}"


def list_recent_tasks():
    try:
        response = httpx.get(
            f"{API_BASE_URL}/tasks?limit=20",
            timeout=10.0
        )
        response.raise_for_status()
        
        result = response.json()
        
        if result['total'] == 0:
            return [], "暂无任务"
        
        # 构建表格数据 [任务ID, 状态, 文档名, 页码范围, 评估集大小, 分数, 创建时间]
        table_data = []
        for task in result['tasks']:
            created = datetime.fromisoformat(task['created_at']).strftime("%Y-%m-%d %H:%M")
            
            # 状态显示
            status_display = {
                'pending': '待处理',
                'running': '运行中',
                'completed': '已完成',
                'failed': '失败'
            }.get(task['status'], task['status'])
            
            # 页码范围显示
            if task.get('start_page') or task.get('end_page'):
                page_range = f"{task.get('start_page', 1)}-{task.get('end_page', '全部')}"
            else:
                page_range = "全部"
            
            # 评估集大小
            num_cases = task.get('num_test_cases', '-')
            
            # 分数显示
            score_display = f"{task['avg_score']:.2f}" if task.get('avg_score') is not None else "-"
            
            table_data.append([
                task['id'],
                status_display,
                task.get('document_filename', 'N/A'),
                page_range,
                num_cases,
                score_display,
                created
            ])
        
        status_msg = f"共 {result['total']} 个任务"
        return table_data, status_msg
        
    except Exception as e:
        return [], f"查询失败: {str(e)}"


# ============================================================
# Gradio 界面
# ============================================================

app = gr.Blocks(
    title="RAG评估系统",
    theme=gr.themes.Soft(),
    css=".gradio-container {max-width: 1200px !important}"
)
    
with app:
    gr.Markdown("""
    # RAG Evaluation
    
    上传PDF文档，系统会自动生成评估集并评估RAG系统指标。
    """)
    
    with gr.Tabs():
        # ============ Tab 1: 上传文档 ============
        with gr.Tab("上传文档"):
            with gr.Row():
                with gr.Column():
                    file_input = gr.File(
                        label="选择PDF文件（选择后自动上传）",
                        file_types=[".pdf"],
                        file_count="single"
                    )
                
                with gr.Column():
                    upload_output = gr.Dataframe(
                        label="上传结果",
                        headers=["字段", "值"],
                        datatype=["str", "str"],
                        col_count=2,
                        wrap=True,
                        interactive=False
                    )
            
            # 隐藏的状态变量
            doc_id_state = gr.State()
            total_pages_state = gr.State()
            
            # 文件选择后自动上传
            file_input.change(
                upload_document,
                inputs=[file_input],
                outputs=[upload_output, doc_id_state, total_pages_state]
            )
        
        # ============ Tab 2: 创建任务 ============
        with gr.Tab("创建评估任务"):
            gr.Markdown("配置评估任务")
            
            with gr.Row():
                with gr.Column():
                    task_doc_id = gr.Number(
                        label="文档ID",
                        value=None,
                        precision=0,
                        info="上传文档后会自动填充"
                    )
                    
                    with gr.Row():
                        task_start_page = gr.Number(
                            label="起始页（可选，0表示不限制）",
                            value=0,
                            precision=0,
                            minimum=0
                        )
                        task_end_page = gr.Number(
                            label="结束页（可选，0表示不限制）",
                            value=0,
                            precision=0,
                            minimum=0
                        )
                    
                    task_num_cases = gr.Slider(
                        label="测试用例数量",
                        minimum=10,
                        maximum=200,
                        value=50,
                        step=10,
                        info="生成的评估case数量"
                    )
                    
                    create_task_btn = gr.Button("创建任务", variant="primary", size="lg")
                
                with gr.Column():
                    task_output = gr.Dataframe(
                        label="任务创建结果",
                        headers=["字段", "值"],
                        datatype=["str", "str"],
                        col_count=2,
                        wrap=True,
                        interactive=False
                    )
            
            task_id_state = gr.State()
            
            # 从上传文档自动填充文档ID
            doc_id_state.change(
                lambda x: x,
                inputs=[doc_id_state],
                outputs=[task_doc_id]
            )
            
            create_task_btn.click(
                create_evaluation_task,
                inputs=[task_doc_id, task_start_page, task_end_page, task_num_cases],
                outputs=[task_output, task_id_state]
            )
        
        # ============ Tab 3: 查询状态 ============
        with gr.Tab("查询任务状态"):
            with gr.Row():
                with gr.Column():
                    query_task_id = gr.Number(
                        label="任务ID",
                        value=None,
                        precision=0,
                        info="创建任务后会自动填充"
                    )
                    query_btn = gr.Button("查询状态", variant="primary", size="lg")
                    
                    gr.Markdown("---")
                    refresh_btn = gr.Button("刷新状态", size="sm")
                
                with gr.Column():
                    status_output = gr.Dataframe(
                        label="任务状态",
                        headers=["字段", "值"],
                        datatype=["str", "str"],
                        col_count=2,
                        wrap=True,
                        interactive=False
                    )
            
            # 下载区域
            with gr.Row():
                with gr.Column():
                    excel_download = gr.File(
                        label="下载 Excel 报告",
                        interactive=False,
                        visible=True
                    )
                with gr.Column():
                    md_download = gr.File(
                        label="下载 Markdown 报告",
                        interactive=False,
                        visible=True
                    )
            
            # 从创建任务自动填充任务ID
            task_id_state.change(
                lambda x: x,
                inputs=[task_id_state],
                outputs=[query_task_id]
            )
            
            query_btn.click(
                get_task_status,
                inputs=[query_task_id],
                outputs=[status_output, excel_download, md_download]
            )
            
            refresh_btn.click(
                get_task_status,
                inputs=[query_task_id],
                outputs=[status_output, excel_download, md_download]
            )
        
        # ============ Tab 4: 文档管理 ============
        with gr.Tab("文档管理") as docs_tab:
            gr.Markdown("已上传的文档")
            
            with gr.Row():
                refresh_docs_btn = gr.Button("刷新", size="sm")
            
            docs_status = gr.Markdown("加载中...")
            
            docs_table = gr.Dataframe(
                headers=["ID", "文件名", "页数", "大小", "上传时间"],
                datatype=["number", "str", "number", "str", "str"],
                col_count=5,
                wrap=True,
                interactive=False
            )
            
            # Tab切换时自动加载
            docs_tab.select(
                list_recent_documents,
                outputs=[docs_table, docs_status]
            )
            
            # 手动刷新
            refresh_docs_btn.click(
                list_recent_documents,
                outputs=[docs_table, docs_status]
            )
        
        # ============ Tab 5: 评估任务 ============
        with gr.Tab("评估任务") as tasks_tab:
            gr.Markdown("评估任务列表（点击已完成的任务可下载报告）")
            
            with gr.Row():
                refresh_tasks_btn = gr.Button("刷新", size="sm")
            
            tasks_status = gr.Markdown("加载中...")
            
            tasks_table = gr.Dataframe(
                headers=["任务ID", "状态", "文档名", "页码范围", "评估集大小", "分数", "创建时间"],
                datatype=["number", "str", "str", "str", "number", "str", "str"],
                col_count=7,
                wrap=True,
                interactive=False
            )
            
            # 下载区域
            gr.Markdown("### 下载报告")
            task_download_status = gr.Markdown("点击上方表格中的任务可下载报告")
            
            with gr.Row():
                with gr.Column():
                    task_excel_download = gr.File(
                        label="Excel 报告",
                        interactive=False
                    )
                with gr.Column():
                    task_md_download = gr.File(
                        label="Markdown 报告",
                        interactive=False
                    )
            
            # Tab切换时自动加载
            tasks_tab.select(
                list_recent_tasks,
                outputs=[tasks_table, tasks_status]
            )
            
            # 手动刷新
            refresh_tasks_btn.click(
                list_recent_tasks,
                outputs=[tasks_table, tasks_status]
            )
            
            # 点击表格行时加载报告
            tasks_table.select(
                get_task_files_for_download,
                outputs=[task_excel_download, task_md_download, task_download_status]
            )
    
    gr.Markdown("""
    ---
    ### 使用说明
    
    1. **上传文档**: 选择PDF文件并上传，记下文档ID（或者在文档管理中查看）
    2. **创建任务**: 配置评估参数，创建评估任务
    3. **查询状态**: 输入任务ID，实时查看评估进度
    4. **查看报告**: 任务完成后，在状态中会显示报告路径
    """)


if __name__ == "__main__":
    print("启动 RAG 评估系统 Web UI...")
    print(f"API 地址: {API_BASE_URL}")
    print(f"Web UI: http://localhost:7860")
    print("")
    
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        inbrowser=False  # 不自动打开浏览器
    )
