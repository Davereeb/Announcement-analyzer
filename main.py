"""
A股公告情感分析系统
使用方法：python main.py

功能：
- 首次运行：从Excel导入全部数据，开始处理
- 中断后重新运行：自动跳过已完成记录，从中断处继续
- 全部完成后自动导出Excel结果
"""
import asyncio

from pipeline import run_pipeline
from exporter import export_to_excel
from db import get_stats, create_tables

if __name__ == "__main__":
    print("=" * 50)
    print("A股公告情感分析系统 启动")
    print("=" * 50)

    # 显示当前进度（如果是续跑）
    create_tables()
    stats = get_stats()
    if stats.get("total", 0) > 0:
        print(f"检测到历史进度：总计{stats['total']}条")
        print(f"  已完成: {stats.get('done', 0)} | 失败: {stats.get('failed', 0)} | 待处理: {stats.get('pending', 0)}")

    # 运行流水线
    asyncio.run(run_pipeline())

    # 导出结果
    print("\n开始导出Excel...")
    export_to_excel()
    print("全部完成！")
