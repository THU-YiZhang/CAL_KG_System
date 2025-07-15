"""
Multi-hop Logic Question Designer for CT-MA System.

Designs complex multi-hop reasoning questions based on circuit application subgraphs.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..utils.logger import LoggerMixin
from ..utils.config_manager import ConfigManager
from ..agents.base_agent import BaseAgent


class QuestionDesignAgent(BaseAgent):
    """Agent for designing multi-hop logic questions."""
    
    def __init__(self, config: ConfigManager, agent_type: str):
        """
        Initialize Question Design Agent.
        
        Args:
            config: Configuration manager
            agent_type: Type of question designer (complexity, logic, application)
        """
        super().__init__(config, f"question_{agent_type}_agent")
        self.agent_type = agent_type
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute question design based on agent type."""
        subgraph = input_data.get('subgraph')
        if not subgraph:
            raise ValueError("No subgraph provided")
        
        if self.agent_type == "complexity":
            return await self._design_complexity_questions(subgraph)
        elif self.agent_type == "logic":
            return await self._design_logic_questions(subgraph)
        elif self.agent_type == "application":
            return await self._design_application_questions(subgraph)
        else:
            raise ValueError(f"Unknown agent type: {self.agent_type}")
    
    async def _design_complexity_questions(self, subgraph: Dict[str, Any]) -> Dict[str, Any]:
        """Design questions focusing on complexity analysis."""
        prompt = self._build_complexity_prompt(subgraph)
        
        messages = [
            self._build_system_message("你是电路复杂度分析专家，专门设计多跳推理问题来测试对电路复杂性的理解。"),
            self._build_user_message(prompt)
        ]
        
        response = await self._call_llm(messages)
        
        return {
            'agent_type': 'complexity',
            'questions': self._parse_questions(response),
            'raw_output': response
        }
    
    async def _design_logic_questions(self, subgraph: Dict[str, Any]) -> Dict[str, Any]:
        """Design questions focusing on logical reasoning."""
        prompt = self._build_logic_prompt(subgraph)
        
        messages = [
            self._build_system_message("你是电路逻辑推理专家，专门设计需要多步逻辑推理的复杂问题。"),
            self._build_user_message(prompt)
        ]
        
        response = await self._call_llm(messages)
        
        return {
            'agent_type': 'logic',
            'questions': self._parse_questions(response),
            'raw_output': response
        }
    
    async def _design_application_questions(self, subgraph: Dict[str, Any]) -> Dict[str, Any]:
        """Design questions focusing on practical applications."""
        prompt = self._build_application_prompt(subgraph)
        
        messages = [
            self._build_system_message("你是电路应用专家，专门设计实际应用导向的多跳推理问题。"),
            self._build_user_message(prompt)
        ]
        
        response = await self._call_llm(messages)
        
        return {
            'agent_type': 'application',
            'questions': self._parse_questions(response),
            'raw_output': response
        }
    
    def _build_complexity_prompt(self, subgraph: Dict[str, Any]) -> str:
        """Build prompt for complexity questions."""
        app_label = subgraph.get('application_label', '未知应用')
        nodes = subgraph.get('nodes', [])
        
        # Extract different types of nodes
        basic_concepts = [n for n in nodes if n.get('node_type') == 'basic_concept']
        core_techs = [n for n in nodes if n.get('node_type') == 'core_technology']
        
        prompt = f"""基于以下电路知识子图谱，设计3个多跳逻辑推理问题，重点关注复杂度分析：

目标应用: {app_label}

基础概念节点:
"""
        for i, concept in enumerate(basic_concepts[:3], 1):
            prompt += f"{i}. {concept.get('label', '')}: {concept.get('summary', '')[:100]}...\n"
        
        prompt += "\n核心技术节点:\n"
        for i, tech in enumerate(core_techs[:3], 1):
            prompt += f"{i}. {tech.get('label', '')}: {tech.get('summary', '')[:100]}...\n"
        
        prompt += f"""

请设计3个多跳推理问题，要求：
1. 每个问题需要跨越至少3个知识节点进行推理
2. 重点分析技术复杂度、实现难度、性能权衡
3. 问题应该引导深入思考为什么选择这些技术组合
4. 包含定量分析要求（如性能指标、参数计算）

输出格式：
<questions>
【问题1】: [复杂度分析问题]
【推理路径】: [节点A] → [节点B] → [节点C] → [结论]
【关键考察点】: [技术复杂度的哪个方面]

【问题2】: [性能权衡问题]
【推理路径】: [节点A] → [节点B] → [节点C] → [结论]
【关键考察点】: [性能权衡的哪个方面]

【问题3】: [实现难度问题]
【推理路径】: [节点A] → [节点B] → [节点C] → [结论]
【关键考察点】: [实现难度的哪个方面]
</questions>"""
        
        return prompt
    
    def _build_logic_prompt(self, subgraph: Dict[str, Any]) -> str:
        """Build prompt for logic questions."""
        app_label = subgraph.get('application_label', '未知应用')
        path_analysis = subgraph.get('path_analysis', {})
        
        prompt = f"""基于以下电路知识子图谱，设计3个多跳逻辑推理问题，重点关注因果逻辑：

目标应用: {app_label}
关键瓶颈: {path_analysis.get('key_bottleneck', '未知瓶颈')}

请设计3个多跳逻辑推理问题，要求：
1. 每个问题需要建立清晰的因果链条
2. 测试对技术演进必然性的理解
3. 包含反向推理（从结果推原因）
4. 涉及多个技术选择的逻辑依据

输出格式：
<questions>
【问题1】: [因果链推理问题]
【逻辑类型】: [正向推理/反向推理/双向推理]
【考察重点】: [技术选择的逻辑依据]

【问题2】: [技术演进问题]
【逻辑类型】: [正向推理/反向推理/双向推理]
【考察重点】: [演进的必然性分析]

【问题3】: [设计决策问题]
【逻辑类型】: [正向推理/反向推理/双向推理]
【考察重点】: [决策的逻辑合理性]
</questions>"""
        
        return prompt
    
    def _build_application_prompt(self, subgraph: Dict[str, Any]) -> str:
        """Build prompt for application questions."""
        app_label = subgraph.get('application_label', '未知应用')
        
        prompt = f"""基于以下电路知识子图谱，设计3个应用导向的多跳推理问题：

目标应用: {app_label}

请设计3个实际应用导向的多跳推理问题，要求：
1. 从实际应用需求出发
2. 涉及多个技术环节的协同分析
3. 包含性能指标和实现约束
4. 考虑工程实践中的权衡取舍

输出格式：
<questions>
【问题1】: [需求分析问题]
【应用场景】: [具体的应用场景]
【技术挑战】: [主要的技术挑战]

【问题2】: [系统设计问题]
【应用场景】: [具体的应用场景]
【技术挑战】: [主要的技术挑战]

【问题3】: [优化改进问题]
【应用场景】: [具体的应用场景]
【技术挑战】: [主要的技术挑战]
</questions>"""
        
        return prompt
    
    def _parse_questions(self, response: str) -> List[Dict[str, Any]]:
        """Parse questions from LLM response."""
        questions = []
        
        if '<questions>' in response and '</questions>' in response:
            content = response.split('<questions>')[1].split('</questions>')[0]
            
            # Split by question markers
            question_blocks = []
            current_block = ""
            
            for line in content.split('\n'):
                if line.strip().startswith('【问题'):
                    if current_block:
                        question_blocks.append(current_block)
                    current_block = line + '\n'
                else:
                    current_block += line + '\n'
            
            if current_block:
                question_blocks.append(current_block)
            
            # Parse each question block
            for i, block in enumerate(question_blocks, 1):
                question_data = {
                    'question_id': f"q_{i}",
                    'question_text': "",
                    'metadata': {}
                }
                
                lines = block.strip().split('\n')
                for line in lines:
                    if line.startswith('【问题'):
                        question_data['question_text'] = line.split(':', 1)[-1].strip()
                    elif '】:' in line:
                        key = line.split('】:')[0].replace('【', '')
                        value = line.split('】:')[1].strip()
                        question_data['metadata'][key] = value
                
                if question_data['question_text']:
                    questions.append(question_data)
        
        return questions


class QuestionDesignCoordinator(LoggerMixin):
    """Coordinates multiple question design agents."""
    
    def __init__(self, config: ConfigManager):
        """Initialize coordinator."""
        self.config = config
        self.agents = {}
    
    async def initialize(self):
        """Initialize all question design agents."""
        self.logger.info("Initializing question design agents...")
        
        agent_types = ['complexity', 'logic', 'application']
        
        for agent_type in agent_types:
            agent = QuestionDesignAgent(self.config, agent_type)
            await agent.initialize()
            self.agents[agent_type] = agent
        
        self.logger.info("Question design agents initialized")
    
    async def design_questions_for_subgraph(self, subgraph: Dict[str, Any]) -> Dict[str, Any]:
        """Design comprehensive questions for a subgraph."""
        app_label = subgraph.get('application_label', 'Unknown')
        self.logger.info(f"Designing questions for: {app_label}")
        
        # Run all agents in parallel
        tasks = []
        for agent_type, agent in self.agents.items():
            task = agent.execute({'subgraph': subgraph})
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        all_questions = []
        agent_results = {}
        
        for i, (agent_type, result) in enumerate(zip(self.agents.keys(), results)):
            if isinstance(result, Exception):
                self.logger.error(f"Agent {agent_type} failed: {result}")
                continue
            
            agent_results[agent_type] = result
            all_questions.extend(result.get('questions', []))
        
        return {
            'application': app_label,
            'total_questions': len(all_questions),
            'questions_by_type': agent_results,
            'all_questions': all_questions,
            'generated_at': datetime.now().isoformat()
        }
    
    async def batch_design_questions(self, subgraphs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Design questions for multiple subgraphs."""
        self.logger.info(f"Designing questions for {len(subgraphs)} subgraphs")
        
        results = []
        for i, subgraph in enumerate(subgraphs, 1):
            try:
                app_label = subgraph.get('application_label', f'App_{i}')
                self.logger.info(f"Processing {i}/{len(subgraphs)}: {app_label}")
                
                question_set = await self.design_questions_for_subgraph(subgraph)
                results.append(question_set)
                
            except Exception as e:
                self.logger.error(f"Failed to design questions for subgraph {i}: {e}")
        
        return results
