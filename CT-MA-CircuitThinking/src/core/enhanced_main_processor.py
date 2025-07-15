"""
Enhanced Main Processor for CT-MA System.

增强主处理器，整合问题设计、CoT生成、专家改进和统一JSON输出
"""

import asyncio
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from ..utils.logger import LoggerMixin
from ..utils.config_manager import ConfigManager
from ..core.kg_loader import KGLoader
from ..visualization.mermaid_extractor import MermaidKGExtractor
from ..agents.enhanced_logic_agent import EnhancedLogicAgent
from ..agents.enhanced_think_team import EnhancedThinkTeam
from ..agents.enhanced_answer_agent import EnhancedAnswerAgent
from ..agents.expert_improvement_team import ExpertImprovementTeam
from ..question_design.kg_based_question_designer import KGBasedQuestionDesigner, QuestionFilterAndSelector
from ..data_integration.unified_json_generator import UnifiedJSONGenerator


class EnhancedMainProcessor(LoggerMixin):
    """增强主处理器"""
    
    def __init__(self, config: ConfigManager):
        """Initialize enhanced main processor."""
        self.config = config
        
        # 初始化组件
        self.kg_loader = KGLoader(config)
        self.mermaid_extractor = MermaidKGExtractor(config)
        self.question_designer = KGBasedQuestionDesigner(config)
        self.question_filter = QuestionFilterAndSelector(config)
        self.logic_agent = EnhancedLogicAgent(config)
        self.think_team = EnhancedThinkTeam(config)
        self.answer_agent = EnhancedAnswerAgent(config)
        self.expert_team = ExpertImprovementTeam(config)
        self.json_generator = UnifiedJSONGenerator(config)
        
        # 并发控制
        self.semaphore = asyncio.Semaphore(config.get('concurrent.max_calls', 8))
        
    async def process_applications(
        self,
        max_applications: int = 3,
        questions_per_application: int = 5,
        output_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """处理多个电路应用"""
        
        if output_dir is None:
            output_dir = Path("output")
        
        self.logger.info(f"开始处理 {max_applications} 个电路应用，每个应用 {questions_per_application} 个问题")
        
        start_time = time.time()
        
        try:
            # 1. 加载知识图谱
            self.logger.info("🔄 步骤1: 加载统一知识图谱...")
            kg_data = await self.kg_loader.load_knowledge_graph()
            kg_load_time = time.time() - start_time
            self.logger.info(f"✅ 知识图谱加载完成：{len(kg_data['nodes'])} 个节点，{len(kg_data['edges'])} 条边，耗时 {kg_load_time:.2f} 秒")
            
            # 2. 提取Mermaid图谱
            self.logger.info("🔄 步骤2: 提取电路应用知识图谱...")
            extract_start = time.time()
            mermaid_graphs = self.mermaid_extractor.extract_circuit_application_graphs(kg_data)
            extract_time = time.time() - extract_start
            self.logger.info(f"✅ 图谱提取完成：{len(mermaid_graphs)} 个应用图谱，耗时 {extract_time:.2f} 秒")
            
            # 3. 选择要处理的应用
            selected_graphs = mermaid_graphs[:max_applications]
            self.logger.info(f"📋 选择处理前 {len(selected_graphs)} 个应用")
            
            # 4. 并发处理每个应用
            self.logger.info("🔄 步骤3: 并发处理各应用...")
            process_start = time.time()
            
            tasks = [
                self._process_single_application(graph_data, questions_per_application, i+1, len(selected_graphs))
                for i, graph_data in enumerate(selected_graphs)
            ]
            
            application_results = await asyncio.gather(*tasks, return_exceptions=True)
            process_time = time.time() - process_start
            
            # 5. 处理结果和异常
            successful_results = []
            failed_results = []
            
            for i, result in enumerate(application_results):
                if isinstance(result, Exception):
                    app_name = selected_graphs[i].get('application_label', f'应用{i+1}')
                    self.logger.error(f"❌ 应用 {app_name} 处理失败：{result}")
                    failed_results.append({'application': app_name, 'error': str(result)})
                else:
                    successful_results.append(result)
            
            self.logger.info(f"✅ 应用处理完成：成功 {len(successful_results)} 个，失败 {len(failed_results)} 个，耗时 {process_time:.2f} 秒")
            
            # 6. 生成统一JSON数据
            self.logger.info("🔄 步骤4: 生成统一JSON数据...")
            json_start = time.time()
            
            unified_records = []
            for result in successful_results:
                if result.get('success', False):
                    unified_record = self.json_generator.generate_unified_json_record(
                        application_info=result['application_info'],
                        mermaid_kg_data=result['mermaid_data'],
                        questions=result['questions'],
                        cot_results=result['cot_results'],
                        expert_improvements=result['expert_improvements'],
                        processing_metrics=result['processing_metrics']
                    )
                    unified_records.append(unified_record)
            
            # 保存统一JSON文件
            output_file = self.json_generator.save_unified_json(unified_records, output_dir)
            json_time = time.time() - json_start
            
            self.logger.info(f"✅ 统一JSON数据生成完成，耗时 {json_time:.2f} 秒")
            
            # 7. 生成最终报告
            total_time = time.time() - start_time
            
            final_report = {
                'success': True,
                'processing_summary': {
                    'total_applications_requested': max_applications,
                    'applications_processed': len(successful_results),
                    'applications_failed': len(failed_results),
                    'total_questions_generated': sum(len(r.get('questions', [])) for r in successful_results),
                    'total_cot_generated': sum(len(r.get('cot_results', [])) for r in successful_results),
                    'output_file': str(output_file),
                    'processing_times': {
                        'kg_loading': kg_load_time,
                        'graph_extraction': extract_time,
                        'application_processing': process_time,
                        'json_generation': json_time,
                        'total_time': total_time
                    }
                },
                'failed_applications': failed_results,
                'output_file_path': str(output_file)
            }
            
            self.logger.info(f"🎉 全部处理完成！总耗时 {total_time:.2f} 秒")
            self.logger.info(f"📄 结果文件：{output_file}")
            
            return final_report
            
        except Exception as e:
            self.logger.error(f"❌ 主处理流程失败：{e}")
            import traceback
            traceback.print_exc()
            
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    async def _process_single_application(
        self, 
        graph_data: Dict[str, Any], 
        questions_per_application: int,
        current_index: int,
        total_count: int
    ) -> Dict[str, Any]:
        """处理单个电路应用"""
        
        async with self.semaphore:
            app_name = graph_data.get('application_label', 'Unknown')
            self.logger.info(f"🔄 处理应用 {current_index}/{total_count}：{app_name}")
            
            app_start_time = time.time()
            
            try:
                # 1. 生成可读描述
                readable_description = self.mermaid_extractor.generate_readable_text_description(graph_data)
                
                # 2. 基于知识图谱设计问题
                question_start = time.time()
                question_result = await self.question_designer.execute({
                    'subgraph': graph_data,
                    'readable_description': readable_description,
                    'question_count': questions_per_application * 2  # 设计更多问题用于筛选
                })
                
                # 筛选最佳问题
                designed_questions = question_result.get('designed_questions', [])
                selected_questions = self.question_filter.filter_and_select_questions(
                    designed_questions, 
                    questions_per_application
                )
                question_time = time.time() - question_start
                
                self.logger.info(f"  📝 问题设计完成：设计 {len(designed_questions)} 个，筛选 {len(selected_questions)} 个，耗时 {question_time:.2f} 秒")
                
                # 3. 为每个问题生成CoT
                cot_start = time.time()
                cot_results = []
                
                for question in selected_questions:
                    cot_result = await self._generate_cot_for_question(
                        question, graph_data, readable_description
                    )
                    cot_results.append(cot_result)
                
                cot_time = time.time() - cot_start
                successful_cot = len([r for r in cot_results if r.get('success', False)])
                self.logger.info(f"  🧠 CoT生成完成：{successful_cot}/{len(selected_questions)} 个成功，耗时 {cot_time:.2f} 秒")
                
                # 4. 专家团队改进
                expert_start = time.time()
                expert_improvements = []
                
                for cot_result in cot_results:
                    if cot_result.get('success', False):
                        improvement_result = await self.expert_team.execute({
                            'question': cot_result['question_text'],
                            'logic': cot_result['logic'],
                            'think': cot_result['think'],
                            'answer': cot_result['answer'],
                            'question_id': cot_result['question_id']
                        })
                        expert_improvements.extend(improvement_result.get('improvements', []))
                
                expert_time = time.time() - expert_start
                self.logger.info(f"  👥 专家改进完成：{len(expert_improvements)} 次改进，耗时 {expert_time:.2f} 秒")
                
                # 5. 构建结果
                app_total_time = time.time() - app_start_time
                
                result = {
                    'success': True,
                    'application_info': {
                        'name': app_name,
                        'id': graph_data.get('application_id', ''),
                        'description': readable_description[:200] + '...' if len(readable_description) > 200 else readable_description,
                        'keywords': []  # 可以从图谱中提取
                    },
                    'mermaid_data': graph_data,
                    'questions': selected_questions,
                    'cot_results': cot_results,
                    'expert_improvements': expert_improvements,
                    'processing_metrics': {
                        'question_design_time': question_time,
                        'cot_generation_time': cot_time,
                        'expert_improvement_time': expert_time,
                        'total_time': app_total_time
                    }
                }
                
                self.logger.info(f"  ✅ 应用 {app_name} 处理完成，总耗时 {app_total_time:.2f} 秒")
                
                return result
                
            except Exception as e:
                self.logger.error(f"  ❌ 应用 {app_name} 处理失败：{e}")
                return {
                    'success': False,
                    'application_name': app_name,
                    'error': str(e),
                    'processing_time': time.time() - app_start_time
                }
    
    async def _generate_cot_for_question(
        self, 
        question: Dict[str, Any], 
        graph_data: Dict[str, Any], 
        readable_description: str
    ) -> Dict[str, Any]:
        """为单个问题生成CoT"""
        
        question_id = question.get('question_id', '')
        question_text = question.get('question_text', '')
        
        try:
            # 1. 生成Logic
            logic_start = time.time()
            logic_result = await self.logic_agent.execute({
                'subgraph': graph_data,
                'readable_description': readable_description,
                'question': question_text
            })
            logic_time = time.time() - logic_start
            
            if not logic_result.get('success', False):
                return {
                    'question_id': question_id,
                    'question_text': question_text,
                    'success': False,
                    'error': f"Logic生成失败：{logic_result.get('error', 'Unknown error')}"
                }
            
            logic = logic_result.get('logic', '')
            
            # 2. 生成Think
            think_start = time.time()
            think_result = await self.think_team.execute({
                'logic': logic,
                'question': question_text,
                'subgraph': graph_data
            })
            think_time = time.time() - think_start
            
            if not think_result.get('success', False):
                return {
                    'question_id': question_id,
                    'question_text': question_text,
                    'logic': logic,
                    'success': False,
                    'error': f"Think生成失败：{think_result.get('error', 'Unknown error')}"
                }
            
            think = think_result.get('think', '')
            
            # 3. 生成Answer
            answer_start = time.time()
            answer_result = await self.answer_agent.execute({
                'logic': logic,
                'think': think,
                'question': question_text
            })
            answer_time = time.time() - answer_start
            
            if not answer_result.get('success', False):
                return {
                    'question_id': question_id,
                    'question_text': question_text,
                    'logic': logic,
                    'think': think,
                    'success': False,
                    'error': f"Answer生成失败：{answer_result.get('error', 'Unknown error')}"
                }
            
            answer = answer_result.get('answer', '')
            
            return {
                'question_id': question_id,
                'question_text': question_text,
                'logic': logic,
                'think': think,
                'answer': answer,
                'success': True,
                'logic_time': logic_time,
                'think_time': think_time,
                'answer_time': answer_time,
                'total_time': logic_time + think_time + answer_time,
                'rag_evidence': think_result.get('rag_evidence', []),
                'rag_quality_score': think_result.get('rag_quality_score', 0)
            }
            
        except Exception as e:
            return {
                'question_id': question_id,
                'question_text': question_text,
                'success': False,
                'error': str(e)
            }
