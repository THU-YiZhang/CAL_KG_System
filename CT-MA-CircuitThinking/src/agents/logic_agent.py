"""
Logic Agent for CT-MA System.

Analyzes knowledge graph subgraphs and extracts logical reasoning paths.
"""

import time
from typing import Dict, List, Any, Optional

from .base_agent import BaseAgent
from ..utils.config_manager import ConfigManager


class LogicAgent(BaseAgent):
    """Agent responsible for extracting logical reasoning paths from subgraphs."""
    
    def __init__(self, config: ConfigManager):
        """
        Initialize Logic Agent.
        
        Args:
            config: Configuration manager instance
        """
        super().__init__(config, "logic_agent")
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute logic analysis on a subgraph.
        
        Args:
            input_data: Contains 'subgraph' key with subgraph data
            
        Returns:
            Dictionary with 'logic' key containing extracted logic
        """
        start_time = time.time()
        success = False
        
        try:
            question = input_data.get('question', '')
            subgraph = input_data.get('subgraph')

            if not subgraph:
                raise ValueError("No subgraph provided in input data")
            if not question:
                raise ValueError("No question provided in input data")

            self.logger.info(f"Analyzing logic for question about: {subgraph.get('application_label', 'unknown')}")

            # Extract logic from subgraph based on question
            logic_content = await self._extract_logic_from_subgraph(question, subgraph)
            
            # Validate output format
            if not self._validate_output_format(logic_content, ['logic']):
                raise ValueError("Logic output does not contain required <logic> tags")
            
            # Extract the logic content
            extracted_logic = self._extract_tagged_content(logic_content, 'logic')
            
            if not extracted_logic:
                raise ValueError("No logic content extracted")
            
            success = True
            result = {
                'logic': extracted_logic,
                'raw_output': logic_content,
                'agent': self.agent_name,
                'execution_time': time.time() - start_time
            }
            
            self.logger.info(f"Logic analysis completed for {subgraph.get('application_label', 'unknown')}")
            return result
            
        except Exception as e:
            self.logger.error(f"Logic analysis failed: {e}")
            raise
        finally:
            self._log_execution_metrics(start_time, success)
    
    async def _extract_logic_from_subgraph(self, question: str, subgraph: Dict[str, Any]) -> str:
        """
        Extract logical reasoning path from subgraph based on specific question.

        Args:
            question: Specific question to analyze
            subgraph: Subgraph data

        Returns:
            Logic analysis in required format
        """
        # Build analysis prompt
        prompt = self._build_logic_analysis_prompt(question, subgraph)
        
        # Prepare messages
        system_message = self._build_system_message()
        user_message = self._build_user_message(prompt)
        
        messages = [system_message, user_message]
        
        # Call LLM
        response = await self._call_llm(messages)

        # 强制处理：检查响应长度，如果过长则强制生成简短版本
        if len(response) > 200:  # 降低阈值，强制生成简短版本
            self.logger.warning(f"Logic response too long ({len(response)} chars), forcing concise generation")
            # 强制生成简短版本
            concise_logic = await self._force_concise_logic(question, subgraph)
            return f"<logic>\n{concise_logic}\n</logic>"

        # 检查Logic标签内容
        logic_content = self._extract_logic_content(response)
        if len(logic_content) > 150:  # 进一步降低阈值
            self.logger.warning(f"Logic content too long ({len(logic_content)} chars), forcing concise generation")
            # 强制生成简短版本
            concise_logic = await self._force_concise_logic(question, subgraph)
            return f"<logic>\n{concise_logic}\n</logic>"

        return response

    def _extract_logic_content(self, response: str) -> str:
        """提取Logic标签内的内容"""
        import re
        match = re.search(r'<logic>(.*?)</logic>', response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return response.strip()

    async def _force_concise_logic(self, question: str, subgraph: Dict[str, Any]) -> str:
        """强制生成简短的Logic"""
        app_label = subgraph.get('application_label', '未知应用')

        # 提取关键技术节点
        nodes = subgraph.get('nodes', [])
        key_techs = []
        for node in nodes[:5]:  # 只取前5个节点
            if node.get('node_type') in ['core_technology', 'basic_concept']:
                key_techs.append(node.get('label', ''))

        # 构建强制简短的提示
        prompt = f"""问题：{question}

请用一句话（不超过100字）说明解决这个问题的技术思路。

格式：针对[问题核心]，关键技术是[技术1]→[技术2]→[技术3]，解决思路是[简短方案]。

可用技术节点：{', '.join(key_techs[:3])}

要求：严格控制在100字以内，只写一句话！"""

        messages = [
            {"role": "system", "content": "你是电路专家，必须用最简洁的语言回答。"},
            {"role": "user", "content": prompt}
        ]

        response = await self._call_llm(messages)

        # 进一步截断确保简短
        if len(response) > 150:
            response = response[:150] + "..."

        return response.strip()

    def _build_logic_analysis_prompt(self, question: str, subgraph: Dict[str, Any]) -> str:
        """Build prompt for logic analysis based on specific question."""
        app_label = subgraph.get('application_label', '未知应用')
        nodes = subgraph.get('nodes', [])

        # Extract node information by type
        basic_concepts = []
        core_technologies = []
        circuit_applications = []

        for node in nodes:
            node_type = node.get('node_type', '')
            node_info = {
                'label': node.get('label', ''),
                'summary': node.get('summary', '')
            }

            if node_type == 'basic_concept':
                basic_concepts.append(node_info)
            elif node_type == 'core_technology':
                core_technologies.append(node_info)
            elif node_type == 'circuit_application':
                circuit_applications.append(node_info)

        prompt = f"""你是一位资深的模拟电路设计工程师，需要针对具体问题进行逻辑思考。

问题: {question}

相关知识图谱节点信息:

基础概念节点:
"""

        for i, concept in enumerate(basic_concepts, 1):
            prompt += f"{i}. {concept['label']}: {concept['summary'][:100]}...\n"

        prompt += "\n核心技术节点:\n"
        for i, tech in enumerate(core_technologies, 1):
            prompt += f"{i}. {tech['label']}: {tech['summary'][:100]}...\n"

        prompt += "\n电路应用节点:\n"
        for i, app in enumerate(circuit_applications, 1):
            prompt += f"{i}. {app['label']}: {app['summary'][:100]}...\n"

        prompt += f"""

请基于上述问题和知识图谱节点，进行简短的逻辑思考。

**重要要求：必须严格控制在100字以内！**

输出格式:
<logic>
针对这个问题，我需要分析[核心技术问题]。关键技术节点是[节点1]→[节点2]→[节点3]，解决思路是：[简短的技术路径]。
</logic>

**示例格式（严格按照此格式）：**
<logic>
针对CMOS运放稳定性问题，我需要分析输入共模电压变化对系统极点的影响。关键技术节点是差分放大器→尾电流源→频率补偿网络，解决思路是：分析工作区域变化→计算极点迁移→优化补偿参数。
</logic>

**严格要求：**
1. 总字数不超过100字
2. 只写一段话，不要展开
3. 必须紧贴问题核心
4. 指出3个关键节点
5. 给出简洁解决思路"""
        
        return prompt
    
    def _validate_logic_structure(self, logic_content: str) -> bool:
        """
        Validate the structure of extracted logic.

        Args:
            logic_content: Extracted logic content

        Returns:
            True if structure is valid
        """
        # 新的简短格式验证
        if len(logic_content.strip()) < 50:
            self.logger.warning("Logic content too short")
            return False

        if len(logic_content.strip()) > 200:
            self.logger.warning("Logic content too long, should be concise")
            return False

        # 检查是否包含基本要素
        required_keywords = ['需要', '技术', '解决']
        found_keywords = sum(1 for keyword in required_keywords if keyword in logic_content)

        if found_keywords < 2:
            self.logger.warning("Logic content lacks required technical elements")
            return False

        return True
    
    def parse_logic_structure(self, logic_content: str) -> Dict[str, Any]:
        """
        Parse logic content into structured format.

        Args:
            logic_content: Raw logic content

        Returns:
            Structured logic data
        """
        # 新的简短格式解析
        parsed = {
            'content': logic_content.strip(),
            'length': len(logic_content.strip()),
            'is_concise': len(logic_content.strip()) <= 200,
            'key_elements': []
        }

        # 提取关键技术元素
        tech_keywords = ['差分放大器', '电流镜', '频率补偿', '输出级', '共模反馈',
                        'MOSFET', 'CMOS', '跨导', '增益', '带宽', '噪声', '功耗']

        for keyword in tech_keywords:
            if keyword in logic_content:
                parsed['key_elements'].append(keyword)

        return parsed
