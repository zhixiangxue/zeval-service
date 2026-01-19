"""评估结果"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class EvalResult:
    """评估结果
    
    包含所有输出文件路径和评估统计信息
    
    Attributes:
        dataset_path: 生成的测试数据集文件路径
        report_markdown_path: Markdown 格式报告路径
        report_excel_path: Excel 格式报告路径
        total_cases: 总测试用例数
        avg_score: 平均评估分数
        metrics_summary: 各指标的平均分
        execution_time: 执行耗时（秒）
        timestamp: 执行时间戳
    """
    
    # 输出路径
    dataset_path: Path
    report_markdown_path: Path
    report_excel_path: Path
    
    # 统计信息
    total_cases: int
    avg_score: float
    metrics_summary: dict[str, float]
    
    # 元数据
    execution_time: float
    timestamp: str
    
    def __str__(self) -> str:
        return (
            f"EvalResult(\n"
            f"  Cases: {self.total_cases}\n"
            f"  Avg Score: {self.avg_score:.2f}\n"
            f"  Time: {self.execution_time:.1f}s\n"
            f"  Report: {self.report_excel_path}\n"
            f")"
        )
