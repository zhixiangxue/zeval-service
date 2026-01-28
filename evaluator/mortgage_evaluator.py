"""Mortgage RAG 评估器 - 核心评估流程"""

import time
import tempfile
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

# Fix torch.xpu compatibility issue for PyTorch < 2.5
import torch
if not hasattr(torch, 'xpu'):
    class MockXPU:
        @staticmethod
        def is_available():
            return False
    torch.xpu = MockXPU()

from zeval.synthetic_data.readers.docling import DoclingReader
from zeval.synthetic_data.splitters import MarkdownHeaderSplitter
from zeval.synthetic_data.transforms.extractors import (
    SummaryExtractor,
    KeyphrasesExtractor,
    EntitiesExtractor
)
from zeval.synthetic_data.generators.persona import generate_personas, Persona
from zeval.synthetic_data.generators.single_hop import generate_single_hop
from zeval.evaluation.metrics import (
    Faithfulness,
    ContextRelevance,
    ContextRecall,
    ContextPrecision,
    AnswerRelevancy,
    AnswerCorrectness,
)
from zeval.evaluation.runner import MetricRunner
from zeval.evaluation.reporter import EvaluationReporter
from zeval.schemas.eval import EvalDataset

from .config import EvaluatorConfig
from .result import EvalResult

console = Console()


# Mortgage 领域的 Persona 模型
class HomeBuyerPersona(Persona):
    """US Home Buyer persona with financial attributes"""
    credit_score: int = Field(
        description="Credit score (300-850), affects mortgage eligibility and interest rates"
    )
    dti_ratio: float = Field(
        description="Debt-to-Income ratio as percentage (typical max is 43%)"
    )
    down_payment_percent: float = Field(
        description="Down payment as percentage of home price (typically 3-20%)"
    )
    budget_range: str = Field(
        description="Home price budget range (e.g., '$300K-$500K')"
    )


class MortgageRAGEvaluator:
    """Mortgage RAG 评估器
    
    端到端评估流程：PDF → 读取 → 分割 → 富化 → 生成测试集 → 调用RAG → 评估 → 报告
    
    Example:
        config = EvaluatorConfig.from_env()
        evaluator = MortgageRAGEvaluator(config)
        result = await evaluator.eval("/path/to/doc.pdf")
        print(f"报告: {result.report_excel_path}")
        print(f"平均分: {result.avg_score:.2f}")
    """
    
    def __init__(self, config: EvaluatorConfig):
        self.config = config
        self.console = console
        
        # 初始化组件
        self.reader = self._init_reader()
        self.splitter = MarkdownHeaderSplitter()
        
        # Extractors
        self.extractor = (
            SummaryExtractor(config.llm_uri, config.api_key, max_sentences=2)
            | KeyphrasesExtractor(config.llm_uri, config.api_key, max_num=5)
            | EntitiesExtractor(config.llm_uri, config.api_key, max_num=5)
        )
        
        # Metrics
        self.metrics = [
            Faithfulness(config.llm_uri, config.api_key),
            ContextRelevance(config.llm_uri, config.api_key),
            ContextRecall(config.llm_uri, config.api_key),
            ContextPrecision(config.llm_uri, config.api_key),
            AnswerRelevancy(config.llm_uri, config.api_key),
            AnswerCorrectness(config.llm_uri, config.api_key),
        ]
        
        self.runner = MetricRunner(metrics=self.metrics)
        self.reporter = EvaluationReporter(config.llm_uri, config.api_key)
    
    def _init_reader(self) -> DoclingReader:
        """初始化 PDF Reader"""
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
        
        pdf_options = PdfPipelineOptions()
        pdf_options.accelerator_options = AcceleratorOptions(
            num_threads=8,
            device=AcceleratorDevice.CPU
        )
        
        return DoclingReader(pdf_pipeline_options=pdf_options)
    
    async def eval(
        self, 
        file_path: str, 
        start_page: int | None = None,
        end_page: int | None = None
    ) -> EvalResult:
        """执行端到端评估
        
        Args:
            file_path: PDF 文件路径
            start_page: 起始页码（从1开始），None表示从第一页开始
            end_page: 结束页码（包含），None表示到最后一页
            
        Returns:
            EvalResult: 评估结果，包含所有输出路径和统计信息
            
        Example:
            # 评估整个文档
            result = await evaluator.eval("/path/to/doc.pdf")
            
            # 只评估第10-20页
            result = await evaluator.eval("/path/to/doc.pdf", start_page=10, end_page=20)
        """
        start_time = time.time()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 生成唯一工作目录 ID（6位随机字符）
        import random
        import string
        work_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        
        # 在系统临时目录下创建工作目录
        work_dir = Path(tempfile.gettempdir()) / f"zeval_{work_id}"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        # 如果指定了页码范围，先切割 PDF
        actual_file_path = file_path
        if start_page is not None or end_page is not None:
            actual_file_path = self._extract_pages(file_path, start_page, end_page, work_dir)
        
        # 显示开始信息
        page_info = ""
        if start_page is not None or end_page is not None:
            page_info = f"\n[bold]页码范围[/bold]: {start_page or 1} - {end_page or '最后一页'}"
        
        self.console.print()
        self.console.print(Panel.fit(
            f"[bold]文件[/bold]: {Path(file_path).name}"
            f"{page_info}\n"
            f"[bold cyan]工作目录[/bold cyan]: {work_dir}\n"
            f"[bold]时间[/bold]: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            title="🚀 开始评估",
            border_style="cyan"
        ))
        self.console.print()
        
        # 1. 读取 PDF
        self.console.print("[cyan]▶[/cyan] [bold]Step 1/6:[/bold] 读取 PDF...")
        document = self.reader.read(str(actual_file_path))
        self.console.print(f"  [green]✓[/green] 读取完成: {len(document.pages)} 页")
        
        # 保存 document content 到工作目录
        doc_content_path = work_dir / "document_content.md"
        doc_content_path.write_text(document.content, encoding='utf-8')
        self.console.print(f"  [blue]ℹ[/blue] 内容已保存: {doc_content_path.name}\n")
        
        # 2. 分割文档
        self.console.print("[cyan]▶[/cyan] [bold]Step 2/6:[/bold] 分割文档...")
        units = document.split(self.splitter)
        self.console.print(f"  [green]✓[/green] 分割完成: {len(units)} 个单元\n")
        
        # 3. 富化单元
        self.console.print("[cyan]▶[/cyan] [bold]Step 3/6:[/bold] 富化单元...")
        enriched_units = await self.extractor.transform(
            units[:self.config.max_units],
            max_concurrency=self.config.max_concurrency
        )
        self.console.print(f"  [green]✓[/green] 富化完成: {len(enriched_units)} 个单元\n")
        
        # 4. 生成测试数据集
        self.console.print("[cyan]▶[/cyan] [bold]Step 4/6:[/bold] 生成测试数据集...")
        dataset = await self._generate_dataset(enriched_units)
        self.console.print(f"  [green]✓[/green] 生成完成: {len(dataset.cases)} 个测试用例\n")
        
        # 保存数据集
        dataset_path = work_dir / "dataset.json"
        dataset.to_json(str(dataset_path))
        
        # 5. 调用 RAG 系统（Mock）
        self.console.print("[cyan]▶[/cyan] [bold]Step 5/6:[/bold] 调用 RAG 系统...")
        await self._call_rag_system(dataset)
        self.console.print(f"  [green]✓[/green] RAG 调用完成\n")
        
        # 6. 执行评估
        self.console.print("[cyan]▶[/cyan] [bold]Step 6/6:[/bold] 执行评估...")
        await self.runner.run(dataset)
        self.console.print(f"  [green]✓[/green] 评估完成\n")
        
        # 7. 生成报告
        self.console.print("[cyan]▶[/cyan] [bold]生成评估报告...[/bold]")
        await self.reporter.generate_report(
            dataset=dataset,
            output_path=str(work_dir)
        )
        self.console.print(f"  [green]✓[/green] 报告生成完成\n")
        
        # 计算统计信息
        execution_time = time.time() - start_time
        avg_score = self._compute_avg_score(dataset)
        metrics_summary = self._compute_metrics_summary(dataset)
        
        result = EvalResult(
            dataset_path=dataset_path,
            report_markdown_path=work_dir / "evaluation_report.md",
            report_excel_path=work_dir / "evaluation_report.xlsx",
            total_cases=len(dataset.cases),
            avg_score=avg_score,
            metrics_summary=metrics_summary,
            execution_time=execution_time,
            timestamp=timestamp
        )
        
        # 显示结果
        self.console.print(Panel.fit(
            f"[bold green]✨ 评估完成！[/bold green]\n\n"
            f"[bold]总测试用例[/bold]: {result.total_cases}\n"
            f"[bold]平均分数[/bold]: {result.avg_score:.2f}\n"
            f"[bold]执行耗时[/bold]: {result.execution_time:.1f}s\n\n"
            f"[bold cyan]所有结果文件均保存在[/bold cyan]:\n"
            f"  {work_dir}",
            title="🎉 评估结果",
            border_style="green"
        ))
        self.console.print()
        
        return result
    
    async def _generate_dataset(self, units) -> EvalDataset:
        """生成测试数据集"""
        # 生成 Personas
        personas = await generate_personas(
            llm_uri=self.config.llm_uri,
            api_key=self.config.api_key,
            domain=self.config.domain,
            num_personas=self.config.num_personas,
            persona_model=HomeBuyerPersona
        )
        
        # 生成测试用例
        dataset = await generate_single_hop(
            llm_uri=self.config.llm_uri,
            api_key=self.config.api_key,
            units=units,
            personas=personas,
            num_cases=self.config.num_test_cases,
            domain=self.config.domain
        )
        
        return dataset
    
    async def _call_rag_system(self, dataset: EvalDataset):
        """调用 RAG 系统
        
        将每个测试用例的 question 发送到 RAG 系统，获取检索结果
        注意：RAG 只负责检索，不生成答案，所以 answer 设为空字符串
        """
        import httpx
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
        
        total_cases = len(dataset.cases)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task("[cyan]调用 RAG...", total=total_cases)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                for idx, case in enumerate(dataset.cases, 1):
                    try:
                        response = await client.post(
                            f"{self.config.rag_base_url}/datasets/{self.config.rag_dataset_id}/query",
                            json={
                                "query": case.question,
                                "top_k": self.config.rag_top_k,
                                "filters": {}
                            }
                        )
                        
                        if response.status_code == 200:
                            results = response.json().get("data", [])
                            # RAG 只负责检索，不生成答案
                            case.answer = ""
                            # 使用检索到的 contexts
                            case.retrieved_contexts = [r["content"] for r in results]
                            progress.update(task, advance=1, description=f"[cyan]调用 RAG... [green]✓[/green] Case {idx}")
                        else:
                            self.console.print(
                                f"  [yellow]![/yellow] Case {idx} RAG 调用失败 (HTTP {response.status_code})"
                            )
                            case.answer = ""
                            case.retrieved_contexts = []
                            progress.update(task, advance=1, description=f"[cyan]调用 RAG... [yellow]![/yellow] Case {idx}")
                            
                    except Exception as e:
                        self.console.print(
                            f"  [yellow]![/yellow] Case {idx} RAG 调用异常: {str(e)[:50]}..."
                        )
                        case.answer = ""
                        case.retrieved_contexts = []
                        progress.update(task, advance=1, description=f"[cyan]调用 RAG... [red]✗[/red] Case {idx}")
    
    def _compute_avg_score(self, dataset: EvalDataset) -> float:
        """计算平均分"""
        if not dataset.cases:
            return 0.0
        
        total_score = sum(
            case.overall_score for case in dataset.cases 
            if case.overall_score is not None
        )
        return total_score / len(dataset.cases)
    
    def _compute_metrics_summary(self, dataset: EvalDataset) -> dict[str, float]:
        """计算各指标平均分"""
        metrics_summary = {}
        
        if not dataset.cases:
            return metrics_summary
        
        # 收集所有指标名称
        all_metric_names = set()
        for case in dataset.cases:
            if case.results:
                all_metric_names.update(case.results.keys())
        
        # 计算每个指标的平均分
        for metric_name in all_metric_names:
            scores = [
                case.results[metric_name].score
                for case in dataset.cases
                if metric_name in case.results and case.results[metric_name].score is not None
            ]
            if scores:
                metrics_summary[metric_name] = sum(scores) / len(scores)
        
        return metrics_summary
    
    def _extract_pages(
        self, 
        pdf_path: str, 
        start_page: int | None = None, 
        end_page: int | None = None,
        work_dir: Path | None = None
    ) -> str:
        """提取指定页码范围的 PDF
        
        Args:
            pdf_path: 原始PDF路径
            start_page: 起始页码（从1开始）
            end_page: 结束页码（包含）
            work_dir: 工作目录
            
        Returns:
            提取后的PDF文件路径（临时文件）
        """
        from PyPDF2 import PdfReader, PdfWriter
        
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        
        # 确定实际的起止页码
        actual_start = (start_page - 1) if start_page else 0  # 转为0-based索引
        actual_end = end_page if end_page else total_pages
        
        # 校验页码范围
        if actual_start < 0:
            actual_start = 0
        if actual_end > total_pages:
            actual_end = total_pages
        if actual_start >= actual_end:
            raise ValueError(
                f"无效的页码范围: {start_page}-{end_page}，"
                f"文档总页数: {total_pages}"
            )
        
        # 创建输出PDF
        writer = PdfWriter()
        for i in range(actual_start, actual_end):
            writer.add_page(reader.pages[i])
        
        # 保存到工作目录
        temp_filename = f"{Path(pdf_path).stem}_p{actual_start+1}-{actual_end}.pdf"
        temp_path = work_dir / temp_filename
        
        with open(temp_path, "wb") as f:
            writer.write(f)
        
        self.console.print(
            f"  [blue]ℹ[/blue] 已提取页码 {actual_start+1}-{actual_end} "
            f"(共 {actual_end - actual_start} 页)\n"
        )
        
        return str(temp_path)
