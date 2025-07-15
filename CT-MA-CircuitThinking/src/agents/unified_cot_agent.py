"""
Unified Chain-of-Thought Agent for CT-MA System.

统一的思维链Agent，同时生成Logic、Think、Answer三个部分，确保逻辑一致性
"""

import asyncio
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..utils.logger import LoggerMixin
from ..utils.config_manager import ConfigManager
from .base_agent import BaseAgent


class UnifiedCoTAgent(BaseAgent):
    """统一的思维链生成Agent"""
    
    def __init__(self, config: ConfigManager):
        """Initialize unified CoT agent."""
        super().__init__(config, "unified_cot_agent")
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute unified CoT generation.
        
        Args:
            input_data: Input containing question, subgraph, evidence_package
            
        Returns:
            Dictionary containing logic, think, answer
        """
        try:
            question = input_data.get('question', '')
            subgraph = input_data.get('subgraph', {})
            evidence_package = input_data.get('evidence_package', {})
            
            if not question:
                raise ValueError("No question provided in input data")
            if not subgraph:
                raise ValueError("No subgraph provided in input data")
            
            self.logger.info(f"Generating unified CoT for question about: {subgraph.get('application_label', 'unknown')}")
            
            # Generate unified CoT
            cot_result = await self._generate_unified_cot(question, subgraph, evidence_package)
            
            # Parse the result into separate components
            parsed_result = self._parse_cot_result(cot_result)
            
            # Validate the result
            validation_result = self._validate_cot_components(parsed_result)
            
            return {
                'success': True,
                'logic': parsed_result.get('logic', ''),
                'think': parsed_result.get('think', ''),
                'answer': parsed_result.get('answer', ''),
                'validation': validation_result,
                'generation_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Unified CoT generation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'logic': '',
                'think': '',
                'answer': ''
            }
    
    async def _generate_unified_cot(
        self, 
        question: str, 
        subgraph: Dict[str, Any], 
        evidence_package: Dict[str, Any]
    ) -> str:
        """
        Generate unified chain-of-thought response.
        
        Args:
            question: The specific question to analyze
            subgraph: Knowledge graph subgraph
            evidence_package: RAG evidence package
            
        Returns:
            Complete CoT response with logic, think, answer
        """
        # Build comprehensive prompt
        prompt = self._build_unified_cot_prompt(question, subgraph, evidence_package)
        
        # Prepare messages
        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": prompt}
        ]
        
        # Call LLM
        response = await self._call_llm(messages)
        
        return response
    
    def _build_unified_cot_prompt(
        self, 
        question: str, 
        subgraph: Dict[str, Any], 
        evidence_package: Dict[str, Any]
    ) -> str:
        """Build comprehensive prompt for unified CoT generation."""
        
        app_label = subgraph.get('application_label', '未知应用')
        
        # Extract and format knowledge graph information
        kg_info = self._format_knowledge_graph_info(subgraph)
        
        # Format RAG evidence
        rag_evidence = self._format_rag_evidence(evidence_package)
        
        prompt = f"""你是一位资深的模拟电路设计专家，需要针对具体问题进行完整的思维链分析。

问题: {question}

相关知识图谱信息:
{kg_info}

RAG检索到的技术证据:
{rag_evidence}

请按照以下格式生成完整的思维链分析：

<logic>
[针对这个问题的简洁逻辑思考，50-100字]
针对[问题核心]，关键技术节点是[节点1]→[节点2]→[节点3]，解决思路是[简短的技术路径]。
</logic>

<think>
[基于Logic的详细技术分析，800-1200字]

推理开始。基于上述Logic的分析思路，我将深入研究这个问题。

第一步：[Logic中提到的第一个关键技术点]
[详细分析这个技术点，包括原理、参数、公式等]
根据RAG证据[引用具体证据]，[技术细节分析]...

第二步：[Logic中提到的第二个关键技术点]
[详细分析这个技术点与问题的关系]
RAG证据[引用具体证据]表明[具体技术内容]...

第三步：[Logic中提到的第三个关键技术点]
[深入分析技术实现和参数计算]
具体计算：[公式和数值]...
根据RAG证据[引用具体证据]，[关键参数分析]...

第四步：综合分析
[将前面的技术点整合，分析它们之间的相互作用]
[定量分析和计算结果]...

推理结束。通过按照Logic的技术路径深入分析，我得出了[具体结论]。
</think>

<answer>
[基于Logic和Think的自然回答，800-1500字]

[直接回答问题，然后展开详细的技术分析]
[包含具体的技术细节、参数、公式、设计方法]
[分析设计权衡、优化策略、实际应用考虑]
[给出具体的数值计算、性能指标、实现方案]
[讨论相关的工艺限制、环境因素、系统集成问题]
[总结核心技术优势和解决方案的重要意义]
</answer>

要求:
1. Logic必须简洁精炼，50-100字，紧贴问题核心
2. Think必须严格按照Logic的技术路径进行详细分析
3. Answer要自然流畅，像正常专家回复一样
4. 三个部分必须逻辑一致，形成完整的思维链
5. 充分利用知识图谱节点和RAG证据
6. 包含具体的技术细节、公式、计算过程
"""
        
        return prompt
    
    def _format_knowledge_graph_info(self, subgraph: Dict[str, Any]) -> str:
        """Format knowledge graph information for prompt."""
        nodes = subgraph.get('nodes', [])
        
        # Categorize nodes
        basic_concepts = []
        core_technologies = []
        circuit_applications = []
        
        for node in nodes:
            node_type = node.get('node_type', '')
            node_info = f"{node.get('label', '')}: {node.get('summary', '')[:100]}..."
            
            if node_type == 'basic_concept':
                basic_concepts.append(node_info)
            elif node_type == 'core_technology':
                core_technologies.append(node_info)
            elif node_type == 'circuit_application':
                circuit_applications.append(node_info)
        
        info_parts = []
        
        if basic_concepts:
            info_parts.append("基础概念节点:")
            for i, concept in enumerate(basic_concepts[:5], 1):
                info_parts.append(f"{i}. {concept}")
        
        if core_technologies:
            info_parts.append("\n核心技术节点:")
            for i, tech in enumerate(core_technologies[:5], 1):
                info_parts.append(f"{i}. {tech}")
        
        if circuit_applications:
            info_parts.append("\n电路应用节点:")
            for i, app in enumerate(circuit_applications[:3], 1):
                info_parts.append(f"{i}. {app}")
        
        return '\n'.join(info_parts)
    
    def _format_rag_evidence(self, evidence_package: Dict[str, Any]) -> str:
        """Format RAG evidence for prompt."""
        if not evidence_package:
            return "暂无RAG检索证据"
        
        evidence_parts = []
        
        # Format different types of evidence
        for key, value in evidence_package.items():
            if isinstance(value, list) and value:
                evidence_parts.append(f"{key}:")
                for item in value[:3]:  # Limit to top 3 items
                    if isinstance(item, dict):
                        content = item.get('content', str(item))[:200]
                        evidence_parts.append(f"- {content}...")
                    else:
                        evidence_parts.append(f"- {str(item)[:200]}...")
        
        return '\n'.join(evidence_parts) if evidence_parts else "暂无RAG检索证据"
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for unified CoT generation."""
        return """你是一位资深的模拟电路设计专家，具有深厚的理论基础和丰富的实践经验。

你的任务是针对具体的电路设计问题，生成完整的思维链分析，包括：
1. Logic: 简洁的逻辑思考（50-100字）
2. Think: 详细的技术分析（800-1200字）
3. Answer: 自然的专家回答（800-1500字）

你必须确保：
- Logic简洁精炼，直击问题核心
- Think严格按照Logic的思路进行深入分析
- Answer自然流畅，体现专家水准
- 三个部分逻辑一致，形成完整思维链
- 充分利用提供的知识图谱和RAG证据
- 包含具体的技术细节、公式、计算过程"""
    
    def _parse_cot_result(self, cot_result: str) -> Dict[str, str]:
        """Parse CoT result into separate components."""
        result = {
            'logic': '',
            'think': '',
            'answer': ''
        }
        
        # Extract logic
        logic_match = re.search(r'<logic>(.*?)</logic>', cot_result, re.DOTALL)
        if logic_match:
            result['logic'] = logic_match.group(1).strip()
        
        # Extract think
        think_match = re.search(r'<think>(.*?)</think>', cot_result, re.DOTALL)
        if think_match:
            result['think'] = think_match.group(1).strip()
        
        # Extract answer
        answer_match = re.search(r'<answer>(.*?)</answer>', cot_result, re.DOTALL)
        if answer_match:
            result['answer'] = answer_match.group(1).strip()
        
        return result
    
    def _validate_cot_components(self, parsed_result: Dict[str, str]) -> Dict[str, Any]:
        """Validate the generated CoT components."""
        validation = {
            'logic_valid': False,
            'think_valid': False,
            'answer_valid': False,
            'overall_valid': False,
            'issues': []
        }
        
        # Validate logic
        logic = parsed_result.get('logic', '')
        if 50 <= len(logic) <= 150:
            validation['logic_valid'] = True
        else:
            validation['issues'].append(f"Logic length ({len(logic)}) not in range 50-150")
        
        # Validate think
        think = parsed_result.get('think', '')
        if 800 <= len(think) <= 1500:
            validation['think_valid'] = True
        else:
            validation['issues'].append(f"Think length ({len(think)}) not in range 800-1500")
        
        # Validate answer
        answer = parsed_result.get('answer', '')
        if 800 <= len(answer) <= 2000:
            validation['answer_valid'] = True
        else:
            validation['issues'].append(f"Answer length ({len(answer)}) not in range 800-2000")
        
        # Overall validation
        validation['overall_valid'] = all([
            validation['logic_valid'],
            validation['think_valid'],
            validation['answer_valid']
        ])
        
        return validation
