"""
Multi-Expert CoT Improvement Team for CT-MA System.

Uses multiple expert models to review and improve generated CoT data.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from openai import AsyncOpenAI

from ..utils.logger import LoggerMixin
from ..utils.config_manager import ConfigManager


class ExpertAgent(LoggerMixin):
    """Individual expert agent for CoT improvement."""
    
    def __init__(self, config: ConfigManager, expert_type: str, model_name: str):
        """
        Initialize Expert Agent.
        
        Args:
            config: Configuration manager
            expert_type: Type of expert (logic, technical, clarity, completeness)
            model_name: Model to use for this expert
        """
        self.config = config
        self.expert_type = expert_type
        self.model_name = model_name
        self.client = None
        
        # Expert-specific configurations
        self.expertise_focus = {
            'logic': '逻辑一致性和推理连贯性',
            'technical': '技术准确性和专业深度',
            'clarity': '表达清晰度和可读性',
            'completeness': '内容完整性和结构完善性',
            'expert_a': '逻辑一致性和技术准确性',
            'expert_b': '表达清晰度和内容完整性'
        }
    
    async def initialize(self) -> None:
        """Initialize the expert agent."""
        self.logger.info(f"Initializing {self.expert_type} expert with {self.model_name}")
        
        # Initialize client based on model
        if "HuoShan" in self.model_name or "qwen" in self.model_name:
            # Use same API configuration as DeepSeek
            api_key = self.config.get("models.llm.api_key")
            base_url = self.config.get("models.llm.base_url")
        else:
            api_key = self.config.get("models.llm.api_key")
            base_url = self.config.get("models.llm.base_url")
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        self.logger.info(f"{self.expert_type} expert initialized")
    
    async def review_cot(self, cot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Review CoT data from expert perspective.
        
        Args:
            cot_data: Original CoT data
            
        Returns:
            Expert review with suggestions
        """
        prompt = self._build_review_prompt(cot_data)
        
        messages = [
            {"role": "system", "content": self._get_expert_system_prompt()},
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
                'expert_type': self.expert_type,
                'model': self.model_name,
                'review': self._parse_review(review_content),
                'raw_output': review_content
            }
            
        except Exception as e:
            self.logger.error(f"{self.expert_type} expert review failed: {e}")
            return {
                'expert_type': self.expert_type,
                'model': self.model_name,
                'error': str(e)
            }
    
    def _get_expert_system_prompt(self) -> str:
        """Get system prompt for this expert."""
        base_prompt = f"你是电路设计领域的资深专家，专门负责{self.expertise_focus[self.expert_type]}的评估和改进。"
        
        if self.expert_type == 'logic':
            return base_prompt + """
你的任务是评估思维链的逻辑一致性：
1. 检查logic、think、answer三部分之间的逻辑连贯性
2. 识别推理过程中的逻辑跳跃或矛盾
3. 评估因果关系的合理性
4. 提出逻辑改进建议
"""
        elif self.expert_type == 'technical':
            return base_prompt + """
你的任务是评估技术内容的准确性：
1. 检查技术术语使用的准确性
2. 验证公式和参数的正确性
3. 评估技术深度和专业水准
4. 识别技术错误或不准确之处
"""
        elif self.expert_type == 'clarity':
            return base_prompt + """
你的任务是评估表达的清晰度：
1. 检查语言表达是否清晰易懂
2. 评估结构组织是否合理
3. 识别表达模糊或歧义的地方
4. 提出表达改进建议
"""
        elif self.expert_type == 'completeness':
            return base_prompt + """
你的任务是评估内容的完整性：
1. 检查是否遗漏关键信息
2. 评估各部分内容的充实程度
3. 识别需要补充的技术细节
4. 提出内容完善建议
"""
        elif self.expert_type == 'expert_a':
            return base_prompt + """
你的任务是从逻辑一致性和技术准确性角度评估思维链：
1. 检查logic、think、answer三部分之间的逻辑连贯性
2. 验证技术术语、公式和参数的准确性
3. 识别推理过程中的逻辑跳跃或技术错误
4. 评估技术深度和专业水准
5. 提出逻辑和技术改进建议
"""
        elif self.expert_type == 'expert_b':
            return base_prompt + """
你的任务是从表达清晰度和内容完整性角度评估思维链：
1. 检查语言表达是否清晰易懂
2. 评估结构组织是否合理
3. 检查是否遗漏关键信息
4. 识别表达模糊或需要补充的技术细节
5. 提出表达和内容完善建议
"""

        return base_prompt
    
    def _build_review_prompt(self, cot_data: Dict[str, Any]) -> str:
        """Build review prompt for the expert."""
        app_name = cot_data.get('source_application', '未知应用')
        logic = cot_data.get('logic', '')
        think = cot_data.get('think', '')
        answer = cot_data.get('answer', '')
        
        prompt = f"""请从{self.expertise_focus[self.expert_type]}的角度，评估以下电路设计思维链：

应用名称: {app_name}

【Logic部分】:
{logic}

【Think部分】:
{think}

【Answer部分】:
{answer}

请按以下格式输出评估结果：

<review>
【总体评分】: [1-10分，10分最高]
【主要问题】:
1. [问题1描述]
2. [问题2描述]
3. [问题3描述]

【改进建议】:
1. [具体改进建议1]
2. [具体改进建议2]
3. [具体改进建议3]

【需要重新检索的内容】:
- [需要补充的技术点1]
- [需要补充的技术点2]

【修改优先级】:
- 高优先级: [最重要的修改]
- 中优先级: [次要修改]
- 低优先级: [可选修改]
</review>"""
        
        return prompt
    
    def _parse_review(self, review_content: str) -> Dict[str, Any]:
        """Parse expert review content."""
        review = {
            'overall_score': 0,
            'main_issues': [],
            'improvement_suggestions': [],
            'retrieval_needs': [],
            'priority_modifications': {}
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
                        # Extract number from score text
                        import re
                        score_match = re.search(r'(\d+)', score_text)
                        if score_match:
                            review['overall_score'] = int(score_match.group(1))
                    except:
                        pass
                
                elif '【主要问题】' in line:
                    current_section = 'issues'
                elif '【改进建议】' in line:
                    current_section = 'suggestions'
                elif '【需要重新检索的内容】' in line:
                    current_section = 'retrieval'
                elif '【修改优先级】' in line:
                    current_section = 'priority'
                
                elif current_section and line:
                    if current_section == 'issues' and (line.startswith('1.') or line.startswith('2.') or line.startswith('3.')):
                        review['main_issues'].append(line[2:].strip())
                    elif current_section == 'suggestions' and (line.startswith('1.') or line.startswith('2.') or line.startswith('3.')):
                        review['improvement_suggestions'].append(line[2:].strip())
                    elif current_section == 'retrieval' and line.startswith('-'):
                        review['retrieval_needs'].append(line[1:].strip())
                    elif current_section == 'priority':
                        if '高优先级:' in line:
                            review['priority_modifications']['high'] = line.split('高优先级:')[1].strip()
                        elif '中优先级:' in line:
                            review['priority_modifications']['medium'] = line.split('中优先级:')[1].strip()
                        elif '低优先级:' in line:
                            review['priority_modifications']['low'] = line.split('低优先级:')[1].strip()
        
        return review


class ExpertTeamCoordinator(LoggerMixin):
    """Coordinates two-model expert team for iterative CoT improvement."""

    def __init__(self, config: ConfigManager):
        """Initialize expert team coordinator."""
        self.config = config
        self.expert_a = None  # HuoShan-DeepSeek-R1
        self.expert_b = None  # Qwen3
        self.experts = {}  # Dictionary to store experts

        # Two-model expert team
        self.model_a = 'DMXAPI-HuoShan-DeepSeek-R1-671B-64k'
        self.model_b = 'qwen3-235b-a22b'

        # Expert models mapping
        self.expert_models = {
            'expert_a': self.model_a,
            'expert_b': self.model_b
        }

        # Quality thresholds
        self.satisfaction_threshold = config.get('expert_team.satisfaction_threshold', 8.0)
        self.max_iterations = config.get('expert_team.max_iterations', 3)
    
    async def initialize(self) -> None:
        """Initialize all expert agents."""
        self.logger.info("Initializing expert team...")
        
        for expert_type, model_name in self.expert_models.items():
            expert = ExpertAgent(self.config, expert_type, model_name)
            await expert.initialize()
            self.experts[expert_type] = expert
        
        self.logger.info("Expert team initialized")

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute expert team review and improvement.

        Args:
            input_data: Contains 'question', 'logic', 'think', 'answer', 'question_id'

        Returns:
            Dictionary with improvements and statistics
        """
        # Convert input format to cot_data format
        cot_data = {
            'source_application': 'CMOS运算放大器',  # Default application
            'question': input_data.get('question', ''),
            'logic': input_data.get('logic', ''),
            'think': input_data.get('think', ''),
            'answer': input_data.get('answer', ''),
            'question_id': input_data.get('question_id', 'unknown')
        }

        # Call the actual review method
        return await self.review_and_improve_cot(cot_data)

    async def review_and_improve_cot(self, cot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Review and improve CoT data using expert team.
        
        Args:
            cot_data: Original CoT data
            
        Returns:
            Comprehensive review and improvement plan
        """
        app_name = cot_data.get('source_application', 'Unknown')
        self.logger.info(f"Expert team reviewing: {app_name}")

        # Initialize experts if not already done
        if not self.experts:
            await self.initialize()

        # Run all experts in parallel
        review_tasks = []
        for expert_type, expert in self.experts.items():
            task = expert.review_cot(cot_data)
            review_tasks.append(task)
        
        expert_reviews = await asyncio.gather(*review_tasks, return_exceptions=True)
        
        # Compile expert reviews
        compiled_reviews = {}
        for i, (expert_type, review) in enumerate(zip(self.experts.keys(), expert_reviews)):
            if isinstance(review, Exception):
                self.logger.error(f"Expert {expert_type} failed: {review}")
                continue
            compiled_reviews[expert_type] = review
        
        # Generate improvement plan
        improvement_plan = self._generate_improvement_plan(compiled_reviews, cot_data)
        
        return {
            'original_cot': cot_data,
            'expert_reviews': compiled_reviews,
            'improvement_plan': improvement_plan,
            'review_timestamp': datetime.now().isoformat()
        }
    
    def _generate_improvement_plan(
        self, 
        expert_reviews: Dict[str, Any], 
        original_cot: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive improvement plan from expert reviews."""
        
        # Aggregate scores
        scores = []
        all_issues = []
        all_suggestions = []
        all_retrieval_needs = []
        priority_items = {'high': [], 'medium': [], 'low': []}
        
        for expert_type, review in expert_reviews.items():
            if 'error' in review:
                continue
            
            review_data = review.get('review', {})
            
            # Collect scores
            if review_data.get('overall_score', 0) > 0:
                scores.append(review_data['overall_score'])
            
            # Collect issues with expert attribution
            for issue in review_data.get('main_issues', []):
                all_issues.append(f"[{expert_type}] {issue}")
            
            # Collect suggestions
            for suggestion in review_data.get('improvement_suggestions', []):
                all_suggestions.append(f"[{expert_type}] {suggestion}")
            
            # Collect retrieval needs
            all_retrieval_needs.extend(review_data.get('retrieval_needs', []))
            
            # Collect priority items
            priorities = review_data.get('priority_modifications', {})
            for level in ['high', 'medium', 'low']:
                if level in priorities and priorities[level]:
                    priority_items[level].append(f"[{expert_type}] {priorities[level]}")
        
        # Calculate overall assessment
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # Determine improvement strategy
        if avg_score >= 8:
            strategy = "minor_refinement"
        elif avg_score >= 6:
            strategy = "moderate_improvement"
        else:
            strategy = "major_revision"
        
        improvement_plan = {
            'overall_score': avg_score,
            'improvement_strategy': strategy,
            'critical_issues': all_issues[:5],  # Top 5 issues
            'improvement_suggestions': all_suggestions[:8],  # Top 8 suggestions
            'retrieval_requirements': list(set(all_retrieval_needs)),  # Unique retrieval needs
            'priority_modifications': priority_items,
            'recommended_actions': self._generate_recommended_actions(strategy, priority_items)
        }
        
        return improvement_plan
    
    def _generate_recommended_actions(
        self, 
        strategy: str, 
        priority_items: Dict[str, List[str]]
    ) -> List[str]:
        """Generate recommended actions based on improvement strategy."""
        actions = []
        
        if strategy == "major_revision":
            actions.extend([
                "重新设计logic部分的技术路径",
                "补充think部分的推理细节",
                "重新检索相关技术文献",
                "重新生成answer部分"
            ])
        elif strategy == "moderate_improvement":
            actions.extend([
                "优化logic部分的表达",
                "增强think部分的证据支撑",
                "完善answer部分的技术细节"
            ])
        else:  # minor_refinement
            actions.extend([
                "微调表达方式",
                "补充少量技术细节",
                "优化格式结构"
            ])
        
        # Add high priority items
        for item in priority_items.get('high', [])[:3]:
            actions.append(f"高优先级: {item}")
        
        return actions
    
    async def batch_review_cot_data(self, cot_batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Review multiple CoT data items."""
        self.logger.info(f"Expert team reviewing {len(cot_batch)} CoT items")
        
        results = []
        for i, cot_data in enumerate(cot_batch, 1):
            try:
                app_name = cot_data.get('source_application', f'Item_{i}')
                self.logger.info(f"Reviewing {i}/{len(cot_batch)}: {app_name}")
                
                review_result = await self.review_and_improve_cot(cot_data)
                results.append(review_result)
                
            except Exception as e:
                self.logger.error(f"Failed to review CoT item {i}: {e}")
                results.append({
                    'original_cot': cot_data,
                    'error': str(e),
                    'review_timestamp': datetime.now().isoformat()
                })
        
        return results
    
    def get_team_statistics(self, review_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about team review results."""
        total_items = len(review_results)
        successful_reviews = [r for r in review_results if 'error' not in r]
        
        if not successful_reviews:
            return {'total_items': total_items, 'successful_reviews': 0}
        
        # Calculate average scores
        scores = []
        strategies = {'minor_refinement': 0, 'moderate_improvement': 0, 'major_revision': 0}
        
        for result in successful_reviews:
            plan = result.get('improvement_plan', {})
            score = plan.get('overall_score', 0)
            if score > 0:
                scores.append(score)
            
            strategy = plan.get('improvement_strategy', '')
            if strategy in strategies:
                strategies[strategy] += 1
        
        avg_score = sum(scores) / len(scores) if scores else 0
        
        return {
            'total_items': total_items,
            'successful_reviews': len(successful_reviews),
            'average_score': avg_score,
            'improvement_strategies': strategies,
            'review_success_rate': len(successful_reviews) / total_items
        }
