"""
Iterative Expert Team for CT-MA System.

Two-model expert team that iteratively improves CoT data until satisfaction.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from openai import AsyncOpenAI

from ..utils.logger import LoggerMixin
from ..utils.config_manager import ConfigManager


class IterativeExpertAgent(LoggerMixin):
    """Individual expert agent for iterative improvement."""
    
    def __init__(self, config: ConfigManager, model_name: str, role: str):
        """
        Initialize Iterative Expert Agent.
        
        Args:
            config: Configuration manager
            model_name: Model to use for this expert
            role: Role of the expert (reviewer or improver)
        """
        self.config = config
        self.model_name = model_name
        self.role = role
        self.client = None
    
    async def initialize(self) -> None:
        """Initialize the expert agent."""
        self.logger.info(f"Initializing {self.role} expert with {self.model_name}")
        
        api_key = self.config.get("models.llm.api_key")
        base_url = self.config.get("models.llm.base_url")
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        self.logger.info(f"{self.role} expert initialized")
    
    async def review_cot(self, cot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Review CoT data and provide detailed feedback.
        
        Args:
            cot_data: CoT data to review
            
        Returns:
            Review result with score and feedback
        """
        prompt = self._build_review_prompt(cot_data)
        
        messages = [
            {"role": "system", "content": self._get_reviewer_system_prompt()},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.2,
                max_tokens=2000
            )
            
            review_content = response.choices[0].message.content
            
            return {
                'role': 'reviewer',
                'model': self.model_name,
                'review': self._parse_review(review_content),
                'raw_output': review_content
            }
            
        except Exception as e:
            self.logger.error(f"Review failed: {e}")
            return {
                'role': 'reviewer',
                'model': self.model_name,
                'error': str(e)
            }
    
    async def improve_cot(self, cot_data: Dict[str, Any], feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Improve CoT data based on feedback.
        
        Args:
            cot_data: Original CoT data
            feedback: Feedback from reviewer
            
        Returns:
            Improved CoT data
        """
        prompt = self._build_improvement_prompt(cot_data, feedback)
        
        messages = [
            {"role": "system", "content": self._get_improver_system_prompt()},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.3,
                max_tokens=3000
            )
            
            improvement_content = response.choices[0].message.content
            
            # Parse improved CoT
            improved_cot = self._parse_improved_cot(improvement_content, cot_data)
            
            return {
                'role': 'improver',
                'model': self.model_name,
                'improved_cot': improved_cot,
                'raw_output': improvement_content
            }
            
        except Exception as e:
            self.logger.error(f"Improvement failed: {e}")
            return {
                'role': 'improver',
                'model': self.model_name,
                'error': str(e)
            }
    
    def _get_reviewer_system_prompt(self) -> str:
        """Get system prompt for reviewer role."""
        return """你是电路设计领域的资深专家评审员，负责评估思维链数据的质量。

评估维度：
1. 逻辑一致性：logic、think、answer三部分是否逻辑连贯
2. 技术准确性：技术内容是否准确、专业
3. 内容完整性：是否包含必要的技术细节和分析
4. 表达清晰度：是否表达清晰、易于理解

评估标准：
- 9-10分：优秀，各方面都表现出色
- 7-8分：良好，大部分方面表现良好，有少量改进空间
- 5-6分：一般，存在明显问题需要改进
- 3-4分：较差，存在严重问题需要大幅改进
- 1-2分：很差，基本不可用

请客观、严格地评估，并提供具体的改进建议。"""
    
    def _get_improver_system_prompt(self) -> str:
        """Get system prompt for improver role."""
        return """你是电路设计领域的专家改进员，负责根据评审反馈改进思维链数据。

改进原则：
1. 保持原有的核心技术逻辑不变
2. 根据反馈意见进行针对性改进
3. 确保logic、think、answer三部分的一致性
4. 提升技术内容的准确性和深度
5. 改善表达的清晰度和专业性

改进要求：
- 对于逻辑问题：重新梳理技术路径，确保因果关系清晰
- 对于技术问题：补充或修正技术细节，确保准确性
- 对于完整性问题：补充缺失的关键信息
- 对于表达问题：优化语言表达，提高可读性

请基于反馈进行精准改进，确保改进后的内容质量显著提升。"""
    
    def _build_review_prompt(self, cot_data: Dict[str, Any]) -> str:
        """Build review prompt."""
        app_name = cot_data.get('source_application', '未知应用')
        logic = cot_data.get('logic', '')
        think = cot_data.get('think', '')
        answer = cot_data.get('answer', '')
        
        return f"""请评估以下电路设计思维链数据的质量：

应用名称: {app_name}

【Logic部分】:
{logic}

【Think部分】:
{think}

【Answer部分】:
{answer}

请按以下格式输出评估结果：

<review>
【总体评分】: [1-10分]
【逻辑一致性评分】: [1-10分]
【技术准确性评分】: [1-10分]
【内容完整性评分】: [1-10分]
【表达清晰度评分】: [1-10分]

【主要问题】:
1. [具体问题描述1]
2. [具体问题描述2]
3. [具体问题描述3]

【改进建议】:
1. [针对Logic部分的具体改进建议]
2. [针对Think部分的具体改进建议]
3. [针对Answer部分的具体改进建议]

【是否满意】: [满意/不满意]
【满意度说明】: [如果不满意，说明主要原因]
</review>"""
    
    def _build_improvement_prompt(self, cot_data: Dict[str, Any], feedback: Dict[str, Any]) -> str:
        """Build improvement prompt."""
        app_name = cot_data.get('source_application', '未知应用')
        logic = cot_data.get('logic', '')
        think = cot_data.get('think', '')
        answer = cot_data.get('answer', '')
        
        review_data = feedback.get('review', {})
        main_issues = review_data.get('main_issues', [])
        improvement_suggestions = review_data.get('improvement_suggestions', [])
        
        return f"""请根据评审反馈改进以下思维链数据：

应用名称: {app_name}

【原始Logic部分】:
{logic}

【原始Think部分】:
{think}

【原始Answer部分】:
{answer}

【评审反馈】:
总体评分: {review_data.get('overall_score', 0)}分

主要问题:
{chr(10).join(f"{i+1}. {issue}" for i, issue in enumerate(main_issues))}

改进建议:
{chr(10).join(f"{i+1}. {suggestion}" for i, suggestion in enumerate(improvement_suggestions))}

请按以下格式输出改进后的内容：

<improved>
【改进后Logic】:
<logic>
[改进后的logic内容，保持原有格式]
</logic>

【改进后Think】:
<think>
[改进后的think内容，保持原有格式]
</think>

【改进后Answer】:
<answer>
[改进后的answer内容，保持原有格式]
</answer>

【改进说明】:
1. [针对主要问题的改进说明1]
2. [针对主要问题的改进说明2]
3. [针对主要问题的改进说明3]
</improved>"""
    
    def _parse_review(self, review_content: str) -> Dict[str, Any]:
        """Parse review content."""
        review = {
            'overall_score': 0,
            'dimension_scores': {},
            'main_issues': [],
            'improvement_suggestions': [],
            'is_satisfied': False,
            'satisfaction_reason': ''
        }
        
        if '<review>' in review_content and '</review>' in review_content:
            content = review_content.split('<review>')[1].split('</review>')[0]
            
            lines = content.strip().split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                
                if '【总体评分】' in line:
                    try:
                        score_text = line.split('】:')[1].strip()
                        import re
                        score_match = re.search(r'(\d+)', score_text)
                        if score_match:
                            review['overall_score'] = int(score_match.group(1))
                    except:
                        pass
                
                elif '【逻辑一致性评分】' in line:
                    try:
                        score_text = line.split('】:')[1].strip()
                        import re
                        score_match = re.search(r'(\d+)', score_text)
                        if score_match:
                            review['dimension_scores']['logic_consistency'] = int(score_match.group(1))
                    except:
                        pass
                
                elif '【主要问题】' in line:
                    current_section = 'issues'
                elif '【改进建议】' in line:
                    current_section = 'suggestions'
                elif '【是否满意】' in line:
                    try:
                        satisfaction = line.split('】:')[1].strip()
                        review['is_satisfied'] = '满意' in satisfaction
                    except:
                        pass
                
                elif current_section and line:
                    if current_section == 'issues' and (line.startswith('1.') or line.startswith('2.') or line.startswith('3.')):
                        review['main_issues'].append(line[2:].strip())
                    elif current_section == 'suggestions' and (line.startswith('1.') or line.startswith('2.') or line.startswith('3.')):
                        review['improvement_suggestions'].append(line[2:].strip())
        
        return review
    
    def _parse_improved_cot(self, improvement_content: str, original_cot: Dict[str, Any]) -> Dict[str, Any]:
        """Parse improved CoT content."""
        improved_cot = original_cot.copy()
        
        if '<improved>' in improvement_content and '</improved>' in improvement_content:
            content = improvement_content.split('<improved>')[1].split('</improved>')[0]
            
            # Extract improved logic
            if '<logic>' in content and '</logic>' in content:
                logic_content = content.split('<logic>')[1].split('</logic>')[0].strip()
                improved_cot['logic'] = logic_content
            
            # Extract improved think
            if '<think>' in content and '</think>' in content:
                think_content = content.split('<think>')[1].split('</think>')[0].strip()
                improved_cot['think'] = think_content
            
            # Extract improved answer
            if '<answer>' in content and '</answer>' in content:
                answer_content = content.split('<answer>')[1].split('</answer>')[0].strip()
                improved_cot['answer'] = answer_content
        
        return improved_cot


class IterativeExpertTeamCoordinator(LoggerMixin):
    """Coordinates iterative expert team for CoT improvement."""
    
    def __init__(self, config: ConfigManager):
        """Initialize iterative expert team coordinator."""
        self.config = config
        self.reviewer = None
        self.improver = None
        
        # Configuration
        self.satisfaction_threshold = config.get('expert_team.satisfaction_threshold', 8.0)
        self.max_iterations = config.get('expert_team.max_iterations', 3)
        
        # Model assignments
        self.reviewer_model = 'DMXAPI-HuoShan-DeepSeek-R1-671B-64k'
        self.improver_model = 'qwen3-235b-a22b'
    
    async def initialize(self) -> None:
        """Initialize expert team."""
        self.logger.info("Initializing iterative expert team...")
        
        self.reviewer = IterativeExpertAgent(self.config, self.reviewer_model, "reviewer")
        self.improver = IterativeExpertAgent(self.config, self.improver_model, "improver")
        
        await self.reviewer.initialize()
        await self.improver.initialize()
        
        self.logger.info("Iterative expert team initialized")
    
    async def improve_until_satisfied(self, cot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Iteratively improve CoT data until expert team is satisfied.
        
        Args:
            cot_data: Original CoT data
            
        Returns:
            Final improved CoT data with improvement history
        """
        app_name = cot_data.get('source_application', 'Unknown')
        self.logger.info(f"Starting iterative improvement for: {app_name}")
        
        current_cot = cot_data.copy()
        improvement_history = []
        
        for iteration in range(self.max_iterations):
            self.logger.info(f"Iteration {iteration + 1}/{self.max_iterations}")
            
            # Step 1: Review current CoT
            review_result = await self.reviewer.review_cot(current_cot)
            
            if 'error' in review_result:
                self.logger.error(f"Review failed in iteration {iteration + 1}")
                break
            
            review_data = review_result.get('review', {})
            overall_score = review_data.get('overall_score', 0)
            is_satisfied = review_data.get('is_satisfied', False)
            
            self.logger.info(f"Review score: {overall_score}/10, Satisfied: {is_satisfied}")
            
            # Record iteration
            iteration_record = {
                'iteration': iteration + 1,
                'review_result': review_result,
                'overall_score': overall_score,
                'is_satisfied': is_satisfied
            }
            
            # Check satisfaction
            if is_satisfied and overall_score >= self.satisfaction_threshold:
                self.logger.info(f"Expert team satisfied after {iteration + 1} iterations")
                iteration_record['final_result'] = 'satisfied'
                improvement_history.append(iteration_record)
                break
            
            # Step 2: Improve CoT based on feedback
            improvement_result = await self.improver.improve_cot(current_cot, review_result)
            
            if 'error' in improvement_result:
                self.logger.error(f"Improvement failed in iteration {iteration + 1}")
                iteration_record['improvement_error'] = improvement_result['error']
                improvement_history.append(iteration_record)
                break
            
            # Update current CoT
            improved_cot = improvement_result.get('improved_cot', current_cot)
            current_cot = improved_cot
            
            iteration_record['improvement_result'] = improvement_result
            iteration_record['improved_cot'] = improved_cot
            improvement_history.append(iteration_record)
            
            self.logger.info(f"Iteration {iteration + 1} completed")
        
        # Final result
        final_review = improvement_history[-1].get('review_result', {}) if improvement_history else {}
        final_score = final_review.get('review', {}).get('overall_score', 0)
        
        return {
            'original_cot': cot_data,
            'final_cot': current_cot,
            'improvement_history': improvement_history,
            'total_iterations': len(improvement_history),
            'final_score': final_score,
            'is_satisfied': final_score >= self.satisfaction_threshold,
            'improvement_timestamp': datetime.now().isoformat()
        }
