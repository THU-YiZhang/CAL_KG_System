"""
Knowledge Graph Based Question Designer for CT-MA System.

基于知识图谱的问题设计、筛选和难度过滤系统
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..utils.logger import LoggerMixin
from ..utils.config_manager import ConfigManager
from ..agents.base_agent import BaseAgent
from .question_types import AnalogCircuitQuestionTypes, QuestionType, DifficultyLevel


class KGBasedQuestionDesigner(BaseAgent):
    """基于知识图谱的问题设计器"""
    
    def __init__(self, config: ConfigManager):
        """Initialize KG-based question designer."""
        super().__init__(config, "kg_question_designer")
        self.question_types = AnalogCircuitQuestionTypes()
        
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute question design based on knowledge graph."""
        subgraph = input_data.get('subgraph')
        readable_description = input_data.get('readable_description', '')
        question_count = input_data.get('question_count', 3)
        
        if not subgraph:
            raise ValueError("No subgraph provided")
        
        app_label = subgraph.get('application_label', 'Unknown')
        self.logger.info(f"基于知识图谱为 {app_label} 设计 {question_count} 个问题")
        
        # 设计问题
        questions = await self._design_kg_based_questions(subgraph, readable_description, question_count)
        
        return {
            'success': len(questions) > 0,
            'application': app_label,
            'questions': questions,  # 统一字段名
            'designed_questions': questions,  # 保持兼容性
            'question_count': len(questions),
            'design_timestamp': datetime.now().isoformat()
        }
    
    async def _design_kg_based_questions(
        self,
        subgraph: Dict[str, Any],
        readable_description: str,
        question_count: int
    ) -> List[Dict[str, Any]]:
        """基于知识图谱设计问题，确保类型多样性"""

        app_label = subgraph.get('application_label', '未知应用')

        # 分析知识图谱结构
        kg_analysis = self._analyze_kg_structure(subgraph)

        # 生成多样化的问题类型和难度组合
        question_specs = self._generate_question_specifications(question_count)

        # 为每种类型设计问题
        all_questions = []
        for spec in question_specs:
            question_type = spec['type']
            difficulty = spec['difficulty']

            # 构建针对特定类型的问题设计prompt
            prompt = self._build_typed_question_design_prompt(
                app_label, readable_description, kg_analysis, question_type, difficulty
            )

            # 调用LLM设计问题
            messages = [
                self._build_system_message(self._get_question_design_system_prompt()),
                self._build_user_message(prompt)
            ]

            response = await self._call_llm(messages)

            # 解析问题并添加类型信息
            questions = self._parse_designed_questions(response)
            for question in questions:
                question['question_type'] = question_type
                question['difficulty_level'] = difficulty
                question['type_description'] = self.question_types.get_question_type_description(question_type)

            all_questions.extend(questions)

        return all_questions[:question_count]  # 确保不超过请求数量

    def _generate_question_specifications(self, question_count: int) -> List[Dict[str, str]]:
        """生成多样化的问题类型和难度规格"""
        specs = []

        # 获取类型和难度分布
        type_dist = self.question_types.get_question_types_distribution(self.config.config)
        difficulty_dist = self.question_types.get_difficulty_distribution(self.config.config)

        for i in range(question_count):
            question_type, difficulty = self.question_types.select_question_type_and_difficulty(self.config.config)
            specs.append({
                'type': question_type,
                'difficulty': difficulty
            })

        return specs

    def _build_typed_question_design_prompt(
        self,
        app_label: str,
        readable_description: str,
        kg_analysis: Dict[str, Any],
        question_type: str,
        difficulty: str
    ) -> str:
        """构建针对特定类型的问题设计提示"""

        # 获取问题类型描述
        type_description = self.question_types.get_question_type_description(question_type)

        # 获取问题模板（如果有）
        template = self.question_types.get_question_template(question_type, difficulty)

        # 构建知识图谱信息
        kg_info = self._format_kg_analysis_for_prompt(kg_analysis)

        prompt = f"""请基于以下知识图谱信息，设计一个{type_description}的问题。

目标应用: {app_label}
应用描述: {readable_description}
问题类型: {type_description}
难度等级: {difficulty}

知识图谱分析:
{kg_info}

设计要求:
1. 问题必须紧贴{app_label}这个具体应用
2. 问题类型必须符合"{type_description}"的特点
3. 难度等级为"{difficulty}"
4. 问题要能够利用提供的知识图谱节点进行回答
5. 问题要具有技术深度和实际意义

"""

        if template:
            prompt += f"""参考模板: {template}

请基于此模板，结合具体的知识图谱信息，设计一个具体的问题。

"""

        prompt += """输出格式:
<question>
[具体的问题文本，确保问题清晰、具体、有技术深度]
</question>

要求:
1. 问题要具体明确，避免过于宽泛
2. 问题要有技术挑战性，体现专业深度
3. 问题要能够基于提供的知识图谱节点进行深入分析
4. 问题表述要专业准确，符合模拟电路领域规范
"""

        return prompt

    def _format_kg_analysis_for_prompt(self, kg_analysis: Dict[str, Any]) -> str:
        """格式化知识图谱分析信息用于提示"""
        info_parts = []

        # 节点统计
        node_counts = kg_analysis.get('node_counts', {})
        info_parts.append(f"节点统计: 基础概念{node_counts.get('basic_concepts', 0)}个, "
                         f"核心技术{node_counts.get('core_technologies', 0)}个, "
                         f"电路应用{node_counts.get('applications', 0)}个")

        # 关键技术节点
        key_techs = kg_analysis.get('key_technologies', [])
        if key_techs:
            info_parts.append(f"关键技术: {', '.join(key_techs[:5])}")  # 只显示前5个

        # 技术层次
        tech_layers = kg_analysis.get('tech_layers', {})
        if tech_layers:
            info_parts.append(f"技术层次: {len(tech_layers)}层技术结构")

        return '\n'.join(info_parts)

    def _analyze_kg_structure(self, subgraph: Dict[str, Any]) -> Dict[str, Any]:
        """分析知识图谱结构"""
        nodes = subgraph.get('nodes', [])
        edges = subgraph.get('edges', [])
        
        # 按类型分类节点
        basic_concepts = [n for n in nodes if n.get('node_type') == 'basic_concept']
        core_technologies = [n for n in nodes if n.get('node_type') == 'core_technology']
        applications = [n for n in nodes if n.get('node_type') == 'circuit_application']
        
        # 提取关键技术
        key_technologies = [tech.get('label', '') for tech in core_technologies[:10]]  # 取前10个核心技术

        # 分析技术层次
        tech_layers = self._identify_tech_layers(nodes, edges)

        # 分析关键路径
        key_paths = self._identify_key_paths(nodes, edges)

        return {
            'node_counts': {
                'basic_concepts': len(basic_concepts),
                'core_technologies': len(core_technologies),
                'applications': len(applications)
            },
            'key_technologies': key_technologies,
            'tech_layers': tech_layers,
            'key_paths': key_paths,
            'complexity_indicators': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'avg_connections': len(edges) / len(nodes) if nodes else 0
            }
        }
    
    def _identify_tech_layers(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """识别技术层次"""
        layers = {
            'foundation': [],  # 基础层
            'core': [],        # 核心层
            'application': []  # 应用层
        }
        
        for node in nodes:
            node_type = node.get('node_type', '')
            label = node.get('label', '')
            
            if node_type == 'basic_concept':
                layers['foundation'].append(label)
            elif node_type == 'core_technology':
                layers['core'].append(label)
            elif node_type == 'circuit_application':
                layers['application'].append(label)
        
        return layers
    
    def _identify_key_paths(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """识别关键技术路径"""
        # 简化的路径识别算法
        paths = []
        
        # 找到从基础概念到应用的路径
        concept_nodes = [n for n in nodes if n.get('node_type') == 'basic_concept']
        app_nodes = [n for n in nodes if n.get('node_type') == 'circuit_application']
        
        for concept in concept_nodes[:3]:  # 取前3个概念
            for app in app_nodes[:2]:      # 取前2个应用
                path = {
                    'start': concept.get('label', ''),
                    'end': app.get('label', ''),
                    'path_type': 'concept_to_application'
                }
                paths.append(path)
        
        return paths
    
    def _get_question_design_system_prompt(self) -> str:
        """获取问题设计系统prompt"""
        return """你是电路设计问题设计专家，专门基于知识图谱设计高质量的多跳推理问题。

你的任务是：
1. 基于知识图谱的结构和内容，设计具有挑战性的问题
2. 确保问题需要跨越多个技术层次进行推理
3. 问题应该测试对技术关系和演进逻辑的理解
4. 设计不同难度级别的问题

问题设计原则：
- 基于真实的知识图谱内容，不要编造
- 问题应该有明确的推理路径
- 涵盖从基础概念到核心技术再到应用的完整链条
- 包含定量分析和定性分析要求
- 体现工程实践的复杂性

输出格式要求：
- 必须输出标准JSON格式
- 使用以下结构：
{
  "questions": [
    {
      "question_id": "q1",
      "question_text": "问题描述",
      "difficulty_level": "简单/中等/困难",
      "reasoning_path": "推理路径描述",
      "focus_points": "考察重点",
      "quantitative_requirements": "定量要求",
      "quality_score": 4.0,
      "complexity_score": 3.5,
      "relevance_score": 4.0
    }
  ]
}"""
    
    def _build_question_design_prompt(
        self, 
        app_label: str, 
        readable_description: str, 
        kg_analysis: Dict[str, Any], 
        question_count: int
    ) -> str:
        """构建问题设计prompt"""
        
        node_counts = kg_analysis['node_counts']
        tech_layers = kg_analysis['tech_layers']
        complexity = kg_analysis['complexity_indicators']
        
        prompt = f"""基于以下知识图谱信息，为"{app_label}"设计{question_count}个高质量的多跳推理问题：

【目标应用】: {app_label}

【知识图谱结构分析】:
- 基础概念: {node_counts['basic_concepts']} 个
- 核心技术: {node_counts['core_technologies']} 个  
- 电路应用: {node_counts['applications']} 个
- 总连接数: {complexity['total_edges']} 条
- 平均连接度: {complexity['avg_connections']:.2f}

【技术层次分布】:
基础层概念: {', '.join(tech_layers['foundation'][:5])}...
核心层技术: {', '.join(tech_layers['core'][:5])}...
应用层: {', '.join(tech_layers['application'][:3])}...

【知识图谱详细描述】:
{readable_description}

请设计{question_count}个问题，要求：

1. 问题难度分布：
   - 中等难度: {max(1, question_count//2)} 个
   - 高难度: {question_count - max(1, question_count//2)} 个

2. 问题类型要求：
   - 每个问题都要基于实际的知识图谱内容
   - 需要跨越至少3个技术层次进行推理
   - 包含定量分析要求（参数计算、性能评估等）
   - 体现工程实践中的技术权衡

3. 推理路径要求：
   - 明确的从基础概念→核心技术→应用实现的路径
   - 涉及多个技术节点的协同分析
   - 包含技术选择的逻辑依据

请严格按照以下JSON格式输出，不要添加任何其他文字：

{{
  "questions": [
    {{
      "question_id": "q1",
      "question_text": "[具体问题描述，基于知识图谱内容]",
      "difficulty_level": "中等",
      "reasoning_path": "[基础概念] → [核心技术1] → [核心技术2] → [应用实现] → [结论]",
      "focus_points": "[主要考察的技术能力和知识点]",
      "quantitative_requirements": "[具体的计算或分析要求]",
      "quality_score": 4.0,
      "complexity_score": 3.5,
      "relevance_score": 4.0
    }}
  ]
}}

注意：
1. 必须输出有效的JSON格式
2. 问题必须基于提供的知识图谱内容，不要编造技术节点
3. 确保推理路径中的每个节点都在知识图谱中存在
3. 问题应该有实际的工程意义和应用价值
4. 难度级别要合理分布，体现递进关系"""
        
        return prompt
    
    def _parse_designed_questions(self, response: str) -> List[Dict[str, Any]]:
        """解析设计的问题 - 支持JSON格式"""
        questions = []

        # 调试：打印原始响应
        self.logger.info(f"Raw LLM response: {response[:500]}...")

        # 首先尝试解析JSON格式
        try:
            # 查找JSON内容
            import json
            import re

            # 尝试提取JSON部分
            json_match = re.search(r'\{.*"questions".*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)

                if 'questions' in data and isinstance(data['questions'], list):
                    for q in data['questions']:
                        if isinstance(q, dict) and 'question_text' in q:
                            # 标准化字段名
                            question_data = {
                                'question_id': q.get('question_id', f"q_{len(questions)+1}"),
                                'question_text': q.get('question_text', ''),
                                'difficulty_level': q.get('difficulty_level', '中等'),
                                'reasoning_path': q.get('reasoning_path', ''),
                                'focus_points': q.get('focus_points', ''),
                                'quantitative_requirements': q.get('quantitative_requirements', ''),
                                'quality_score': float(q.get('quality_score', 4.0)),
                                'complexity_score': float(q.get('complexity_score', 3.5)),
                                'relevance_score': float(q.get('relevance_score', 4.0))
                            }
                            questions.append(question_data)

                    self.logger.info(f"Successfully parsed {len(questions)} questions from JSON")
                    return questions

        except (json.JSONDecodeError, AttributeError, KeyError) as e:
            self.logger.warning(f"JSON parsing failed: {e}, trying fallback parsing")

        # 如果JSON解析失败，尝试原有的格式解析
        if '<questions>' in response and '</questions>' in response:
            content = response.split('<questions>')[1].split('</questions>')[0]
            
            # 分割问题块
            question_blocks = []
            current_block = ""
            
            for line in content.split('\n'):
                if line.strip().startswith('【问题') and ('】' in line):
                    if current_block:
                        question_blocks.append(current_block)
                    current_block = line + '\n'
                else:
                    current_block += line + '\n'
            
            if current_block:
                question_blocks.append(current_block)
            
            # 解析每个问题块
            for i, block in enumerate(question_blocks, 1):
                question_data = {
                    'question_id': f"kg_q_{i}",
                    'question_text': "",
                    'difficulty_level': "",
                    'reasoning_path': "",
                    'focus_points': "",
                    'quantitative_requirements': "",
                    'metadata': {}
                }
                
                lines = block.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    # 匹配实际的LLM输出格式
                    if line.startswith('【问题') and '】:' in line:
                        question_data['question_text'] = line.split('】:', 1)[-1].strip()
                    elif line.startswith('【难度级别】:'):
                        question_data['difficulty_level'] = line.split('】:', 1)[-1].strip()
                    elif line.startswith('【推理路径】:'):
                        question_data['reasoning_path'] = line.split('】:', 1)[-1].strip()
                    elif line.startswith('【考察重点】:'):
                        question_data['focus_points'] = line.split('】:', 1)[-1].strip()
                    elif line.startswith('【定量要求】:'):
                        question_data['quantitative_requirements'] = line.split('】:', 1)[-1].strip()
                    # 更宽松的匹配
                    elif '【难度级别】' in line and ':' in line:
                        question_data['difficulty_level'] = line.split(':', 1)[-1].strip()
                    elif '【推理路径】' in line and ':' in line:
                        question_data['reasoning_path'] = line.split(':', 1)[-1].strip()
                    elif '【考察重点】' in line and ':' in line:
                        question_data['focus_points'] = line.split(':', 1)[-1].strip()
                    elif '【定量要求】' in line and ':' in line:
                        question_data['quantitative_requirements'] = line.split(':', 1)[-1].strip()
                    # 兼容旧格式
                    elif line.startswith('问题描述：'):
                        question_data['question_text'] = line.split('：', 1)[-1].strip()
                    elif line.startswith('难度级别：'):
                        question_data['difficulty_level'] = line.split('：', 1)[-1].strip()
                    elif line.startswith('推理路径：'):
                        question_data['reasoning_path'] = line.split('：', 1)[-1].strip()
                    elif line.startswith('考察重点：'):
                        question_data['focus_points'] = line.split('：', 1)[-1].strip()
                    elif line.startswith('定量要求：'):
                        question_data['quantitative_requirements'] = line.split('：', 1)[-1].strip()

                # 添加默认质量评分
                question_data['quality_score'] = 4.0
                question_data['complexity_score'] = 3.5
                question_data['relevance_score'] = 4.0
                
                if question_data['question_text']:
                    questions.append(question_data)
        else:
            # 如果没有找到标准格式，尝试简单解析
            self.logger.warning("Standard format not found, trying simple parsing")
            lines = response.split('\n')
            current_question = ""
            question_count = 0

            for line in lines:
                line = line.strip()
                if line and ('问题' in line or '设计' in line or '分析' in line):
                    if current_question:
                        question_count += 1
                        questions.append({
                            'question_id': f"simple_q_{question_count}",
                            'question_text': current_question.strip(),
                            'difficulty_level': "中等",
                            'reasoning_path': "基于知识图谱推理",
                            'focus_points': "电路设计原理",
                            'quality_score': 3.0
                        })
                    current_question = line
                elif line and current_question:
                    current_question += " " + line

            # 添加最后一个问题
            if current_question:
                question_count += 1
                questions.append({
                    'question_id': f"simple_q_{question_count}",
                    'question_text': current_question.strip(),
                    'difficulty_level': "中等",
                    'reasoning_path': "基于知识图谱推理",
                    'focus_points': "电路设计原理",
                    'quality_score': 3.0
                })

        self.logger.info(f"Parsed {len(questions)} questions from response")
        return questions


class QuestionFilterAndSelector(LoggerMixin):
    """问题筛选和难度过滤器"""
    
    def __init__(self, config: ConfigManager):
        """Initialize question filter."""
        self.config = config
    
    def filter_and_select_questions(
        self, 
        questions: List[Dict[str, Any]], 
        target_count: int,
        difficulty_distribution: Dict[str, float] = None
    ) -> List[Dict[str, Any]]:
        """筛选和选择问题"""
        
        if difficulty_distribution is None:
            difficulty_distribution = {'中等': 0.4, '高': 0.6}
        
        self.logger.info(f"从 {len(questions)} 个问题中筛选 {target_count} 个")
        
        # 按难度分类
        questions_by_difficulty = {}
        for question in questions:
            difficulty = question.get('difficulty_level', '中等')
            if difficulty not in questions_by_difficulty:
                questions_by_difficulty[difficulty] = []
            questions_by_difficulty[difficulty].append(question)
        
        # 按分布选择
        selected_questions = []
        
        for difficulty, ratio in difficulty_distribution.items():
            target_num = int(target_count * ratio)
            available_questions = questions_by_difficulty.get(difficulty, [])
            
            # 质量评分和选择
            scored_questions = self._score_questions(available_questions)
            selected = scored_questions[:target_num]
            selected_questions.extend(selected)
        
        # 如果数量不够，从剩余问题中补充
        if len(selected_questions) < target_count:
            remaining_questions = [q for q in questions if q not in selected_questions]
            scored_remaining = self._score_questions(remaining_questions)
            needed = target_count - len(selected_questions)
            selected_questions.extend(scored_remaining[:needed])
        
        self.logger.info(f"筛选完成：选择了 {len(selected_questions)} 个问题")
        
        return selected_questions[:target_count]
    
    def _score_questions(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """为问题评分并排序"""
        scored_questions = []
        
        for question in questions:
            score = self._calculate_question_score(question)
            question['quality_score'] = score
            scored_questions.append(question)
        
        # 按评分排序
        scored_questions.sort(key=lambda x: x['quality_score'], reverse=True)
        
        return scored_questions
    
    def _calculate_question_score(self, question: Dict[str, Any]) -> float:
        """计算问题质量评分"""
        score = 0.0
        
        # 问题文本长度评分
        question_text = question.get('question_text', '')
        if len(question_text) > 50:
            score += 1.0
        
        # 推理路径复杂度评分
        reasoning_path = question.get('reasoning_path', '')
        path_steps = reasoning_path.count('→')
        score += min(path_steps * 0.5, 2.0)
        
        # 定量要求评分
        quant_req = question.get('quantitative_requirements', '')
        if quant_req and len(quant_req) > 10:
            score += 1.0
        
        # 考察重点评分
        focus_points = question.get('focus_points', '')
        if focus_points and len(focus_points) > 20:
            score += 1.0
        
        return score
