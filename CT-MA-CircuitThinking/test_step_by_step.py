#!/usr/bin/env python3
"""
CT-MA系统逐步测试
逐步测试每个组件，便于调试
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.config_manager import ConfigManager
from src.utils.logger import setup_logger
from src.core.kg_loader import KGLoader
from src.visualization.mermaid_extractor import MermaidKGExtractor


def print_progress(message, status="INFO"):
    """打印进度信息"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    status_icons = {
        "INFO": "ℹ️",
        "SUCCESS": "✅", 
        "ERROR": "❌",
        "WARNING": "⚠️",
        "STEP": "🔧"
    }
    icon = status_icons.get(status, "ℹ️")
    print(f"[{timestamp}] {icon}  {message}")


async def test_step_1_basic_loading():
    """测试第1步：基础加载"""
    print_progress("测试第1步：基础系统加载", "STEP")
    
    try:
        # 配置初始化
        print_progress("初始化配置...", "INFO")
        config = ConfigManager()
        setup_logger(debug=False)
        print_progress("配置初始化完成", "SUCCESS")
        
        # 知识图谱加载
        print_progress("加载知识图谱...", "INFO")
        kg_loader = KGLoader(config)
        kg_data = await kg_loader.load_knowledge_graph()
        print_progress(f"知识图谱加载完成：{len(kg_data['nodes'])} 节点，{len(kg_data['edges'])} 边", "SUCCESS")
        
        return True, {'config': config, 'kg_data': kg_data}
        
    except Exception as e:
        print_progress(f"第1步失败：{e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False, None


async def test_step_2_subgraph_extraction(config, kg_data):
    """测试第2步：子图提取"""
    print_progress("测试第2步：子图提取", "STEP")
    
    try:
        # 子图提取
        print_progress("提取电路应用子图...", "INFO")
        mermaid_extractor = MermaidKGExtractor(config)
        circuit_graphs = mermaid_extractor.extract_circuit_application_graphs(kg_data)
        print_progress(f"提取到 {len(circuit_graphs)} 个电路应用子图", "SUCCESS")
        
        if not circuit_graphs:
            print_progress("没有找到电路应用子图", "ERROR")
            return False, None
        
        # 检查第一个子图
        test_subgraph = circuit_graphs[0]
        app_name = test_subgraph['application_label']
        node_count = test_subgraph['statistics']['total_nodes']
        edge_count = test_subgraph['statistics']['total_edges']
        
        print_progress(f"测试子图：{app_name} ({node_count} 节点，{edge_count} 边)", "INFO")
        
        # 检查子图数据结构
        subgraph_data = test_subgraph['subgraph_data']
        print_progress(f"子图数据：{len(subgraph_data['nodes'])} 节点，{len(subgraph_data['edges'])} 边", "INFO")
        
        return True, {'test_subgraph': test_subgraph, 'app_name': app_name}
        
    except Exception as e:
        print_progress(f"第2步失败：{e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False, None


async def test_step_3_question_design(config, test_subgraph, app_name):
    """测试第3步：问题设计"""
    print_progress("测试第3步：问题设计", "STEP")
    
    try:
        from src.question_design.kg_based_question_designer import KGBasedQuestionDesigner
        
        # 初始化问题设计器
        print_progress("初始化问题设计器...", "INFO")
        question_designer = KGBasedQuestionDesigner(config)
        await question_designer.initialize()
        print_progress("问题设计器初始化完成", "SUCCESS")
        
        # 设计问题
        print_progress("设计问题...", "INFO")
        question_result = await question_designer.execute({
            'subgraph': test_subgraph['subgraph_data'],
            'readable_description': f"电路应用：{app_name}",
            'question_count': 2
        })
        
        questions = question_result.get('questions', [])
        success = question_result.get('success', False)
        
        if success and questions:
            print_progress(f"问题设计成功：生成 {len(questions)} 个问题", "SUCCESS")
            for i, q in enumerate(questions, 1):
                question_text = q.get('question_text', q.get('question', ''))
                print_progress(f"问题{i}：{question_text[:100]}...", "INFO")
            return True, {'questions': questions}
        else:
            print_progress("问题设计失败", "ERROR")
            return False, None
        
    except Exception as e:
        print_progress(f"第3步失败：{e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False, None


async def test_step_4_rag_setup(config):
    """测试第4步：RAG设置"""
    print_progress("测试第4步：RAG设置", "STEP")
    
    try:
        from src.rag.llamaindex_retriever import LlamaIndexRetriever
        
        # 初始化RAG
        print_progress("初始化RAG检索器...", "INFO")
        llamaindex_retriever = LlamaIndexRetriever(config)
        await llamaindex_retriever.setup()
        print_progress("RAG检索器初始化完成", "SUCCESS")
        
        return True, {'rag_retriever': llamaindex_retriever}
        
    except Exception as e:
        print_progress(f"第4步失败：{e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False, None


async def test_step_5_agents(config, test_subgraph, app_name, rag_retriever):
    """测试第5步：Agents"""
    print_progress("测试第5步：Agents初始化和执行", "STEP")
    
    try:
        from src.agents.enhanced_logic_agent import EnhancedLogicAgent
        from src.agents.enhanced_think_team import EnhancedThinkAgent
        from src.agents.answer_agent import AnswerAgent
        
        # 准备输入数据
        agent_input = {
            'subgraph': test_subgraph['subgraph_data'],
            'readable_description': f"电路应用：{app_name}"
        }
        
        # Logic Agent
        print_progress("测试Logic Agent...", "INFO")
        logic_agent = EnhancedLogicAgent(config)
        await logic_agent.initialize()
        logic_result = await logic_agent.execute(agent_input)
        
        if logic_result.get('success'):
            logic_content = logic_result.get('logic', '')
            print_progress(f"Logic Agent成功：{len(logic_content)} 字符", "SUCCESS")
        else:
            print_progress("Logic Agent失败", "ERROR")
            return False, None
        
        # Think Agent
        print_progress("测试Think Agent...", "INFO")
        think_agent = EnhancedThinkAgent(config, rag_retriever)
        await think_agent.initialize()
        think_result = await think_agent.execute(agent_input)
        
        if think_result.get('success'):
            think_content = think_result.get('think', '')
            print_progress(f"Think Agent成功：{len(think_content)} 字符", "SUCCESS")
        else:
            print_progress("Think Agent失败", "ERROR")
            return False, None
        
        # Answer Agent
        print_progress("测试Answer Agent...", "INFO")
        answer_agent = AnswerAgent(config)
        await answer_agent.initialize()
        answer_result = await answer_agent.execute(agent_input)
        
        if answer_result.get('success'):
            answer_content = answer_result.get('answer', '')
            print_progress(f"Answer Agent成功：{len(answer_content)} 字符", "SUCCESS")
        else:
            print_progress("Answer Agent失败", "ERROR")
            return False, None
        
        return True, {
            'logic': logic_content,
            'think': think_content,
            'answer': answer_content
        }
        
    except Exception as e:
        print_progress(f"第5步失败：{e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False, None


async def main():
    """主函数 - 逐步测试"""
    print("🚀 CT-MA系统逐步测试")
    print("=" * 60)
    
    # 第1步：基础加载
    success, data = await test_step_1_basic_loading()
    if not success:
        print_progress("第1步失败，停止测试", "ERROR")
        return False
    
    config = data['config']
    kg_data = data['kg_data']
    
    # 第2步：子图提取
    success, data = await test_step_2_subgraph_extraction(config, kg_data)
    if not success:
        print_progress("第2步失败，停止测试", "ERROR")
        return False
    
    test_subgraph = data['test_subgraph']
    app_name = data['app_name']
    
    # 第3步：问题设计
    success, data = await test_step_3_question_design(config, test_subgraph, app_name)
    if not success:
        print_progress("第3步失败，停止测试", "ERROR")
        return False
    
    questions = data['questions']
    
    # 第4步：RAG设置
    success, data = await test_step_4_rag_setup(config)
    if not success:
        print_progress("第4步失败，停止测试", "ERROR")
        return False
    
    rag_retriever = data['rag_retriever']
    
    # 第5步：Agents
    success, data = await test_step_5_agents(config, test_subgraph, app_name, rag_retriever)
    if not success:
        print_progress("第5步失败，停止测试", "ERROR")
        return False
    
    logic = data['logic']
    think = data['think']
    answer = data['answer']
    
    print("\n" + "=" * 60)
    print("🎉 所有步骤测试成功！")
    print("=" * 60)
    print(f"应用：{app_name}")
    print(f"问题数量：{len(questions)}")
    print(f"Logic长度：{len(logic)} 字符")
    print(f"Think长度：{len(think)} 字符")
    print(f"Answer长度：{len(answer)} 字符")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
