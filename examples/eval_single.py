"""单文件评估示例

演示如何使用 MortgageRAGEvaluator 评估单个 PDF 文件

Usage:
    python examples/eval_single.py
"""

import asyncio
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from evaluator import MortgageRAGEvaluator, EvaluatorConfig


async def main():
    """主函数"""
    
    print("\n" + "="*80)
    print("Mortgage RAG 评估器 - 单文件评估示例")
    print("="*80 + "\n")
    
    # 1. 获取 PDF 文件路径
    print("请输入 PDF 文件路径:")
    pdf_input = input("> ").strip().strip('"').strip("'")
    
    pdf_path = Path(pdf_input)
    if not pdf_path.exists():
        print(f"\n错误: 文件不存在 - {pdf_path}")
        return
    
    if not pdf_path.suffix.lower() == '.pdf':
        print(f"\n错误: 不是 PDF 文件 - {pdf_path}")
        return
    
    # 2. 页码范围（可选）
    print("\n页码范围 (格式: 5-20，直接回车评估整个文档):")
    page_range_input = input("> ").strip()
    
    start_page = None
    end_page = None
    
    if page_range_input:
        # 解析页码范围
        if '-' not in page_range_input:
            print(f"\n错误: 页码范围格式错误，必须是 '起始页-结束页' 格式，例如: 5-20")
            return
        
        try:
            parts = page_range_input.split('-')
            if len(parts) != 2:
                raise ValueError("格式错误")
            
            start_page = int(parts[0].strip())
            end_page = int(parts[1].strip())
            
            if start_page < 1:
                print(f"\n错误: 起始页必须 >= 1")
                return
            
            if start_page > end_page:
                print(f"\n错误: 起始页 ({start_page}) 不能大于结束页 ({end_page})")
                return
            
            print(f"将评估页码范围: {start_page}-{end_page}")
            
        except ValueError:
            print(f"\n错误: 页码范围格式错误，必须是 '起始页-结束页' 格式，例如: 5-20")
            return
    
    # 3. 创建配置
    try:
        # 可以指定模型，默认使用 openai/gpt-4o-mini
        # config = EvaluatorConfig.from_env("bailian/qwen-plus")
        config = EvaluatorConfig.from_env()
        
        print(f"\n配置信息:")
        print(f"  LLM: {config.llm_uri}")
        print(f"  测试用例数: {config.num_test_cases}")
        print(f"  最大单元数: {config.max_units}")
        print(f"  Personas: {config.num_personas}")
        print(f"  RAG 服务: {config.rag_base_url}")
        print(f"  RAG 数据集: {config.rag_dataset_id}")
        print(f"  RAG Top-K: {config.rag_top_k}")
    except ValueError as e:
        print(f"\n错误: {e}")
        return
    
    # 4. 创建评估器
    evaluator = MortgageRAGEvaluator(config)
    
    # 5. 执行评估
    try:
        result = await evaluator.eval(str(pdf_path), start_page=start_page, end_page=end_page)
        
        # 6. 输出结果
        print("\n" + "="*80)
        print("评估结果")
        print("="*80)
        print(f"\n📊 总测试用例: {result.total_cases}")
        print(f"⭐ 平均分数: {result.avg_score:.2f}")
        print(f"⏱️  执行耗时: {result.execution_time:.1f}s")
        
        print(f"\n📈 各指标得分:")
        for metric_name, score in result.metrics_summary.items():
            print(f"  - {metric_name}: {score:.2f}")
        
        print(f"\n📁 输出文件:")
        print(f"  - 数据集: {result.dataset_path}")
        print(f"  - Markdown: {result.report_markdown_path}")
        print(f"  - Excel: {result.report_excel_path}")
        
        print(f"\n✅ 评估完成！\n")
        
    except Exception as e:
        print(f"\n❌ 评估失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
