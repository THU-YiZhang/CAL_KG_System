"""
Answer Agent for CT-MA System.

Synthesizes final answers based on detailed thinking process.
"""

import time
from typing import Dict, List, Any, Optional

from .base_agent import BaseAgent
from ..utils.config_manager import ConfigManager


class AnswerAgent(BaseAgent):
    """Agent responsible for synthesizing final answers."""
    
    def __init__(self, config: ConfigManager):
        """
        Initialize Answer Agent.
        
        Args:
            config: Configuration manager instance
        """
        super().__init__(config, "answer_agent")
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute answer synthesis.
        
        Args:
            input_data: Contains 'think', 'logic', and 'subgraph' keys
            
        Returns:
            Dictionary with 'answer' key containing final answer
        """
        start_time = time.time()
        success = False
        
        try:
            question = input_data.get('question', '')
            think_content = input_data.get('think')
            logic_content = input_data.get('logic')
            subgraph = input_data.get('subgraph', {})

            if not think_content:
                raise ValueError("No think content provided in input data")

            if not question:
                raise ValueError("No question provided in input data")

            self.logger.info(f"Synthesizing answer for question about: {subgraph.get('application_label', 'unknown')}")

            # Generate final answer
            answer_content = await self._synthesize_final_answer(
                question, think_content, logic_content, subgraph
            )
            
            # Validate output format
            if not self._validate_output_format(answer_content, ['answer']):
                raise ValueError("Answer output does not contain required <answer> tags")
            
            # Extract the answer content
            extracted_answer = self._extract_tagged_content(answer_content, 'answer')
            
            if not extracted_answer:
                raise ValueError("No answer content extracted")
            
            success = True
            result = {
                'success': True,
                'answer': extracted_answer,
                'raw_output': answer_content,
                'agent': self.agent_name,
                'execution_time': time.time() - start_time
            }

            self.logger.info(f"Answer synthesis completed for {subgraph.get('application_label', 'unknown')}")
            return result

        except Exception as e:
            self.logger.error(f"Answer synthesis failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'agent': self.agent_name,
                'execution_time': time.time() - start_time
            }
        finally:
            self._log_execution_metrics(start_time, success)
    
    async def _synthesize_final_answer(
        self,
        question: str,
        think_content: str,
        logic_content: str,
        subgraph: Dict[str, Any]
    ) -> str:
        """
        Synthesize final answer from thinking process.

        Args:
            question: Original question being answered
            think_content: Detailed thinking from Think Agent
            logic_content: Logic analysis from Logic Agent
            subgraph: Original subgraph data

        Returns:
            Final answer in required format
        """
        # Build synthesis prompt
        prompt = self._build_synthesis_prompt(question, think_content, logic_content, subgraph)
        
        # Prepare messages
        system_message = self._build_system_message()
        user_message = self._build_user_message(prompt)
        
        messages = [system_message, user_message]
        
        # Call LLM
        response = await self._call_llm(messages)
        
        return response
    
    def _build_synthesis_prompt(
        self,
        question: str,
        think_content: str,
        logic_content: str,
        subgraph: Dict[str, Any]
    ) -> str:
        """Build prompt for answer synthesis."""
        app_label = subgraph.get('application_label', '未知应用')

        # Extract key insights from thinking process
        key_insights = self._extract_key_insights(think_content)

        prompt = f"""你是一位资深的模拟电路设计专家，需要基于详细的思考过程回答用户的技术问题。

用户问题:
{question}

你的逻辑思考:
{logic_content}

你的详细分析:
{think_content}

关键技术洞察:
{key_insights}

请基于上述思考过程，像一个正常的大模型一样，自然、全面、深入地回答用户的问题。

输出格式要求:
<answer>
[像正常大模型回复一样，自然地回答问题，不需要固定的格式结构]

[直接回答问题，然后展开详细的技术分析]
[包含具体的技术细节、参数、公式、设计方法]
[分析设计权衡、优化策略、实际应用考虑]
[给出具体的数值计算、性能指标、实现方案]
[讨论相关的工艺限制、环境因素、系统集成问题]
[总结核心技术优势和解决方案的重要意义]
</answer>

要求:
1. 回答要自然流畅，像正常的技术专家回复一样
2. 不要使用固定的格式标题（如"核心原理分析"等）
3. 内容要详细深入，包含丰富的技术细节
4. 要有具体的参数、公式、计算过程
5. 分析要全面，涵盖原理、实现、优化、应用等方面
6. 语言要专业准确，体现工程师的技术深度
7. 答案长度控制在800-1500字，确保内容充实
8. 必须基于思考过程中的分析给出具体的技术方案
"""
        
        return prompt
    
    def _extract_key_insights(self, think_content: str) -> str:
        """Extract key insights from thinking content."""
        insights = []
        
        # Look for key phrases that indicate insights
        insight_patterns = [
            '关键洞察',
            '核心原理',
            '技术优势',
            '解决方案',
            '设计要点',
            '核心矛盾'
        ]
        
        lines = think_content.split('\n')
        for line in lines:
            line = line.strip()
            for pattern in insight_patterns:
                if pattern in line:
                    insights.append(line)
                    break
        
        # Also extract conclusion if present
        if '推理结束' in think_content:
            conclusion_start = think_content.find('推理结束')
            conclusion_text = think_content[conclusion_start:conclusion_start+200]
            insights.append(conclusion_text)
        
        return '\n'.join(insights[:5])  # Top 5 insights
    
    def _validate_answer_quality(self, answer_content: str) -> Dict[str, Any]:
        """
        Validate the quality of answer content.
        
        Args:
            answer_content: Generated answer content
            
        Returns:
            Quality assessment
        """
        quality_metrics = {
            'has_solution': False,
            'has_principle': False,
            'has_technical_details': False,
            'has_design_tradeoffs': False,
            'has_practical_considerations': False,
            'appropriate_length': False,
            'technical_depth': False
        }

        # Check for solution description
        solution_indicators = ['解决方案', '技术方案', '设计方法', '实现策略']
        quality_metrics['has_solution'] = any(indicator in answer_content for indicator in solution_indicators)

        # Check for principle explanation
        principle_indicators = ['核心原理', '物理机制', '数学模型', '工作原理']
        quality_metrics['has_principle'] = any(indicator in answer_content for indicator in principle_indicators)

        # Check for technical details
        detail_indicators = ['技术细节', '参数设计', '性能指标', '实现方法', '设计考虑']
        quality_metrics['has_technical_details'] = any(indicator in answer_content for indicator in detail_indicators)

        # Check for design tradeoffs
        tradeoff_indicators = ['权衡', '优化', '平衡', '折中', '取舍']
        quality_metrics['has_design_tradeoffs'] = any(indicator in answer_content for indicator in tradeoff_indicators)

        # Check for practical considerations
        practical_indicators = ['实际应用', '工艺限制', '环境因素', '系统集成', '实现难点']
        quality_metrics['has_practical_considerations'] = any(indicator in answer_content for indicator in practical_indicators)

        # Check length (updated for detailed answers)
        min_length = self.config.get("quality.min_answer_length", 800)
        max_length = self.config.get("quality.max_answer_length", 2000)
        length = len(answer_content)
        quality_metrics['appropriate_length'] = min_length <= length <= max_length

        # Check technical depth (expanded technical terms)
        technical_terms = ['电路', '电压', '电流', '阻抗', '增益', '频率', '功率', '器件', '晶体管', '运放',
                          'CMOS', '差分', '共模', '带宽', '噪声', '失真', '线性度', '稳定性', '补偿', '反馈']
        tech_count = sum(1 for term in technical_terms if term in answer_content)
        quality_metrics['technical_depth'] = tech_count >= 2
        
        return quality_metrics
    
    def extract_answer_components(self, answer_content: str) -> Dict[str, str]:
        """
        Extract components from answer content.
        
        Args:
            answer_content: Answer content
            
        Returns:
            Dictionary of answer components
        """
        components = {
            'core_solution': '',
            'principle': '',
            'key_technology': '',
            'advantages': '',
            'final_effect': '',
            'core_contradiction': ''
        }
        
        # Simple pattern matching for common structures
        if '原理在于：' in answer_content:
            parts = answer_content.split('原理在于：')
            if len(parts) >= 2:
                components['core_solution'] = parts[0].strip()
                remaining = parts[1]
                
                if '。' in remaining:
                    components['principle'] = remaining.split('。')[0].strip()
        
        # Extract key technology mentions
        tech_patterns = ['能', '通过', '采用', '使用']
        for pattern in tech_patterns:
            if pattern in answer_content:
                # Extract sentence containing the pattern
                sentences = answer_content.split('。')
                for sentence in sentences:
                    if pattern in sentence:
                        components['key_technology'] = sentence.strip()
                        break
        
        # Extract advantages
        advantage_patterns = ['优势', '优点', '能够', '实现']
        for pattern in advantage_patterns:
            if pattern in answer_content:
                sentences = answer_content.split('。')
                for sentence in sentences:
                    if pattern in sentence:
                        components['advantages'] = sentence.strip()
                        break
        
        return components
    
    def generate_answer_summary(self, answer_content: str) -> Dict[str, Any]:
        """
        Generate summary of the answer.
        
        Args:
            answer_content: Answer content
            
        Returns:
            Answer summary
        """
        components = self.extract_answer_components(answer_content)
        quality = self._validate_answer_quality(answer_content)
        
        return {
            'length': len(answer_content),
            'components': components,
            'quality_metrics': quality,
            'technical_terms_count': self._count_technical_terms(answer_content),
            'readability_score': self._calculate_readability_score(answer_content)
        }
    
    def _count_technical_terms(self, text: str) -> int:
        """Count technical terms in text."""
        technical_terms = [
            '电路', '电压', '电流', '阻抗', '增益', '频率', '功率', 
            '器件', '晶体管', '运放', '放大器', '滤波器', '振荡器',
            '模拟', '数字', '信号', '噪声', '带宽', '失真'
        ]
        
        return sum(1 for term in technical_terms if term in text)
    
    def _calculate_readability_score(self, text: str) -> float:
        """Calculate simple readability score."""
        if not text:
            return 0.0
        
        # Simple metrics: sentence length, character variety
        sentences = text.split('。')
        avg_sentence_length = len(text) / len(sentences) if sentences else 0
        
        # Normalize to 0-1 scale
        readability = min(1.0, max(0.0, (50 - avg_sentence_length) / 50))
        
        return readability
