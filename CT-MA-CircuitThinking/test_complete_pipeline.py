#!/usr/bin/env python3
"""
CT-MA系统完整流水线测试
测试从问题生成到回答生成的完整流程
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import time

# Add src to path and set working directory
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Change to project root directory to ensure correct relative paths
os.chdir(project_root)

from src.utils.config_manager import ConfigManager
from src.utils.logger import setup_logger, get_logger
from src.core.kg_loader import KGLoader
from src.visualization.mermaid_extractor import MermaidKGExtractor
from src.question_design.kg_based_question_designer import KGBasedQuestionDesigner
from src.question_design.question_filter import QuestionFilterAndSelector
from src.question_design.smart_node_selector import SmartNodeSelector
from src.rag.llamaindex_retriever import LlamaIndexRetriever
from src.agents.unified_cot_agent import UnifiedCoTAgent
from src.improvement.expert_team import ExpertTeamCoordinator


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


async def test_complete_pipeline():
    """测试完整的CT-MA流水线"""
    
    print("🚀 CT-MA系统完整流水线测试")
    print("=" * 80)
    print("测试范围：知识图谱加载 → 子图提取 → 问题设计 → Logic → Think → Answer → 专家评审")
    print("=" * 80)
    
    start_time = time.time()
    
    try:
        # ========== 第1步：系统初始化 ==========
        print_progress("第1步：系统初始化", "STEP")
        config = ConfigManager()
        setup_logger(debug=False, level="WARNING")  # 只显示警告和错误
        logger = get_logger(__name__)
        
        # ========== 第2步：知识图谱加载 ==========
        print_progress("第2步：加载知识图谱", "STEP")
        kg_loader = KGLoader(config)
        kg_data = await kg_loader.load_knowledge_graph()
        print_progress(f"知识图谱加载完成：{len(kg_data['nodes'])} 节点，{len(kg_data['edges'])} 边", "SUCCESS")
        
        # ========== 第3步：电路应用子图提取 ==========
        print_progress("第3步：提取电路应用子图", "STEP")
        mermaid_extractor = MermaidKGExtractor(config)
        circuit_graphs = mermaid_extractor.extract_circuit_application_graphs(kg_data)
        print_progress(f"提取到 {len(circuit_graphs)} 个电路应用子图", "SUCCESS")
        
        # 选择第一个电路应用进行测试
        if not circuit_graphs:
            print_progress("没有找到电路应用子图", "ERROR")
            return False
            
        test_subgraph = circuit_graphs[0]
        app_name = test_subgraph['application_label']
        node_count = test_subgraph['statistics']['total_nodes']
        edge_count = test_subgraph['statistics']['total_edges']
        print_progress(f"选择测试应用：{app_name} ({node_count} 节点，{edge_count} 边)", "INFO")
        
        # ========== 第4步：初始化所有组件 ==========
        print_progress("第4步：初始化系统组件", "STEP")
        
        # 问题设计器
        question_designer = KGBasedQuestionDesigner(config)
        await question_designer.initialize()
        
        question_filter = QuestionFilterAndSelector(config)
        
        # RAG检索器
        llamaindex_retriever = LlamaIndexRetriever(config)
        await llamaindex_retriever.setup()

        # 统一CoT Agent
        unified_cot_agent = UnifiedCoTAgent(config)
        await unified_cot_agent.initialize()

        expert_team = ExpertTeamCoordinator(config)
        await expert_team.initialize()
        
        print_progress("所有组件初始化完成", "SUCCESS")
        
        # ========== 第5步：智能节点选择 ==========
        print_progress("第5步：基于应用主题选择相关节点", "STEP")
        node_selector = SmartNodeSelector(config)
        await node_selector.initialize()

        selection_result = await node_selector.select_relevant_nodes_by_topic(
            app_name,  # 使用应用名称作为主题
            test_subgraph['subgraph_data'],
            max_nodes=15
        )

        if selection_result.get('success'):
            filtered_subgraph_data = selection_result['filtered_subgraph']
            selected_count = selection_result['selected_node_count']
            print_progress(f"智能选择了 {selected_count} 个相关节点", "SUCCESS")
        else:
            filtered_subgraph_data = test_subgraph['subgraph_data']
            print_progress("节点选择失败，使用完整子图", "WARNING")

        # ========== 第6步：基于小知识图谱设计问题 ==========
        print_progress("第6步：基于筛选后的知识图谱设计问题", "STEP")

        # 构建筛选后的子图结构
        filtered_test_subgraph = {
            'application_label': test_subgraph['application_label'],
            'subgraph_data': filtered_subgraph_data
        }

        # 从配置文件读取问题生成参数
        initial_count = config.get("question_generation.initial_generation_count", 10)
        final_count = config.get("question_generation.final_selection_count", 2)

        question_result = await question_designer.execute({
            'subgraph': filtered_test_subgraph,  # 使用筛选后的子图
            'readable_description': f"电路应用：{app_name}（基于{selected_count if selection_result.get('success') else len(test_subgraph['subgraph_data'].get('nodes', []))}个核心节点）",
            'question_count': initial_count  # 使用配置的初始生成数量
        })

        questions = question_result.get('questions', [])
        print_progress(f"设计了 {len(questions)} 个问题", "SUCCESS" if questions else "WARNING")

        if not questions:
            print_progress("问题设计失败，无法继续测试", "ERROR")
            return False

        # ========== 第7步：问题筛选 ==========
        print_progress("第7步：筛选高质量问题", "STEP")
        filtered_questions = question_filter.filter_and_select(questions, target_count=final_count)  # 使用配置的最终选择数量
        print_progress(f"筛选出 {len(filtered_questions)} 个高质量问题", "SUCCESS" if filtered_questions else "WARNING")

        if not filtered_questions:
            # 如果筛选失败，直接使用第一个问题
            filtered_questions = questions[:1]
            print_progress("筛选失败，使用第一个问题继续测试", "WARNING")

        test_question = filtered_questions[0]
        question_text = test_question.get('question_text', test_question.get('question', ''))
        print_progress(f"选择测试问题", "INFO")
        
        # ========== 第8步：统一CoT生成 ==========
        print_progress("第8步：生成统一的Logic-Think-Answer思维链", "STEP")

        # 准备RAG证据包
        evidence_package = {}
        try:
            # 使用RAG检索相关证据
            rag_query = f"{question_text} {app_name}"
            evidence_package = await llamaindex_retriever.retrieve_evidence(rag_query)
        except Exception as e:
            print_progress(f"RAG检索失败: {e}", "WARNING")
            evidence_package = {}

        cot_input = {
            'question': question_text,
            'subgraph': filtered_subgraph_data,
            'evidence_package': evidence_package
        }

        cot_result = await unified_cot_agent.execute(cot_input)
        cot_success = cot_result.get('success', False)

        if cot_success:
            logic_content = cot_result.get('logic', '')
            think_content = cot_result.get('think', '')
            answer_content = cot_result.get('answer', '')
            validation = cot_result.get('validation', {})

            print_progress(f"统一CoT生成成功：Logic({len(logic_content)}字符) Think({len(think_content)}字符) Answer({len(answer_content)}字符)", "SUCCESS")

            if not validation.get('overall_valid', False):
                print_progress(f"CoT质量警告: {validation.get('issues', [])}", "WARNING")
        else:
            print_progress("统一CoT生成失败", "ERROR")
            return False
        
        # ========== 第9步：专家团队评审 ==========
        print_progress("第9步：专家团队评审和改进", "STEP")
        expert_result = await expert_team.execute({
            'question': question_text,
            'logic': logic_content,
            'think': think_content,
            'answer': answer_content,
            'question_id': f'{app_name}_test'
        })
        
        improvement_plan = expert_result.get('improvement_plan', {})
        expert_reviews = expert_result.get('expert_reviews', {})
        
        if improvement_plan and expert_reviews:
            overall_score = improvement_plan.get('overall_score', 0)
            strategy = improvement_plan.get('improvement_strategy', 'unknown')
            print_progress(f"专家评审完成：评分 {overall_score:.1f}/10，策略 {strategy}", "SUCCESS")
        else:
            print_progress("专家评审失败", "ERROR")
            return False
        
        # ========== 第10步：生成最终结果 ==========
        print_progress("第10步：生成最终测试结果", "STEP")
        
        final_result = {
            'test_metadata': {
                'test_time': datetime.now().isoformat(),
                'application': app_name,
                'total_duration': time.time() - start_time,
                'pipeline_steps': 11
            },
            'subgraph_info': {
                'application_label': app_name,
                'node_count': node_count,
                'edge_count': edge_count,
                'mermaid_syntax': test_subgraph.get('mermaid_syntax', '')
            },
            'question': {
                'text': question_text,
                'quality_score': test_question.get('quality_score', 0),
                'difficulty_level': test_question.get('difficulty_level', 'unknown')
            },
            'cot_results': {
                'logic': logic_content,
                'think': think_content,
                'answer': answer_content
            },
            'expert_evaluation': {
                'overall_score': overall_score,
                'strategy': strategy,
                'reviews': expert_reviews,
                'improvement_plan': improvement_plan
            },
            'pipeline_success': True
        }
        
        # 保存测试结果
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"pipeline_test_result_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_result, f, ensure_ascii=False, indent=2)
        
        print_progress(f"测试结果已保存到：{output_file}", "SUCCESS")
        
        # ========== 测试总结 ==========
        total_time = time.time() - start_time
        print("\n" + "=" * 80)
        print("🎉 CT-MA系统完整流水线测试成功完成！")
        print("=" * 80)
        print(f"📊 测试总结：")
        print(f"  测试应用：{app_name}")
        print(f"  总耗时：{total_time:.1f} 秒")
        print(f"  问题数量：{len(questions)} → {len(filtered_questions)}")
        print(f"  Logic长度：{len(logic_content)} 字符")
        print(f"  Think长度：{len(think_content)} 字符")
        print(f"  Answer长度：{len(answer_content)} 字符")
        print(f"  专家评分：{overall_score:.1f}/10")
        print(f"  输出文件：{output_file}")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print_progress(f"流水线测试失败：{e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    success = await test_complete_pipeline()
    
    if success:
        print("\n✅ 完整流水线测试成功！")
    else:
        print("\n❌ 完整流水线测试失败！")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
