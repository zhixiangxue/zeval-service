"""Interactive Debug Script for MortgageRAGEvaluator

Quick local testing tool that directly calls MortgageRAGEvaluator
without database or worker complexity.

Usage:
    python eval-service/worker/debug_eval.py
    
    Then follow the interactive prompts.
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluator import MortgageRAGEvaluator, EvaluatorConfig

console = Console()


def get_pdf_path() -> Path:
    """Get PDF path with PowerShell artifact cleaning"""
    console.print("\n[bold]请输入PDF文件路径:[/bold]")
    pdf_input = input("> ").strip()
    
    if not pdf_input:
        console.print("[red]✗ 错误: PDF路径不能为空[/red]")
        sys.exit(1)
    
    # Clean path: remove PowerShell artifacts and quotes
    if pdf_input.startswith("& '") or pdf_input.startswith('& "'):
        pdf_input = pdf_input[3:]  # Remove "& '" or '& "'
    
    # Remove quotes
    pdf_input = pdf_input.strip('"').strip("'")
    
    pdf_path = Path(pdf_input)
    if not pdf_path.exists():
        console.print(f"[red]✗ 错误: PDF文件不存在: {pdf_path}[/red]")
        sys.exit(1)
    
    return pdf_path


def get_page_range() -> tuple[int | None, int | None]:
    """Get optional page range"""
    console.print("\n[bold]是否指定页码范围? (y/n, 默认: n):[/bold]")
    choice = input("> ").strip().lower()
    
    if choice not in ['y', 'yes']:
        return None, None
    
    # Get start page
    console.print("\n[bold]起始页码 (从1开始, 默认: 1):[/bold]")
    start_input = input("> ").strip()
    start_page = int(start_input) if start_input else None
    
    # Get end page
    console.print("\n[bold]结束页码 (包含, 默认: 最后一页):[/bold]")
    end_input = input("> ").strip()
    end_page = int(end_input) if end_input else None
    
    return start_page, end_page


def show_config_and_confirm(
    pdf_path: Path,
    start_page: int | None,
    end_page: int | None,
    config: EvaluatorConfig
) -> bool:
    """Display configuration and ask for confirmation"""
    
    page_info = "全部页面"
    if start_page or end_page:
        page_info = f"{start_page or 1} - {end_page or '最后一页'}"
    
    console.print("\n" + "="*80)
    console.print(Panel.fit(
        f"[bold cyan]评估配置[/bold cyan]\n\n"
        f"[bold]PDF文件[/bold]: {pdf_path.name}\n"
        f"[bold]完整路径[/bold]: {pdf_path}\n"
        f"[bold]页码范围[/bold]: {page_info}\n\n"
        f"[bold yellow]LLM配置[/bold yellow]\n"
        f"  模型: {config.llm_uri}\n"
        f"  并发数: {config.max_concurrency}\n\n"
        f"[bold yellow]生成配置[/bold yellow]\n"
        f"  测试用例数: {config.num_test_cases}\n"
        f"  最大单元数: {config.max_units}\n"
        f"  Personas数: {config.num_personas}\n\n"
        f"[bold yellow]RAG配置[/bold yellow]\n"
        f"  RAG地址: {config.rag_base_url}\n"
        f"  数据集ID: {config.rag_dataset_id}\n"
        f"  Top-K: {config.rag_top_k}",
        title="📋 配置信息",
        border_style="cyan"
    ))
    
    console.print("\n[bold yellow]是否继续? (yes/no):[/bold yellow]")
    confirm = input("> ").strip().lower()
    
    return confirm in ['yes', 'y']


async def main():
    """Main interactive workflow"""
    
    # Load environment variables
    load_dotenv()
    
    console.print("\n" + "="*80)
    console.print("[bold cyan]🔧 MortgageRAG 评估器 - 调试模式[/bold cyan]")
    console.print("="*80)
    
    # 1. Get PDF path
    pdf_path = get_pdf_path()
    
    # 2. Get page range
    start_page, end_page = get_page_range()
    
    # 3. Load config from environment
    try:
        config = EvaluatorConfig.from_env(llm_uri="openai/gpt-4o-mini")
        
        # Override with debug-friendly defaults
        config.num_test_cases = 10  # Faster for debugging
        config.max_units = 20  # Faster for debugging
        
    except ValueError as e:
        console.print(f"\n[red]✗ 配置错误: {e}[/red]")
        console.print("\n请确保已设置 OPENAI_API_KEY 环境变量")
        sys.exit(1)
    
    # 4. Show config and confirm
    if not show_config_and_confirm(pdf_path, start_page, end_page, config):
        console.print("\n[yellow]已取消[/yellow]")
        return
    
    # 5. Create evaluator
    console.print("\n" + "="*80)
    console.print("[bold green]开始评估...[/bold green]")
    console.print("="*80)
    
    evaluator = MortgageRAGEvaluator(config)
    
    # 6. Run evaluation
    try:
        result = await evaluator.eval(
            file_path=str(pdf_path),
            start_page=start_page,
            end_page=end_page
        )
        
        # 7. Display results
        console.print("\n" + "="*80)
        console.print("[bold green]✨ 评估完成！[/bold green]")
        console.print("="*80 + "\n")
        
        console.print(Panel.fit(
            f"[bold]结果摘要[/bold]\n\n"
            f"✓ 测试用例数: {result.total_cases}\n"
            f"✓ 平均分数: {result.avg_score:.2f}\n"
            f"✓ 执行耗时: {result.execution_time:.1f}秒\n\n"
            f"[bold cyan]输出文件[/bold cyan]:\n"
            f"  数据集: {result.dataset_path.name}\n"
            f"  报告(MD): {result.report_markdown_path.name}\n"
            f"  报告(Excel): {result.report_excel_path.name}\n\n"
            f"[bold cyan]工作目录[/bold cyan]:\n"
            f"  {result.dataset_path.parent}",
            title="📊 评估结果",
            border_style="green"
        ))
        
        # Show metrics breakdown
        if result.metrics_summary:
            console.print("\n[bold]指标详情:[/bold]")
            for metric_name, score in result.metrics_summary.items():
                console.print(f"  {metric_name}: {score:.2f}")
        
        console.print()
        
    except KeyboardInterrupt:
        console.print("\n\n[yellow]评估被用户中断[/yellow]")
    except Exception as e:
        console.print(f"\n\n[red]评估失败: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
