"""
Quality Checker for CT-MA System.

Assesses the quality of generated CoT data across multiple dimensions.
"""

import re
from typing import Dict, List, Any, Optional, Tuple

from ..utils.logger import LoggerMixin
from ..utils.config_manager import ConfigManager


class QualityChecker(LoggerMixin):
    """Assesses quality of CoT data across multiple dimensions."""
    
    def __init__(self, config: ConfigManager):
        """
        Initialize Quality Checker.
        
        Args:
            config: Configuration manager instance
        """
        self.config = config
        
        # Quality thresholds
        self.min_quality_score = config.get("quality.min_quality_score", 0.7)
        
        # Technical terms for domain relevance
        self.circuit_terms = [
            '电路', '电压', '电流', '阻抗', '增益', '频率', '功率', '器件',
            '晶体管', '运放', '放大器', '滤波器', '振荡器', '模拟', '数字',
            '信号', '噪声', '带宽', '失真', '反馈', '稳定性', '线性',
            'MOS', 'BJT', 'CMOS', 'PN结', '二极管', '电容', '电感', '电阻'
        ]
        
        # Quality indicators
        self.quality_indicators = {
            'logic_indicators': ['因果关系', '技术路径', '逻辑连接', '必然性'],
            'reasoning_indicators': ['分析', '推理', '证实', '解释', '显示'],
            'technical_indicators': ['原理', '机制', '方法', '技术', '设计'],
            'conclusion_indicators': ['解决', '实现', '达到', '满足', '优化']
        }
    
    def check_quality(self, cot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive quality assessment of CoT data.
        
        Args:
            cot_data: CoT data to assess
            
        Returns:
            Quality assessment results
        """
        quality_result = {
            'overall_score': 0.0,
            'dimension_scores': {},
            'quality_issues': [],
            'strengths': [],
            'recommendations': []
        }
        
        try:
            # Assess different quality dimensions
            dimensions = {
                'logical_coherence': self._assess_logical_coherence(cot_data),
                'technical_accuracy': self._assess_technical_accuracy(cot_data),
                'reasoning_depth': self._assess_reasoning_depth(cot_data),
                'domain_relevance': self._assess_domain_relevance(cot_data),
                'completeness': self._assess_completeness(cot_data),
                'clarity': self._assess_clarity(cot_data)
            }
            
            quality_result['dimension_scores'] = dimensions
            
            # Calculate overall score (weighted average)
            weights = {
                'logical_coherence': 0.25,
                'technical_accuracy': 0.20,
                'reasoning_depth': 0.20,
                'domain_relevance': 0.15,
                'completeness': 0.10,
                'clarity': 0.10
            }
            
            overall_score = sum(
                dimensions[dim]['score'] * weights[dim] 
                for dim in dimensions
            )
            quality_result['overall_score'] = overall_score
            
            # Collect issues and strengths
            for dim_name, dim_result in dimensions.items():
                quality_result['quality_issues'].extend(dim_result.get('issues', []))
                quality_result['strengths'].extend(dim_result.get('strengths', []))
            
            # Generate recommendations
            quality_result['recommendations'] = self._generate_recommendations(dimensions)
            
        except Exception as e:
            quality_result['quality_issues'].append(f"Quality assessment error: {str(e)}")
            self.logger.error(f"Quality check failed: {e}")
        
        return quality_result
    
    def _assess_logical_coherence(self, cot_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess logical coherence across sections."""
        result = {'score': 0.0, 'issues': [], 'strengths': []}
        
        logic_content = cot_data.get('logic', '')
        think_content = cot_data.get('think', '')
        answer_content = cot_data.get('answer', '')
        
        score_components = []
        
        # Check logic-think consistency
        if logic_content and think_content:
            consistency_score = self._check_logic_think_consistency(logic_content, think_content)
            score_components.append(consistency_score)
            
            if consistency_score > 0.8:
                result['strengths'].append("Strong consistency between logic and thinking")
            elif consistency_score < 0.5:
                result['issues'].append("Poor consistency between logic and thinking sections")
        
        # Check think-answer consistency
        if think_content and answer_content:
            conclusion_score = self._check_think_answer_consistency(think_content, answer_content)
            score_components.append(conclusion_score)
            
            if conclusion_score > 0.8:
                result['strengths'].append("Answer well-supported by reasoning")
            elif conclusion_score < 0.5:
                result['issues'].append("Answer not well-supported by reasoning")
        
        # Check causal chain coherence
        if logic_content:
            causal_score = self._check_causal_coherence(logic_content)
            score_components.append(causal_score)
            
            if causal_score > 0.7:
                result['strengths'].append("Clear causal relationships")
            elif causal_score < 0.4:
                result['issues'].append("Unclear causal relationships")
        
        result['score'] = sum(score_components) / len(score_components) if score_components else 0.0
        return result
    
    def _assess_technical_accuracy(self, cot_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess technical accuracy and correctness."""
        result = {'score': 0.0, 'issues': [], 'strengths': []}
        
        all_content = ' '.join([
            cot_data.get('logic', ''),
            cot_data.get('think', ''),
            cot_data.get('answer', '')
        ])
        
        score_components = []
        
        # Check for technical terminology usage
        tech_term_score = self._assess_technical_terminology(all_content)
        score_components.append(tech_term_score)
        
        if tech_term_score > 0.7:
            result['strengths'].append("Good use of technical terminology")
        elif tech_term_score < 0.3:
            result['issues'].append("Insufficient technical terminology")
        
        # Check for formula/equation references
        formula_score = self._assess_formula_usage(all_content)
        score_components.append(formula_score)
        
        if formula_score > 0.5:
            result['strengths'].append("Includes relevant formulas/equations")
        
        # Check for specific circuit concepts
        concept_score = self._assess_circuit_concepts(all_content)
        score_components.append(concept_score)
        
        if concept_score > 0.6:
            result['strengths'].append("Demonstrates circuit design knowledge")
        elif concept_score < 0.3:
            result['issues'].append("Limited circuit design concepts")
        
        result['score'] = sum(score_components) / len(score_components) if score_components else 0.0
        return result
    
    def _assess_reasoning_depth(self, cot_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess depth and quality of reasoning."""
        result = {'score': 0.0, 'issues': [], 'strengths': []}
        
        think_content = cot_data.get('think', '')
        
        if not think_content:
            result['issues'].append("No thinking content to assess")
            return result
        
        score_components = []
        
        # Check reasoning step count and depth
        step_score = self._assess_reasoning_steps(think_content)
        score_components.append(step_score)
        
        if step_score > 0.8:
            result['strengths'].append("Comprehensive reasoning steps")
        elif step_score < 0.4:
            result['issues'].append("Insufficient reasoning steps")
        
        # Check evidence usage
        evidence_score = self._assess_evidence_usage(think_content)
        score_components.append(evidence_score)
        
        if evidence_score > 0.7:
            result['strengths'].append("Good use of evidence and references")
        elif evidence_score < 0.3:
            result['issues'].append("Limited evidence and references")
        
        # Check reasoning complexity
        complexity_score = self._assess_reasoning_complexity(think_content)
        score_components.append(complexity_score)
        
        if complexity_score > 0.6:
            result['strengths'].append("Demonstrates complex reasoning")
        elif complexity_score < 0.3:
            result['issues'].append("Reasoning too simplistic")
        
        result['score'] = sum(score_components) / len(score_components) if score_components else 0.0
        return result
    
    def _assess_domain_relevance(self, cot_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess relevance to circuit domain."""
        result = {'score': 0.0, 'issues': [], 'strengths': []}
        
        all_content = ' '.join([
            cot_data.get('logic', ''),
            cot_data.get('think', ''),
            cot_data.get('answer', '')
        ])
        
        # Count circuit-related terms
        circuit_term_count = sum(1 for term in self.circuit_terms if term in all_content)
        total_terms = len(self.circuit_terms)
        
        # Calculate relevance score
        relevance_score = min(1.0, circuit_term_count / (total_terms * 0.3))  # 30% coverage is max
        
        if relevance_score > 0.7:
            result['strengths'].append("Highly relevant to circuit domain")
        elif relevance_score < 0.3:
            result['issues'].append("Limited relevance to circuit domain")
        
        # Check for application context
        app_context_score = self._assess_application_context(cot_data)
        
        # Combine scores
        result['score'] = (relevance_score + app_context_score) / 2
        return result
    
    def _assess_completeness(self, cot_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess completeness of the CoT data."""
        result = {'score': 0.0, 'issues': [], 'strengths': []}
        
        completeness_factors = []
        
        # Check section completeness
        required_sections = ['logic', 'think', 'answer']
        present_sections = sum(1 for section in required_sections if cot_data.get(section))
        section_score = present_sections / len(required_sections)
        completeness_factors.append(section_score)
        
        # Check logic completeness
        logic_content = cot_data.get('logic', '')
        if logic_content:
            logic_elements = ['目标应用', '关键瓶颈', '支撑路径', '因果链']
            present_elements = sum(1 for element in logic_elements if f'【{element}】' in logic_content)
            logic_completeness = present_elements / len(logic_elements)
            completeness_factors.append(logic_completeness)
            
            if logic_completeness == 1.0:
                result['strengths'].append("Complete logic structure")
            elif logic_completeness < 0.75:
                result['issues'].append("Incomplete logic structure")
        
        # Check thinking completeness
        think_content = cot_data.get('think', '')
        if think_content:
            think_completeness = self._assess_thinking_completeness(think_content)
            completeness_factors.append(think_completeness)
            
            if think_completeness > 0.8:
                result['strengths'].append("Comprehensive thinking process")
            elif think_completeness < 0.5:
                result['issues'].append("Incomplete thinking process")
        
        result['score'] = sum(completeness_factors) / len(completeness_factors) if completeness_factors else 0.0
        return result
    
    def _assess_clarity(self, cot_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess clarity and readability."""
        result = {'score': 0.0, 'issues': [], 'strengths': []}
        
        clarity_scores = []
        
        for section_name in ['logic', 'think', 'answer']:
            content = cot_data.get(section_name, '')
            if content:
                section_clarity = self._assess_section_clarity(content)
                clarity_scores.append(section_clarity)
        
        if clarity_scores:
            avg_clarity = sum(clarity_scores) / len(clarity_scores)
            result['score'] = avg_clarity
            
            if avg_clarity > 0.7:
                result['strengths'].append("Clear and well-structured content")
            elif avg_clarity < 0.4:
                result['issues'].append("Content lacks clarity")
        
        return result
    
    def _check_logic_think_consistency(self, logic_content: str, think_content: str) -> float:
        """Check consistency between logic and think sections."""
        # Extract key terms from logic
        logic_terms = self._extract_key_terms(logic_content)
        
        # Check how many logic terms appear in thinking
        mentioned_terms = sum(1 for term in logic_terms if term in think_content)
        
        if not logic_terms:
            return 0.5  # Neutral score if no terms to check
        
        return mentioned_terms / len(logic_terms)
    
    def _check_think_answer_consistency(self, think_content: str, answer_content: str) -> float:
        """Check consistency between think and answer sections."""
        # Look for conclusion keywords in both sections
        conclusion_keywords = ['解决', '实现', '优势', '方法', '技术']
        
        think_conclusions = [kw for kw in conclusion_keywords if kw in think_content]
        answer_conclusions = [kw for kw in conclusion_keywords if kw in answer_content]
        
        if not think_conclusions:
            return 0.5
        
        overlap = len(set(think_conclusions) & set(answer_conclusions))
        return overlap / len(think_conclusions)
    
    def _check_causal_coherence(self, logic_content: str) -> float:
        """Check causal coherence in logic section."""
        causal_indicators = ['因果', '导致', '由于', '因此', '所以', '从而', '实现']
        
        causal_count = sum(1 for indicator in causal_indicators if indicator in logic_content)
        
        # Normalize based on content length
        content_length = len(logic_content)
        if content_length == 0:
            return 0.0
        
        causal_density = causal_count / (content_length / 100)  # Per 100 characters
        return min(1.0, causal_density)
    
    def _assess_technical_terminology(self, content: str) -> float:
        """Assess use of technical terminology."""
        tech_count = sum(1 for term in self.circuit_terms if term in content)
        
        # Normalize by content length and expected density
        content_length = len(content)
        if content_length == 0:
            return 0.0
        
        expected_density = 0.02  # 2% of content should be technical terms
        actual_density = tech_count / content_length
        
        return min(1.0, actual_density / expected_density)
    
    def _assess_formula_usage(self, content: str) -> float:
        """Assess usage of formulas and equations."""
        formula_indicators = ['=', '公式', '方程', '计算', 'V_', 'I_', 'R_', 'C_', 'L_']
        
        formula_count = sum(1 for indicator in formula_indicators if indicator in content)
        
        # Score based on presence and frequency
        if formula_count == 0:
            return 0.0
        elif formula_count <= 2:
            return 0.5
        else:
            return min(1.0, formula_count / 5)
    
    def _assess_circuit_concepts(self, content: str) -> float:
        """Assess circuit-specific concepts."""
        circuit_concepts = [
            '放大', '滤波', '振荡', '反馈', '稳定', '线性', '非线性',
            '频率响应', '增益', '带宽', '噪声', '失真', '功耗'
        ]
        
        concept_count = sum(1 for concept in circuit_concepts if concept in content)
        
        return min(1.0, concept_count / len(circuit_concepts))
    
    def _assess_reasoning_steps(self, think_content: str) -> float:
        """Assess reasoning steps in thinking section."""
        step_patterns = ['第一步', '第二步', '第三步', '第四步', '第五步']
        
        step_count = sum(1 for pattern in step_patterns if pattern in think_content)
        
        # Score based on number of steps
        if step_count >= 4:
            return 1.0
        elif step_count >= 3:
            return 0.8
        elif step_count >= 2:
            return 0.5
        elif step_count >= 1:
            return 0.3
        else:
            return 0.0
    
    def _assess_evidence_usage(self, think_content: str) -> float:
        """Assess usage of evidence and references."""
        evidence_patterns = [r'RAG证据\[.*?\]', '证实', '显示', '表明', '说明']
        
        evidence_count = 0
        for pattern in evidence_patterns:
            if pattern.startswith('RAG'):
                evidence_count += len(re.findall(pattern, think_content))
            else:
                evidence_count += think_content.count(pattern)
        
        # Score based on evidence density
        return min(1.0, evidence_count / 5)
    
    def _assess_reasoning_complexity(self, think_content: str) -> float:
        """Assess complexity of reasoning."""
        complexity_indicators = [
            '分析', '推理', '推导', '证明', '验证', '比较', '权衡',
            '考虑', '评估', '判断', '选择', '优化'
        ]
        
        complexity_count = sum(1 for indicator in complexity_indicators if indicator in think_content)
        
        return min(1.0, complexity_count / len(complexity_indicators))
    
    def _assess_application_context(self, cot_data: Dict[str, Any]) -> float:
        """Assess application context relevance."""
        app_label = cot_data.get('source_application', '')
        
        if not app_label:
            return 0.5
        
        all_content = ' '.join([
            cot_data.get('logic', ''),
            cot_data.get('think', ''),
            cot_data.get('answer', '')
        ])
        
        # Check if application is mentioned in content
        app_mentions = all_content.count(app_label)
        
        return min(1.0, app_mentions / 3)  # Expect at least 3 mentions
    
    def _assess_thinking_completeness(self, think_content: str) -> float:
        """Assess completeness of thinking process."""
        required_elements = [
            '推理开始', '第一步', '第二步', '第三步', '推理结束'
        ]
        
        present_elements = sum(1 for element in required_elements if element in think_content)
        
        return present_elements / len(required_elements)
    
    def _assess_section_clarity(self, content: str) -> float:
        """Assess clarity of a content section."""
        # Simple heuristics for clarity
        sentences = content.split('。')
        
        if not sentences:
            return 0.0
        
        # Average sentence length (shorter is clearer)
        avg_sentence_length = sum(len(s) for s in sentences) / len(sentences)
        length_score = max(0.0, 1.0 - (avg_sentence_length - 50) / 100)
        
        # Structure indicators
        structure_indicators = ['首先', '其次', '然后', '最后', '因此', '所以']
        structure_count = sum(1 for indicator in structure_indicators if indicator in content)
        structure_score = min(1.0, structure_count / 3)
        
        return (length_score + structure_score) / 2
    
    def _extract_key_terms(self, content: str) -> List[str]:
        """Extract key terms from content."""
        # Simple extraction of terms in brackets or technical terms
        terms = []
        
        # Extract terms in brackets
        bracket_terms = re.findall(r'\[([^\]]+)\]', content)
        terms.extend(bracket_terms)
        
        # Extract circuit terms
        for term in self.circuit_terms:
            if term in content:
                terms.append(term)
        
        return list(set(terms))  # Remove duplicates
    
    def _generate_recommendations(self, dimensions: Dict[str, Dict[str, Any]]) -> List[str]:
        """Generate improvement recommendations based on dimension scores."""
        recommendations = []
        
        for dim_name, dim_result in dimensions.items():
            score = dim_result['score']
            
            if score < 0.5:
                if dim_name == 'logical_coherence':
                    recommendations.append("Improve logical consistency between sections")
                elif dim_name == 'technical_accuracy':
                    recommendations.append("Include more technical terminology and concepts")
                elif dim_name == 'reasoning_depth':
                    recommendations.append("Provide more detailed reasoning steps")
                elif dim_name == 'domain_relevance':
                    recommendations.append("Focus more on circuit-specific concepts")
                elif dim_name == 'completeness':
                    recommendations.append("Ensure all required sections are complete")
                elif dim_name == 'clarity':
                    recommendations.append("Improve clarity and structure of content")
        
        return recommendations
