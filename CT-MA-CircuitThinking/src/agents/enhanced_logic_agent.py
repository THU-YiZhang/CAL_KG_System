"""
Enhanced Logic Agent for CT-MA System.

Provides improved logic analysis with readable text descriptions.
"""

import time
from typing import Dict, List, Any

from .base_agent import BaseAgent


class EnhancedLogicAgent(BaseAgent):
    """Enhanced Logic Agent with readable text description support."""
    
    def __init__(self, config, agent_name: str = "enhanced_logic_agent"):
        """
        Initialize Enhanced Logic Agent.
        
        Args:
            config: Configuration manager instance
            agent_name: Name of the agent
        """
        super().__init__(config, agent_name)
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute enhanced logic analysis.
        
        Args:
            input_data: Contains 'subgraph' and 'readable_description'
            
        Returns:
            Dictionary with logic analysis result
        """
        start_time = time.time()
        success = False
        
        try:
            subgraph = input_data.get('subgraph')
            readable_description = input_data.get('readable_description', '')
            
            if not subgraph:
                raise ValueError("No subgraph provided in input data")
            
            app_label = subgraph.get('application_label', 'unknown')
            self.logger.info(f"Enhanced logic analysis for: {app_label}")
            
            # Generate enhanced logic analysis
            logic_content = await self._generate_enhanced_logic(subgraph, readable_description)
            
            # Validate and extract logic
            if not self._validate_output_format(logic_content, ['logic']):
                raise ValueError("Logic output does not contain required <logic> tags")
            
            extracted_logic = self._extract_tagged_content(logic_content, 'logic')
            
            if not extracted_logic:
                raise ValueError("No logic content extracted")
            
            success = True
            result = {
                'success': True,
                'logic': extracted_logic,
                'raw_output': logic_content,
                'agent': self.agent_name,
                'execution_time': time.time() - start_time
            }

            self.logger.info(f"Enhanced logic analysis completed for {app_label}")
            return result

        except Exception as e:
            self.logger.error(f"Enhanced logic analysis failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'agent': self.agent_name,
                'execution_time': time.time() - start_time
            }
        finally:
            self._log_execution_metrics(start_time, success)
    
    async def _generate_enhanced_logic(self, subgraph: Dict[str, Any], readable_description: str) -> str:
        """Generate enhanced logic analysis with readable description."""
        
        # Build enhanced prompt
        prompt = self._build_enhanced_logic_prompt(subgraph, readable_description)
        
        # Prepare messages
        system_message = self._build_enhanced_system_message()
        user_message = self._build_user_message(prompt)
        
        messages = [system_message, user_message]
        
        # Call LLM
        response = await self._call_llm(messages)
        
        return response
    
    def _build_enhanced_system_message(self) -> Dict[str, str]:
        """Build enhanced system message for logic analysis."""
        system_prompt = """你是电路设计逻辑整理专家，专门将知识图谱转化为逻辑思维过程。

你的核心任务是：
将复杂的知识图谱转化为一段自然的逻辑思维过程，就像工程师在解决问题时的内心独白。

输出格式要求：
- 必须使用<logic></logic>标签包围全部内容
- 采用第一人称"我"的思维独白形式
- 体现真实的工程师思考过程

内容结构：
1. 问题认知：我需要解决什么问题
2. 逻辑整理：我首先需要整理我的逻辑
3. 技术分析：我需要先思考直接关联的核心技术有哪些
4. 概念梳理：这些核心技术涉及哪些基础概念
5. 扩展思考：同时其他关联的核心技术有哪些
6. 路径规划：从基础概念到核心技术再到最终应用的完整路径

语言风格：
- 自然流畅的思维过程
- 体现工程师的专业思考
- 逻辑清晰但不生硬
- 像真实的内心独白"""

        return {"role": "system", "content": system_prompt}
    
    def _build_enhanced_logic_prompt(self, subgraph: Dict[str, Any], readable_description: str) -> str:
        """Build enhanced logic analysis prompt."""

        app_label = subgraph.get('application_label', '未知应用')

        # Use readable description if provided, otherwise generate basic info
        if readable_description:
            graph_description = readable_description
        else:
            graph_description = self._generate_basic_description(subgraph)

        prompt = f"""请基于以下知识图谱信息，转化为工程师的逻辑思维过程：

目标应用: {app_label}

知识图谱结构分析:
{graph_description}

请将上述知识图谱转化为工程师解决问题时的逻辑思维过程：

<logic>
我需要解决{app_label}的设计问题。面对这个挑战，我首先需要整理我的逻辑。

我需要先思考直接关联的核心技术有哪些。从知识图谱分析来看，[基于图谱中的直接关联技术，列出2-3个最重要的核心技术，说明它们为什么是关键的]。

这些核心技术涉及哪些基础概念呢？[分析支撑这些核心技术的基础理论概念，解释概念与技术的关系]。

同时，我还需要考虑其他关联的核心技术。[分析图谱中的间接关联技术，说明它们如何与主要技术路径形成协同]。

从技术演进的角度来看，[描述从基础概念→核心技术→应用实现的完整逻辑路径，强调每一步的必然性和合理性]。

因此，我的技术选择逻辑是：[总结整个技术路径的合理性，说明为什么这样的技术组合能够有效解决目标问题]。
</logic>

要求：
1. 采用第一人称"我"的思维独白形式
2. 体现真实工程师的思考过程
3. 基于实际的知识图谱内容，不要编造
4. 逻辑流畅自然，像内心独白
5. 重点体现技术选择的逻辑性和必然性"""

        return prompt
    
    def _generate_basic_description(self, subgraph: Dict[str, Any]) -> str:
        """Generate basic description if readable description not provided."""
        nodes = subgraph.get('nodes', [])
        
        # Categorize nodes
        basic_concepts = [n for n in nodes if n.get('node_type') == 'basic_concept']
        core_technologies = [n for n in nodes if n.get('node_type') == 'core_technology']
        applications = [n for n in nodes if n.get('node_type') == 'circuit_application']
        
        description = "基于知识图谱的技术结构分析：\n\n"
        
        if basic_concepts:
            description += "【基础概念层】:\n"
            for concept in basic_concepts[:3]:
                description += f"- {concept.get('label', '未知概念')}: {concept.get('summary', '基础概念')[:50]}...\n"
            description += "\n"
        
        if core_technologies:
            description += "【核心技术层】:\n"
            for tech in core_technologies[:4]:
                description += f"- {tech.get('label', '未知技术')}: {tech.get('summary', '核心技术')[:50]}...\n"
            description += "\n"
        
        if len(applications) > 1:
            description += "【应用层】:\n"
            for app in applications[:2]:
                description += f"- {app.get('label', '未知应用')}: {app.get('summary', '电路应用')[:50]}...\n"
        
        description += "\n需要分析这些技术层次之间的逻辑关系和演进路径。"
        
        return description
    
    def _build_user_message(self, content: str) -> Dict[str, str]:
        """Build user message."""
        return {"role": "user", "content": content}
    
    def _validate_output_format(self, content: str, required_tags: List[str]) -> bool:
        """Validate that output contains required tags."""
        for tag in required_tags:
            if f"<{tag}>" not in content or f"</{tag}>" not in content:
                return False
        return True
    
    def _extract_tagged_content(self, content: str, tag: str) -> str:
        """Extract content between specified tags."""
        start_tag = f"<{tag}>"
        end_tag = f"</{tag}>"
        
        start_idx = content.find(start_tag)
        end_idx = content.find(end_tag)
        
        if start_idx == -1 or end_idx == -1:
            return ""
        
        start_idx += len(start_tag)
        return content[start_idx:end_idx].strip()
    
    def _log_execution_metrics(self, start_time: float, success: bool) -> None:
        """Log execution metrics."""
        execution_time = time.time() - start_time
        status = "success" if success else "failed"
        self.logger.info(f"{self.agent_name} execution completed in {execution_time:.2f}s, status: {status}")
