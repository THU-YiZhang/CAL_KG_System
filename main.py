"""
CAL-KG系统主程序
电路领域自适应逻辑知识图谱系统的主入口
"""

import argparse
import time
from pathlib import Path
from typing import Optional

from src.document_splitter import DocumentSplitter
from src.main_logic_generator import MainLogicGenerator
from src.sub_logic_generator import SubLogicGenerator
from src.connection_analyzer import ConnectionAnalyzer
from src.knowledge_graph_fuser import KnowledgeGraphFuser
from src.visualizer import Visualizer
from src.utils import logger, file_manager, format_time_duration

class CALKGSystem:
    """CAL-KG系统主类"""
    
    def __init__(self, workers: int = 8):
        """初始化系统"""
        self.workers = workers
        self.start_time = None
        
        # 初始化各个模块
        self.document_splitter = DocumentSplitter(workers)
        self.main_logic_generator = MainLogicGenerator(workers)
        self.sub_logic_generator = SubLogicGenerator(workers)
        self.connection_analyzer = ConnectionAnalyzer(workers)
        self.knowledge_graph_fuser = KnowledgeGraphFuser(workers)
        self.visualizer = Visualizer()
        
        logger.info(f"CAL-KG系统初始化完成 (并发数: {workers})")
    
    def run_complete_pipeline(self, input_file: str = "data/input/06_12CMOS模拟IP线性集成电路_吴金 (1).md") -> bool:
        """运行完整的知识图谱构建流水线"""
        print("\n" + "="*80)
        print("🚀 CAL-KG 电路领域自适应逻辑知识图谱系统")
        print("="*80)
        print(f"📊 并发数: {self.workers}")
        print(f"📁 输入文件: {input_file}")
        print(f"⏰ 开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.start_time = time.time()
        
        try:
            # Step 1: 文档分割
            if not self._run_step("document_split", input_file):
                return False
            
            # Step 2: 主逻辑图谱生成
            if not self._run_step("main_logic"):
                return False
            
            # Step 3: 子逻辑图谱生成
            if not self._run_step("sub_logic"):
                return False
            
            # Step 4: 连接分析
            if not self._run_step("connection"):
                return False
            
            # Step 5: 可视化
            if not self._run_step("visualization"):
                return False
            
            # 生成最终报告
            self._generate_final_report()
            
            elapsed_time = time.time() - self.start_time
            print(f"\n🎉 CAL-KG系统构建完成!")
            print(f"⏱️ 总耗时: {format_time_duration(elapsed_time)}")
            print(f"📁 结果文件位于: output/final/")
            
            return True
            
        except Exception as e:
            logger.error(f"流水线执行失败: {e}")
            return False
    
    def _run_step(self, step_name: str, *args, **kwargs) -> bool:
        """运行单个步骤"""
        step_start_time = time.time()
        
        try:
            if step_name == "document_split":
                input_file = args[0] if args else "data/input/book.md"
                result = self.document_splitter.split_document(input_file)
                success = bool(result)
                
            elif step_name == "main_logic":
                result = self.main_logic_generator.generate_main_logic()
                success = bool(result)
                
            elif step_name == "sub_logic":
                result = self.sub_logic_generator.generate_sub_logic()
                success = bool(result)

            elif step_name == "connection":
                result = self.connection_analyzer.analyze_connections()
                success = bool(result)

            elif step_name == "fusion":
                result = self.knowledge_graph_fuser.fuse_knowledge_graphs()
                success = bool(result)

            elif step_name == "visualization":
                success = self.visualizer.generate_visualizations()
                
            else:
                logger.error(f"未知步骤: {step_name}")
                return False
            
            step_elapsed = time.time() - step_start_time
            
            if success:
                print(f"✅ {step_name} 完成，耗时: {format_time_duration(step_elapsed)}")
                logger.info(f"步骤 {step_name} 成功完成")
            else:
                print(f"❌ {step_name} 失败")
                logger.error(f"步骤 {step_name} 执行失败")
            
            return success
            
        except Exception as e:
            step_elapsed = time.time() - step_start_time
            print(f"❌ {step_name} 异常: {e}")
            logger.error(f"步骤 {step_name} 执行异常: {e}")
            return False
    
    def run_single_step(self, step_name: str, *args, **kwargs) -> bool:
        """运行单个步骤"""
        print(f"\n🎯 运行单步骤: {step_name}")
        self.start_time = time.time()
        
        success = self._run_step(step_name, *args, **kwargs)
        
        elapsed_time = time.time() - self.start_time
        print(f"\n📊 单步骤执行完成，耗时: {format_time_duration(elapsed_time)}")
        
        return success
    
    def _generate_final_report(self):
        """生成最终报告"""
        print("\n📋 生成最终报告...")
        
        try:
            elapsed_time = time.time() - self.start_time
            
            report_content = f"""# CAL-KG系统构建报告

## 📊 构建概要

- **构建时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}
- **总耗时**: {format_time_duration(elapsed_time)}
- **并发数**: {self.workers}
- **状态**: ✅ 成功完成

## 📁 输出文件结构

### 中间结果文件
- `output/intermediate/sections/` - 章节分割结果
- `output/intermediate/main_logic/` - 主逻辑图谱
- `output/intermediate/sub_logic/` - 子逻辑图谱
- `output/intermediate/connections/` - 连接分析结果

### 最终结果文件
- `output/final/knowledge_graph.json` - 完整知识图谱
- `output/final/interactive_graph.html` - 交互式图谱
- `output/final/static_graph.png` - 静态图谱
- `output/final/analysis_report.md` - 详细分析报告

## 🎯 系统特性

✅ **智能文档分割**: 自动识别章节结构
✅ **主逻辑图谱**: 构建知识层次关系
✅ **子逻辑图谱**: 深度提取技术细节
✅ **智能连接**: 以电路应用为中心的关联分析
✅ **并发处理**: {self.workers}个并发API调用
✅ **可视化展示**: 交互式和静态图谱

## 📞 使用说明

1. 查看交互式图谱: 打开 `output/final/interactive_graph.html`
2. 阅读详细分析: 查看 `output/final/analysis_report.md`
3. 获取原始数据: 使用 `output/final/knowledge_graph.json`

---
*报告生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}*
*CAL-KG System v1.0.0*
"""
            
            # 保存报告
            report_path = file_manager.get_path("final", "build_report.md")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            print(f"✅ 最终报告保存到: {report_path}")
            
        except Exception as e:
            logger.error(f"生成最终报告失败: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="CAL-KG 电路领域自适应逻辑知识图谱系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python main.py                           # 运行完整流水线
  python main.py --workers 16              # 指定16个并发
  python main.py --step document_split     # 只运行文档分割
  python main.py --input my_book.md        # 指定输入文件
        """
    )
    
    parser.add_argument(
        '--workers', 
        type=int, 
        default=8,
        help='并发数 (默认: 8)'
    )
    
    parser.add_argument(
        '--step',
        choices=['document_split', 'main_logic', 'sub_logic', 'connection', 'fusion', 'visualization'],
        help='只运行指定步骤'
    )
    
    parser.add_argument(
        '--input',
        type=str,
        default='data/input/06_12CMOS模拟IP线性集成电路_吴金 (1).md',
        help='输入文件路径 (默认: data/input/book.md)'
    )
    
    args = parser.parse_args()
    
    # 验证输入文件
    input_path = Path(args.input)
    if not input_path.exists():
        # 尝试相对路径
        input_path = Path("CAL_KG_System") / args.input
        if not input_path.exists():
            print(f"❌ 输入文件不存在: {args.input}")
            return
    
    # 创建系统实例
    system = CALKGSystem(workers=args.workers)
    
    # 运行系统
    if args.step:
        # 运行单个步骤
        success = system.run_single_step(args.step, str(input_path))
    else:
        # 运行完整流水线
        success = system.run_complete_pipeline(str(input_path))
    
    if success:
        print("\n🎊 系统运行成功!")
    else:
        print("\n❌ 系统运行失败!")
        exit(1)

if __name__ == "__main__":
    main()
