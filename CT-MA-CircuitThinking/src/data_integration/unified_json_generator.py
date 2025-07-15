"""
Unified JSON Data Generator for CT-MA System.

统一JSON数据生成器，整合问题、知识图谱、CoT数据和专家修改意见
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from ..utils.logger import LoggerMixin
from ..utils.config_manager import ConfigManager


class UnifiedJSONGenerator(LoggerMixin):
    """统一JSON数据生成器"""
    
    def __init__(self, config: ConfigManager):
        """Initialize unified JSON generator."""
        self.config = config
        
    def generate_unified_json_record(
        self,
        application_info: Dict[str, Any],
        mermaid_kg_data: Dict[str, Any],
        questions: List[Dict[str, Any]],
        cot_results: List[Dict[str, Any]],
        expert_improvements: List[Dict[str, Any]],
        processing_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成统一的JSON记录"""
        
        app_name = application_info.get('name', 'Unknown')
        self.logger.info(f"为应用 {app_name} 生成统一JSON记录")
        
        # 构建统一数据结构
        unified_record = {
            'application_info': {
                'name': app_name,
                'application_id': application_info.get('id', ''),
                'processing_timestamp': datetime.now().isoformat(),
                'description': application_info.get('description', ''),
                'keywords': application_info.get('keywords', [])
            },
            
            'mermaid_knowledge_graph': {
                'syntax': mermaid_kg_data.get('mermaid_syntax', ''),
                'readable_description': mermaid_kg_data.get('readable_description', ''),
                'statistics': mermaid_kg_data.get('statistics', {}),
                'subgraph_data': {
                    'nodes_count': len(mermaid_kg_data.get('subgraph_data', {}).get('nodes', [])),
                    'edges_count': len(mermaid_kg_data.get('subgraph_data', {}).get('edges', [])),
                    'node_types_distribution': self._analyze_node_types(mermaid_kg_data.get('subgraph_data', {}))
                }
            },
            
            'generated_questions': self._format_questions_data(questions),
            
            'cot_analysis_results': self._format_cot_results(cot_results),
            
            'expert_improvement_history': self._format_expert_improvements(expert_improvements),
            
            'processing_summary': {
                'total_questions': len(questions),
                'successful_cot_generations': len([r for r in cot_results if r.get('success', False)]),
                'expert_improvement_iterations': len(expert_improvements),
                'final_quality_scores': [imp.get('final_score', 0) for imp in expert_improvements],
                'average_final_score': self._calculate_average_score(expert_improvements),
                'expert_satisfaction_rate': self._calculate_satisfaction_rate(expert_improvements),
                'processing_metrics': processing_metrics
            }
        }
        
        return unified_record
    
    def _analyze_node_types(self, subgraph_data: Dict[str, Any]) -> Dict[str, int]:
        """分析节点类型分布"""
        nodes = subgraph_data.get('nodes', [])
        type_counts = {}
        
        for node in nodes:
            node_type = node.get('node_type', 'unknown')
            type_counts[node_type] = type_counts.get(node_type, 0) + 1
        
        return type_counts
    
    def _format_questions_data(self, questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """格式化问题数据"""
        questions_by_difficulty = {}
        
        for question in questions:
            difficulty = question.get('difficulty_level', '中等')
            if difficulty not in questions_by_difficulty:
                questions_by_difficulty[difficulty] = []
            
            formatted_question = {
                'question_id': question.get('question_id', ''),
                'question_text': question.get('question_text', ''),
                'reasoning_path': question.get('reasoning_path', ''),
                'focus_points': question.get('focus_points', ''),
                'quantitative_requirements': question.get('quantitative_requirements', ''),
                'quality_score': question.get('quality_score', 0),
                'metadata': question.get('metadata', {})
            }
            
            questions_by_difficulty[difficulty].append(formatted_question)
        
        return {
            'total_questions': len(questions),
            'questions_by_difficulty': questions_by_difficulty,
            'difficulty_distribution': {
                difficulty: len(q_list) 
                for difficulty, q_list in questions_by_difficulty.items()
            }
        }
    
    def _format_cot_results(self, cot_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """格式化CoT结果数据"""
        formatted_results = []
        
        for result in cot_results:
            formatted_result = {
                'question_id': result.get('question_id', ''),
                'question_text': result.get('question_text', ''),
                'logic_analysis': result.get('logic', ''),
                'think_process': result.get('think', ''),
                'final_answer': result.get('answer', ''),
                'generation_success': result.get('success', False),
                'generation_metrics': {
                    'logic_generation_time': result.get('logic_time', 0),
                    'think_generation_time': result.get('think_time', 0),
                    'answer_generation_time': result.get('answer_time', 0),
                    'total_generation_time': result.get('total_time', 0),
                    'rag_evidence_count': len(result.get('rag_evidence', [])),
                    'rag_evidence_quality': result.get('rag_quality_score', 0)
                },
                'rag_evidence_used': result.get('rag_evidence', []),
                'error_info': result.get('error', '') if not result.get('success', False) else ''
            }
            
            formatted_results.append(formatted_result)
        
        return formatted_results
    
    def _format_expert_improvements(self, expert_improvements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """格式化专家改进数据"""
        if not expert_improvements:
            return {
                'total_iterations': 0,
                'final_score': 0,
                'is_satisfied': False,
                'improvement_history': []
            }
        
        # 按问题ID组织改进历史
        improvements_by_question = {}
        
        for improvement in expert_improvements:
            question_id = improvement.get('question_id', 'unknown')
            if question_id not in improvements_by_question:
                improvements_by_question[question_id] = []
            
            improvements_by_question[question_id].append({
                'iteration': improvement.get('iteration', 0),
                'overall_score': improvement.get('overall_score', 0),
                'detailed_scores': improvement.get('detailed_scores', {}),
                'is_satisfied': improvement.get('is_satisfied', False),
                'main_issues': improvement.get('main_issues', []),
                'improvement_suggestions': improvement.get('improvement_suggestions', []),
                'improved_content': improvement.get('improved_content', {}),
                'improvement_timestamp': improvement.get('timestamp', '')
            })
        
        # 计算总体统计
        all_final_scores = []
        all_satisfied = []
        total_iterations = 0
        
        for question_improvements in improvements_by_question.values():
            if question_improvements:
                final_improvement = question_improvements[-1]
                all_final_scores.append(final_improvement['overall_score'])
                all_satisfied.append(final_improvement['is_satisfied'])
                total_iterations += len(question_improvements)
        
        return {
            'total_iterations': total_iterations,
            'questions_improved': len(improvements_by_question),
            'average_final_score': sum(all_final_scores) / len(all_final_scores) if all_final_scores else 0,
            'satisfaction_rate': sum(all_satisfied) / len(all_satisfied) if all_satisfied else 0,
            'improvements_by_question': improvements_by_question,
            'summary_statistics': {
                'min_score': min(all_final_scores) if all_final_scores else 0,
                'max_score': max(all_final_scores) if all_final_scores else 0,
                'score_distribution': self._calculate_score_distribution(all_final_scores)
            }
        }
    
    def _calculate_average_score(self, expert_improvements: List[Dict[str, Any]]) -> float:
        """计算平均最终评分"""
        if not expert_improvements:
            return 0.0
        
        scores = [imp.get('overall_score', 0) for imp in expert_improvements]
        return sum(scores) / len(scores) if scores else 0.0
    
    def _calculate_satisfaction_rate(self, expert_improvements: List[Dict[str, Any]]) -> float:
        """计算专家满意率"""
        if not expert_improvements:
            return 0.0
        
        satisfied_count = sum(1 for imp in expert_improvements if imp.get('is_satisfied', False))
        return satisfied_count / len(expert_improvements)
    
    def _calculate_score_distribution(self, scores: List[float]) -> Dict[str, int]:
        """计算评分分布"""
        if not scores:
            return {}
        
        distribution = {
            'excellent': 0,  # 9-10分
            'good': 0,       # 7-8分
            'fair': 0,       # 5-6分
            'poor': 0        # 0-4分
        }
        
        for score in scores:
            if score >= 9:
                distribution['excellent'] += 1
            elif score >= 7:
                distribution['good'] += 1
            elif score >= 5:
                distribution['fair'] += 1
            else:
                distribution['poor'] += 1
        
        return distribution
    
    def save_unified_json(
        self, 
        unified_records: List[Dict[str, Any]], 
        output_dir: Path,
        filename_prefix: str = "ct_ma_unified_results"
    ) -> Path:
        """保存统一JSON数据"""
        
        # 创建输出目录
        output_dir.mkdir(exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{filename_prefix}_{timestamp}.json"
        output_file = output_dir / filename
        
        # 构建完整数据结构
        complete_data = {
            'workflow_metadata': {
                'generation_timestamp': datetime.now().isoformat(),
                'system_version': 'CT-MA-v2.0',
                'total_applications': len(unified_records),
                'processing_summary': self._generate_workflow_summary(unified_records)
            },
            'circuit_applications': unified_records,
            'global_statistics': self._generate_global_statistics(unified_records)
        }
        
        # 保存文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(complete_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"统一JSON数据已保存到: {output_file}")
        self.logger.info(f"文件大小: {output_file.stat().st_size} 字节")
        
        return output_file
    
    def _generate_workflow_summary(self, unified_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成工作流程摘要"""
        total_questions = sum(record['processing_summary']['total_questions'] for record in unified_records)
        total_successful_cot = sum(record['processing_summary']['successful_cot_generations'] for record in unified_records)
        
        all_scores = []
        for record in unified_records:
            scores = record['processing_summary']['final_quality_scores']
            all_scores.extend(scores)
        
        return {
            'total_questions_generated': total_questions,
            'total_successful_cot_generations': total_successful_cot,
            'overall_success_rate': total_successful_cot / total_questions if total_questions > 0 else 0,
            'average_quality_score': sum(all_scores) / len(all_scores) if all_scores else 0,
            'quality_score_range': {
                'min': min(all_scores) if all_scores else 0,
                'max': max(all_scores) if all_scores else 0
            }
        }
    
    def _generate_global_statistics(self, unified_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成全局统计信息"""
        total_nodes = sum(
            record['mermaid_knowledge_graph']['subgraph_data']['nodes_count'] 
            for record in unified_records
        )
        
        total_edges = sum(
            record['mermaid_knowledge_graph']['subgraph_data']['edges_count'] 
            for record in unified_records
        )
        
        # 统计节点类型分布
        global_node_types = {}
        for record in unified_records:
            node_types = record['mermaid_knowledge_graph']['subgraph_data']['node_types_distribution']
            for node_type, count in node_types.items():
                global_node_types[node_type] = global_node_types.get(node_type, 0) + count
        
        return {
            'knowledge_graph_statistics': {
                'total_nodes_processed': total_nodes,
                'total_edges_processed': total_edges,
                'average_nodes_per_application': total_nodes / len(unified_records) if unified_records else 0,
                'average_edges_per_application': total_edges / len(unified_records) if unified_records else 0,
                'global_node_type_distribution': global_node_types
            },
            'processing_efficiency': {
                'applications_processed': len(unified_records),
                'average_processing_time_per_application': self._calculate_average_processing_time(unified_records)
            }
        }
    
    def _calculate_average_processing_time(self, unified_records: List[Dict[str, Any]]) -> float:
        """计算平均处理时间"""
        total_time = 0
        count = 0
        
        for record in unified_records:
            metrics = record['processing_summary'].get('processing_metrics', {})
            if 'total_time' in metrics:
                total_time += metrics['total_time']
                count += 1
        
        return total_time / count if count > 0 else 0
