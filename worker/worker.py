"""Evaluation Worker - 定时拉取任务并执行评估

Worker 特性：
- 每次只获取 1 个任务（原子性获取，避免并发冲突）
- 获取后立即更新状态为 running
- 执行过程中实时更新进度到数据库
- 支持多 Worker 并发运行
- 单任务失败不影响其他任务
"""

import asyncio
import time
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import schedule
from rich.console import Console

from models import TaskStatus
from database import (
    claim_next_pending_task,
    get_document_by_id,
    update_task_status,
    update_task_progress,
)
from evaluator import MortgageRAGEvaluator, EvaluatorConfig


# 配置日志
logging.basicConfig(
    level=logging.WARNING,  # 设置为 WARNING，过滤掉第三方库的 INFO 日志
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('.data/worker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Worker 自己的日志保持 INFO 级别

console = Console()


class EvaluationWorker:
    """评估 Worker
    
    定时检查待处理任务，逐个执行评估流程。
    """
    
    def __init__(self, config: EvaluatorConfig, check_interval: int = 60):
        """初始化 Worker
        
        Args:
            config: 评估器配置
            check_interval: 检查任务间隔（秒），默认 60 秒
        """
        self.config = config
        self.check_interval = check_interval
        self.evaluator = MortgageRAGEvaluator(config)
        self.should_stop = False
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """处理停止信号"""
        console.print("\n[yellow]收到停止信号，等待当前任务完成...[/yellow]")
        self.should_stop = True
    
    def start(self):
        """启动 Worker"""
        console.print("[bold green]🚀 Evaluation Worker 启动[/bold green]")
        console.print(f"检查间隔: {self.check_interval} 秒")
        console.print(f"LLM URI: {self.config.llm_uri}\n")
        
        # 定时任务：每 check_interval 秒检查一次
        schedule.every(self.check_interval).seconds.do(self._process_next_task)
        
        # 启动时立即执行一次
        self._process_next_task()
        
        # 主循环
        while not self.should_stop:
            schedule.run_pending()
            time.sleep(1)
        
        console.print("[bold yellow]Worker 已停止[/bold yellow]")
    
    def _process_next_task(self):
        """处理下一个待处理任务"""
        try:
            # 原子性获取一个任务
            task = claim_next_pending_task()
            
            if not task:
                logger.info("没有待处理任务，等待下次检查...")
                return
            
            logger.info(f"获取到任务 {task.id}，开始处理...")
            console.print(f"\n[bold cyan]📋 任务 {task.id} - 开始处理[/bold cyan]")
            
            # 获取文档信息
            document = get_document_by_id(task.document_id)
            if not document:
                error_msg = f"文档 {task.document_id} 不存在"
                logger.error(error_msg)
                update_task_status(
                    task.id,
                    status=TaskStatus.FAILED,
                    completed_at=datetime.now(),
                    error=error_msg
                )
                return
            
            console.print(f"文档: {document.filename} ({document.total_pages} 页)")
            console.print(f"页码范围: {task.start_page or 1} - {task.end_page or document.total_pages}")
            console.print(f"测试用例数: {task.num_test_cases}\n")
            
            # 执行评估
            self._execute_evaluation(task, document)
            
        except Exception as e:
            logger.exception(f"处理任务时发生错误: {e}")
            console.print(f"[bold red]❌ 错误: {e}[/bold red]")
    
    def _execute_evaluation(self, task, document):
        """执行评估流程"""
        try:
            # 执行评估
            result = asyncio.run(
                self.evaluator.eval(
                    document.file_path,
                    start_page=task.start_page,
                    end_page=task.end_page
                )
            )
            
            # 更新任务状态为完成
            update_task_status(
                task.id,
                status=TaskStatus.COMPLETED,
                progress=100,
                completed_at=datetime.now(),
                result_path=str(result.report_excel_path),
                dataset_path=str(result.dataset_path),
                avg_score=result.avg_score,
                metrics_summary=result.metrics_summary
            )
            
            console.print(f"[bold green]✅ 任务 {task.id} 完成！平均分: {result.avg_score:.2f}[/bold green]")
            logger.info(f"任务 {task.id} 完成，平均分: {result.avg_score:.2f}")
            
        except Exception as e:
            # 更新任务状态为失败
            error_msg = str(e)
            update_task_status(
                task.id,
                status=TaskStatus.FAILED,
                completed_at=datetime.now(),
                error=error_msg
            )
            
            console.print(f"[bold red]❌ 任务 {task.id} 失败: {error_msg}[/bold red]")
            logger.exception(f"任务 {task.id} 失败")


def main():
    """Worker 入口"""
    try:
        # 从环境变量加载配置
        config = EvaluatorConfig.from_env()
        
        # 启动 Worker
        worker = EvaluationWorker(config, check_interval=60)
        worker.start()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Worker 被用户中断[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Worker 启动失败: {e}[/bold red]")
        logger.exception("Worker 启动失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
