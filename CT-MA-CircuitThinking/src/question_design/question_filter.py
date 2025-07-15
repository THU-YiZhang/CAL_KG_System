#!/usr/bin/env python3
"""
Question Filter and Selector
问题筛选和选择器
"""

import random
from typing import List, Dict, Any
from ..utils.logger import get_logger


class QuestionFilterAndSelector:
    """问题筛选和选择器"""
    
    def __init__(self, config):
        """初始化筛选器"""
        self.config = config
        self.logger = get_logger(__name__)
        
        # 质量评分阈值
        self.quality_threshold = config.get('question_filter.quality_threshold', 3.5)
        self.complexity_threshold = config.get('question_filter.complexity_threshold', 3.0)
        
    def filter_and_select(self, questions: List[Dict[str, Any]], target_count: int = 3) -> List[Dict[str, Any]]:
        """
        筛选和选择高质量问题
        
        Args:
            questions: 问题列表
            target_count: 目标问题数量
            
        Returns:
            筛选后的问题列表
        """
        self.logger.info(f"Filtering {len(questions)} questions to select {target_count}")
        
        # 1. 质量筛选
        quality_filtered = []
        for q in questions:
            quality_score = q.get('quality_score', 0)
            complexity_score = q.get('complexity_score', 0)
            
            if quality_score >= self.quality_threshold and complexity_score >= self.complexity_threshold:
                quality_filtered.append(q)
        
        self.logger.info(f"After quality filtering: {len(quality_filtered)} questions")
        
        # 2. 如果筛选后的问题不够，降低阈值
        if len(quality_filtered) < target_count:
            self.logger.warning(f"Not enough high-quality questions, lowering thresholds")
            quality_filtered = []
            for q in questions:
                quality_score = q.get('quality_score', 0)
                complexity_score = q.get('complexity_score', 0)
                
                if quality_score >= 2.5 and complexity_score >= 2.0:
                    quality_filtered.append(q)
        
        # 3. 如果还是不够，直接使用所有问题
        if len(quality_filtered) < target_count:
            quality_filtered = questions
        
        # 4. 按综合评分排序
        def calculate_composite_score(q):
            quality = q.get('quality_score', 0)
            complexity = q.get('complexity_score', 0)
            relevance = q.get('relevance_score', 0)
            return (quality * 0.4 + complexity * 0.3 + relevance * 0.3)
        
        quality_filtered.sort(key=calculate_composite_score, reverse=True)
        
        # 5. 选择前N个
        selected = quality_filtered[:target_count]
        
        # 6. 如果还是不够，随机补充
        if len(selected) < target_count:
            remaining = [q for q in questions if q not in selected]
            random.shuffle(remaining)
            needed = target_count - len(selected)
            selected.extend(remaining[:needed])
        
        self.logger.info(f"Selected {len(selected)} questions")
        
        # 7. 为选中的问题添加选择原因
        for i, q in enumerate(selected):
            q['selection_rank'] = i + 1
            q['selection_reason'] = self._get_selection_reason(q, calculate_composite_score(q))
        
        return selected
    
    def _get_selection_reason(self, question: Dict[str, Any], composite_score: float) -> str:
        """获取选择原因"""
        quality = question.get('quality_score', 0)
        complexity = question.get('complexity_score', 0)
        relevance = question.get('relevance_score', 0)
        
        reasons = []
        
        if quality >= 4.0:
            reasons.append("高质量问题")
        elif quality >= 3.5:
            reasons.append("良好质量")
        
        if complexity >= 4.0:
            reasons.append("高复杂度")
        elif complexity >= 3.0:
            reasons.append("适中复杂度")
        
        if relevance >= 4.0:
            reasons.append("高相关性")
        elif relevance >= 3.0:
            reasons.append("良好相关性")
        
        if composite_score >= 4.0:
            reasons.append("综合评分优秀")
        elif composite_score >= 3.5:
            reasons.append("综合评分良好")
        
        return "、".join(reasons) if reasons else "基础筛选"
    
    def get_filter_statistics(self, original_questions: List[Dict[str, Any]], 
                            filtered_questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取筛选统计信息"""
        
        def get_score_stats(questions, score_key):
            scores = [q.get(score_key, 0) for q in questions]
            if not scores:
                return {"avg": 0, "min": 0, "max": 0}
            return {
                "avg": sum(scores) / len(scores),
                "min": min(scores),
                "max": max(scores)
            }
        
        return {
            "original_count": len(original_questions),
            "filtered_count": len(filtered_questions),
            "filter_rate": len(filtered_questions) / len(original_questions) if original_questions else 0,
            "original_quality": get_score_stats(original_questions, 'quality_score'),
            "filtered_quality": get_score_stats(filtered_questions, 'quality_score'),
            "original_complexity": get_score_stats(original_questions, 'complexity_score'),
            "filtered_complexity": get_score_stats(filtered_questions, 'complexity_score'),
            "original_relevance": get_score_stats(original_questions, 'relevance_score'),
            "filtered_relevance": get_score_stats(filtered_questions, 'relevance_score')
        }
