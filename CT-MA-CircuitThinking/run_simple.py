#!/usr/bin/env python3
"""
简化的CT-MA运行脚本
抽取2个电路应用，每个应用生成3条数据
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
import time

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.config_manager import ConfigManager
from src.utils.logger import setup_logger, get_logger
from src.core.kg_loader import KGLoader
from src.visualization.mermaid_extractor import MermaidKGExtractor
from src.question_design.kg_based_question_designer import KGBasedQuestionDesigner
from src.question_design.question_filter import QuestionFilterAndSelector
from src.rag.llamaindex_retriever import LlamaIndexRetriever
from src.agents.enhanced_logic_agent import EnhancedLogicAgent
from src.agents.enhanced_think_team import EnhancedThinkAgent
from src.agents.answer_agent import AnswerAgent
from src.improvement.expert_team import ExpertTeamCoordinator


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


async def run_ct_ma_system():
    """运行CT-MA系统主流程"""
    
    print("🚀 启动CT-MA电路思维系统")
    print("=" * 60)
    print("配置：")
    print("  电路应用数量：2个")
    print("  每个应用生成数据：3条")
    print("=" * 60)
    
    try:
        # 1. 初始化配置
        print_progress("初始化系统配置...")
        config = ConfigManager()
        
        # 2. 加载知识图谱
        print_progress("加载知识图谱...")
        kg_loader = KGLoader(config)
        kg_data = await kg_loader.load_knowledge_graph()
        print_progress(f"知识图谱加载完成：{len(kg_data['nodes'])} 节点，{len(kg_data['edges'])} 边", "SUCCESS")
        
        # 3. 提取电路应用子图
        print_progress("提取电路应用知识图谱...")
        mermaid_extractor = MermaidKGExtractor(config)
        circuit_graphs_list = mermaid_extractor.extract_circuit_application_graphs(kg_data)
        
        # 选择前2个电路应用
        selected_graphs = circuit_graphs_list[:2]
        print_progress(f"选择电路应用：{[g['application_label'] for g in selected_graphs]}", "SUCCESS")
        
        # 4. 初始化各个组件
        print_progress("初始化系统组件...")

        # 问题设计器
        question_designer = KGBasedQuestionDesigner(config)
        await question_designer.initialize()

        question_filter = QuestionFilterAndSelector(config)

        # RAG检索器
        llamaindex_retriever = LlamaIndexRetriever(config)
        await llamaindex_retriever.setup()

        # 各个Agent
        logic_agent = EnhancedLogicAgent(config)
        await logic_agent.initialize()

        think_agent = EnhancedThinkAgent(config, llamaindex_retriever)
        await think_agent.initialize()

        answer_agent = AnswerAgent(config)
        await answer_agent.initialize()

        expert_team = ExpertTeamCoordinator(config)
        await expert_team.initialize()

        print_progress("系统组件初始化完成", "SUCCESS")
        
        # 5. 处理每个电路应用
        all_results = []
        
        for app_idx, subgraph in enumerate(selected_graphs, 1):
            app_name = subgraph['application_label']
            print(f"\n{'='*60}")
            print(f"🔧 处理电路应用 {app_idx}/2：{app_name}")
            print(f"{'='*60}")
            
            # 5.1 设计问题
            print_progress(f"为 {app_name} 设计问题...")
            question_result = await question_designer.execute({
                'subgraph': subgraph,
                'readable_description': f"电路应用：{app_name}",
                'question_count': 6
            })
            questions = question_result.get('questions', [])
            print_progress(f"问题设计结果：成功={question_result.get('success')}, 问题数量={len(questions)}")
            
            # 5.2 筛选问题
            print_progress("筛选高质量问题...")
            filtered_questions = question_filter.filter_and_select(questions, target_count=3)
            print_progress(f"筛选出 {len(filtered_questions)} 个高质量问题", "SUCCESS")
            
            # 5.3 为每个问题生成CoT数据
            app_results = []
            
            for q_idx, question_data in enumerate(filtered_questions, 1):
                print(f"\n📝 生成第 {q_idx}/3 条数据...")
                question_text = question_data['question']
                
                try:
                    # Logic分析
                    print_progress("生成Logic分析...")
                    logic_result = await logic_agent.execute(subgraph)
                    logic = logic_result.get('logic', '') if logic_result.get('success') else ''
                    
                    # Think分析
                    print_progress("生成Think分析...")
                    think_result = await think_agent.execute(subgraph)
                    think = think_result.get('think', '') if think_result.get('success') else ''
                    
                    # Answer生成
                    print_progress("生成Answer...")
                    answer_result = await answer_agent.execute(subgraph)
                    answer = answer_result.get('answer', '') if answer_result.get('success') else ''
                    
                    # 专家改进
                    print_progress("专家团队评审...")
                    expert_result = await expert_team.execute({
                        'question': question_text,
                        'logic': logic,
                        'think': think,
                        'answer': answer,
                        'question_id': f'{app_name}_q{q_idx}'
                    })
                    
                    improvement_plan = expert_result.get('improvement_plan', {})
                    overall_score = improvement_plan.get('overall_score', 0)
                    
                    print_progress(f"数据生成完成，专家评分：{overall_score:.1f}/10", "SUCCESS")
                    
                    # 保存结果
                    result = {
                        'application': app_name,
                        'question_id': f'{app_name}_q{q_idx}',
                        'question': question_text,
                        'mermaid_graph': subgraph.get('mermaid_syntax', ''),
                        'logic': logic,
                        'think': think,
                        'answer': answer,
                        'expert_score': overall_score,
                        'expert_review': expert_result
                    }
                    
                    app_results.append(result)
                    
                except Exception as e:
                    print_progress(f"生成第 {q_idx} 条数据失败：{e}", "ERROR")
                    continue
            
            all_results.extend(app_results)
            print_progress(f"{app_name} 处理完成，生成 {len(app_results)} 条数据", "SUCCESS")
        
        # 6. 保存最终结果
        print_progress("保存最终结果...")
        
        # 生成统一JSON
        final_data = {
            'metadata': {
                'generation_time': datetime.now().isoformat(),
                'total_applications': len(selected_graphs),
                'total_records': len(all_results),
                'applications': [g['application_label'] for g in selected_graphs]
            },
            'records': all_results
        }
        
        # 保存到文件
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"ct_ma_results_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        
        print_progress(f"结果已保存到：{output_file}", "SUCCESS")
        
        # 7. 显示总结
        print(f"\n{'='*60}")
        print("🎉 CT-MA系统运行完成！")
        print(f"{'='*60}")
        print(f"📊 运行总结：")
        print(f"  处理电路应用：{len(selected_graphs)} 个")
        print(f"  生成数据记录：{len(all_results)} 条")
        if all_results:
            avg_score = sum(r['expert_score'] for r in all_results) / len(all_results)
            print(f"  平均专家评分：{avg_score:.1f}/10")
        print(f"  输出文件：{output_file}")
        
        return True
        
    except Exception as e:
        print_progress(f"系统运行失败：{e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    # 设置日志
    setup_logger(debug=False)
    
    # 运行系统
    success = await run_ct_ma_system()
    
    if success:
        print("\n✅ 系统运行成功完成！")
    else:
        print("\n❌ 系统运行失败！")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
