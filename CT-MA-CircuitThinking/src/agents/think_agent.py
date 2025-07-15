"""
Think Agent for CT-MA System.

Performs detailed reasoning based on logic analysis and RAG evidence.
"""

import time
from typing import Dict, List, Any, Optional

from .base_agent import BaseAgent
from ..utils.config_manager import ConfigManager


class ThinkAgent(BaseAgent):
    """Agent responsible for detailed reasoning and thinking process."""
    
    def __init__(self, config: ConfigManager):
        """
        Initialize Think Agent.
        
        Args:
            config: Configuration manager instance
        """
        super().__init__(config, "think_agent")
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute detailed thinking process.
        
        Args:
            input_data: Contains 'logic', 'evidence_package', and 'subgraph' keys
            
        Returns:
            Dictionary with 'think' key containing detailed reasoning
        """
        start_time = time.time()
        success = False
        
        try:
            question = input_data.get('question', '')
            logic_content = input_data.get('logic')
            evidence_package = input_data.get('evidence_package', {})
            subgraph = input_data.get('subgraph', {})

            if not logic_content:
                raise ValueError("No logic content provided in input data")
            if not question:
                raise ValueError("No question provided in input data")

            self.logger.info(f"Starting detailed thinking for question about: {subgraph.get('application_label', 'unknown')}")

            # Generate detailed thinking
            think_content = await self._generate_detailed_thinking(
                question, logic_content, evidence_package, subgraph
            )
            
            # Validate output format
            if not self._validate_output_format(think_content, ['think']):
                raise ValueError("Think output does not contain required <think> tags")
            
            # Extract the think content
            extracted_think = self._extract_tagged_content(think_content, 'think')
            
            if not extracted_think:
                raise ValueError("No think content extracted")
            
            success = True
            result = {
                'think': extracted_think,
                'raw_output': think_content,
                'agent': self.agent_name,
                'execution_time': time.time() - start_time,
                'rag_references_count': self._count_rag_references(extracted_think)
            }
            
            self.logger.info(f"Detailed thinking completed for {subgraph.get('application_label', 'unknown')}")
            return result
            
        except Exception as e:
            self.logger.error(f"Detailed thinking failed: {e}")
            raise
        finally:
            self._log_execution_metrics(start_time, success)
    
    async def _generate_detailed_thinking(
        self,
        question: str,
        logic_content: str,
        evidence_package: Dict[str, Any],
        subgraph: Dict[str, Any]
    ) -> str:
        """
        Generate detailed thinking process based on specific question.

        Args:
            question: Specific question to analyze
            logic_content: Logic analysis from Logic Agent
            evidence_package: RAG evidence package
            subgraph: Original subgraph data

        Returns:
            Detailed thinking in required format
        """
        # Build thinking prompt
        prompt = self._build_thinking_prompt(question, logic_content, evidence_package, subgraph)
        
        # Prepare messages
        system_message = self._build_system_message()
        user_message = self._build_user_message(prompt)
        
        messages = [system_message, user_message]
        
        # Call LLM with longer context
        response = await self._call_llm(
            messages, 
            max_tokens=self.config.get("models.llm.max_tokens", 4000)
        )
        
        return response
    
    def _build_thinking_prompt(
        self,
        question: str,
        logic_content: str,
        evidence_package: Dict[str, Any],
        subgraph: Dict[str, Any]
    ) -> str:
        """Build prompt for detailed thinking based on specific question."""
        app_label = subgraph.get('application_label', '未知应用')

        # Format evidence for prompt
        formatted_evidence = self._format_evidence_for_prompt(evidence_package)

        prompt = f"""你是一位资深的模拟电路设计专家，需要基于Logic的思路进行详细的技术分析。

问题: {question}

Logic思路:
{logic_content}

检索到的相关知识证据:
{formatted_evidence}

请严格按照Logic中提出的技术路径，结合RAG检索到的知识，进行详细的技术分析。

输出格式要求:
<think>
推理开始。基于Logic的分析思路，我将深入研究这个问题。

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

要求:
1. 严格按照Logic中的技术路径进行分析
2. 每个步骤都要紧贴问题的具体要求
3. 包含具体的技术细节、参数、公式、计算
4. 充分利用RAG检索到的技术知识
5. 体现深度的工程分析过程
3. 推理过程要体现专家的思维方式
4. 要展现从问题分析到解决方案的完整思考过程
5. 每个RAG证据引用都要具体明确，格式为"RAG证据[具体内容]"
"""
        
        return prompt
    
    def _format_evidence_for_prompt(self, evidence_package: Dict[str, Any]) -> str:
        """Format evidence package for prompt."""
        formatted_lines = []
        
        # Format knowledge evidence
        knowledge_evidence = evidence_package.get('knowledge_evidence', {})
        for concept, definitions in knowledge_evidence.items():
            if definitions:
                formatted_lines.append(f"【{concept}定义】")
                for i, def_item in enumerate(definitions[:2], 1):
                    content = def_item['content'][:200] + "..." if len(def_item['content']) > 200 else def_item['content']
                    formatted_lines.append(f"定义证据{i}: {content}")
        
        # Format formula evidence
        formula_evidence = evidence_package.get('formula_evidence', {})
        for concept, formulas in formula_evidence.items():
            if formulas:
                formatted_lines.append(f"【{concept}公式】")
                for i, formula_item in enumerate(formulas[:2], 1):
                    content = formula_item['content'][:150] + "..." if len(formula_item['content']) > 150 else formula_item['content']
                    formatted_lines.append(f"公式证据{i}: {content}")
        
        # Format technical evidence
        technical_evidence = evidence_package.get('technical_evidence', {})
        for concept, tech_details in technical_evidence.items():
            if tech_details:
                formatted_lines.append(f"【{concept}技术细节】")
                for i, tech_item in enumerate(tech_details[:1], 1):
                    content = tech_item['content'][:200] + "..." if len(tech_item['content']) > 200 else tech_item['content']
                    formatted_lines.append(f"技术证据{i}: {content}")
        
        # Format example evidence
        example_evidence = evidence_package.get('example_evidence', {})
        for concept, examples in example_evidence.items():
            if examples:
                formatted_lines.append(f"【{concept}应用示例】")
                for i, example_item in enumerate(examples[:1], 1):
                    content = example_item['content'][:150] + "..." if len(example_item['content']) > 150 else example_item['content']
                    formatted_lines.append(f"示例证据{i}: {content}")
        
        if not formatted_lines:
            return "暂无相关知识证据"
        
        return "\n".join(formatted_lines)
    
    def _count_rag_references(self, think_content: str) -> int:
        """Count RAG evidence references in thinking content."""
        import re
        
        # Count patterns like "RAG证据[...]"
        pattern = r'RAG证据\[.*?\]'
        matches = re.findall(pattern, think_content)
        
        return len(matches)
    
    def _validate_thinking_quality(self, think_content: str) -> Dict[str, Any]:
        """
        Validate the quality of thinking content.
        
        Args:
            think_content: Generated thinking content
            
        Returns:
            Quality assessment
        """
        quality_metrics = {
            'has_reasoning_steps': False,
            'has_rag_references': False,
            'has_conclusion': False,
            'sufficient_length': False,
            'step_count': 0,
            'rag_reference_count': 0
        }
        
        # Check for reasoning steps
        step_patterns = ['第一步', '第二步', '第三步', '第四步']
        step_count = sum(1 for pattern in step_patterns if pattern in think_content)
        quality_metrics['step_count'] = step_count
        quality_metrics['has_reasoning_steps'] = step_count >= 3
        
        # Check for RAG references
        rag_count = self._count_rag_references(think_content)
        quality_metrics['rag_reference_count'] = rag_count
        quality_metrics['has_rag_references'] = rag_count >= 3
        
        # Check for conclusion
        conclusion_patterns = ['推理结束', '通过层层递进', '解决了设计核心矛盾']
        quality_metrics['has_conclusion'] = any(pattern in think_content for pattern in conclusion_patterns)
        
        # Check length
        min_length = self.config.get("quality.min_think_length", 500)
        quality_metrics['sufficient_length'] = len(think_content) >= min_length
        
        return quality_metrics
    
    def extract_reasoning_steps(self, think_content: str) -> List[Dict[str, str]]:
        """
        Extract individual reasoning steps from thinking content.
        
        Args:
            think_content: Thinking content
            
        Returns:
            List of reasoning steps
        """
        steps = []
        lines = think_content.split('\n')
        current_step = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            
            # Check if this is a step header
            if any(pattern in line for pattern in ['第一步', '第二步', '第三步', '第四步']):
                # Save previous step
                if current_step and current_content:
                    steps.append({
                        'step': current_step,
                        'content': '\n'.join(current_content)
                    })
                
                # Start new step
                current_step = line
                current_content = []
            elif current_step and line:
                current_content.append(line)
        
        # Save last step
        if current_step and current_content:
            steps.append({
                'step': current_step,
                'content': '\n'.join(current_content)
            })
        
        return steps
