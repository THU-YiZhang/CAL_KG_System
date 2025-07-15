#!/usr/bin/env python3
"""
最基础的测试 - 只测试知识图谱加载和子图提取
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))


def print_progress(message, status="INFO"):
    """打印进度信息"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    status_icons = {
        "INFO": "ℹ️",
        "SUCCESS": "✅", 
        "ERROR": "❌",
        "WARNING": "⚠️"
    }
    icon = status_icons.get(status, "ℹ️")
    print(f"[{timestamp}] {icon}  {message}")


async def test_basic():
    """最基础的测试"""
    print("🔍 基础组件测试")
    print("=" * 40)
    
    try:
        # 1. 配置
        print_progress("1. 初始化配置...")
        from src.utils.config_manager import ConfigManager
        config = ConfigManager()
        print_progress("配置初始化完成", "SUCCESS")
        
        # 2. 知识图谱
        print_progress("2. 加载知识图谱...")
        from src.core.kg_loader import KGLoader
        kg_loader = KGLoader(config)
        kg_data = await kg_loader.load_knowledge_graph()
        print_progress(f"知识图谱加载完成：{len(kg_data['nodes'])} 节点，{len(kg_data['edges'])} 边", "SUCCESS")
        
        # 3. 子图提取
        print_progress("3. 提取子图...")
        from src.visualization.mermaid_extractor import MermaidKGExtractor
        mermaid_extractor = MermaidKGExtractor(config)
        circuit_graphs = mermaid_extractor.extract_circuit_application_graphs(kg_data)
        print_progress(f"提取到 {len(circuit_graphs)} 个电路应用", "SUCCESS")
        
        if circuit_graphs:
            first_app = circuit_graphs[0]
            app_name = first_app['application_label']
            node_count = first_app['statistics']['total_nodes']
            edge_count = first_app['statistics']['total_edges']
            print_progress(f"第一个应用：{app_name} ({node_count} 节点，{edge_count} 边)", "INFO")
        
        print("\n✅ 基础测试完成！")
        return True
        
    except Exception as e:
        print_progress(f"测试失败：{e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_basic())
    sys.exit(0 if success else 1)
