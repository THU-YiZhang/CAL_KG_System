"""
CAL-KG系统测试脚本
用于验证所有模块的功能
"""

import sys
import os
from pathlib import Path

# 添加src目录到Python路径
sys.path.append(str(Path(__file__).parent / "src"))

from main import CALKGSystem

def test_individual_modules():
    """测试各个模块"""
    print("🧪 开始模块测试...")
    
    # 创建系统实例
    system = CALKGSystem(workers=4)  # 使用较少的并发数进行测试
    
    # 测试文档分割
    print("\n1️⃣ 测试文档分割...")
    try:
        result = system.run_single_step("document_split", "data/input/book.md")
        print(f"   文档分割: {'✅ 成功' if result else '❌ 失败'}")
    except Exception as e:
        print(f"   文档分割: ❌ 异常 - {e}")
    
    # 测试主逻辑生成
    print("\n2️⃣ 测试主逻辑生成...")
    try:
        result = system.run_single_step("main_logic")
        print(f"   主逻辑生成: {'✅ 成功' if result else '❌ 失败'}")
    except Exception as e:
        print(f"   主逻辑生成: ❌ 异常 - {e}")
    
    # 测试子逻辑生成
    print("\n3️⃣ 测试子逻辑生成...")
    try:
        result = system.run_single_step("sub_logic")
        print(f"   子逻辑生成: {'✅ 成功' if result else '❌ 失败'}")
    except Exception as e:
        print(f"   子逻辑生成: ❌ 异常 - {e}")
    
    # 测试连接分析
    print("\n4️⃣ 测试连接分析...")
    try:
        result = system.run_single_step("connection")
        print(f"   连接分析: {'✅ 成功' if result else '❌ 失败'}")
    except Exception as e:
        print(f"   连接分析: ❌ 异常 - {e}")
    
    # 测试可视化
    print("\n5️⃣ 测试可视化...")
    try:
        result = system.run_single_step("visualization")
        print(f"   可视化: {'✅ 成功' if result else '❌ 失败'}")
    except Exception as e:
        print(f"   可视化: ❌ 异常 - {e}")

def test_complete_pipeline():
    """测试完整流水线"""
    print("\n🚀 测试完整流水线...")
    
    try:
        system = CALKGSystem(workers=4)
        result = system.run_complete_pipeline("data/input/book.md")
        print(f"完整流水线: {'✅ 成功' if result else '❌ 失败'}")
        
        if result:
            print("\n📁 检查输出文件...")
            
            # 检查各个阶段的输出文件
            expected_files = [
                ("sections", "document_sections.json"),
                ("main_logic", "main_logic_kg.json"),
                ("sub_logic", "sub_logic_kg_total.json"),
                ("connections", "circuit_connections.json"),
                ("final", "knowledge_graph.json"),
                ("final", "interactive_graph.html"),
                ("final", "static_graph.png"),
                ("final", "analysis_report.md")
            ]
            
            from src.utils import file_manager
            
            for category, filename in expected_files:
                try:
                    file_path = file_manager.get_path(category, filename)
                    if file_path.exists():
                        print(f"   ✅ {filename}")
                    else:
                        print(f"   ❌ {filename} (不存在)")
                except Exception as e:
                    print(f"   ❌ {filename} (检查失败: {e})")
        
    except Exception as e:
        print(f"完整流水线: ❌ 异常 - {e}")

def main():
    """主函数"""
    print("🎯 CAL-KG系统测试")
    print("="*50)
    
    # 检查输入文件
    input_file = Path("data/input/book.md")
    if not input_file.exists():
        print(f"❌ 输入文件不存在: {input_file}")
        print("请确保 data/input/book.md 文件存在")
        return
    
    print(f"✅ 输入文件存在: {input_file}")
    
    # 选择测试模式
    print("\n请选择测试模式:")
    print("1. 测试各个模块")
    print("2. 测试完整流水线")
    print("3. 两者都测试")
    
    try:
        choice = input("请输入选择 (1/2/3): ").strip()
        
        if choice == "1":
            test_individual_modules()
        elif choice == "2":
            test_complete_pipeline()
        elif choice == "3":
            test_individual_modules()
            test_complete_pipeline()
        else:
            print("❌ 无效选择")
            
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")

if __name__ == "__main__":
    main()
