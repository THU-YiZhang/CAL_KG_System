"""
模拟电路问题类型分类体系

基于模拟电路领域知识建立详细的问题类型分类，确保问题生成的多样性
"""

from typing import Dict, List, Any, Optional
from enum import Enum
import random


class QuestionType(Enum):
    """问题类型枚举"""
    CIRCUIT_ANALYSIS = "circuit_analysis"           # 电路分析类
    DESIGN_OPTIMIZATION = "design_optimization"     # 设计优化类
    PARAMETER_CALCULATION = "parameter_calculation" # 参数计算类
    PERFORMANCE_COMPARISON = "performance_comparison" # 性能比较类
    TROUBLESHOOTING = "troubleshooting"             # 故障诊断类
    APPLICATION_DESIGN = "application_design"       # 应用设计类


class DifficultyLevel(Enum):
    """难度等级枚举"""
    EASY = "easy"       # 简单（基础概念）
    MEDIUM = "medium"   # 中等（技术应用）
    HARD = "hard"       # 困难（综合设计）


class AnalogCircuitQuestionTypes:
    """模拟电路问题类型分类体系"""
    
    def __init__(self):
        """初始化问题类型分类体系"""
        self.question_templates = self._build_question_templates()
        self.difficulty_indicators = self._build_difficulty_indicators()
        
    def _build_question_templates(self) -> Dict[str, Dict[str, List[str]]]:
        """构建问题模板库"""
        return {
            QuestionType.CIRCUIT_ANALYSIS.value: {
                "easy": [
                    "分析{circuit_name}的基本工作原理，说明各个器件的作用。",
                    "解释{circuit_name}中{key_component}的功能和重要性。",
                    "描述{circuit_name}的信号流向和基本特性。",
                    "分析{circuit_name}的直流工作点设置方法。"
                ],
                "medium": [
                    "分析{circuit_name}的小信号等效电路，推导其增益表达式。",
                    "研究{circuit_name}的频率响应特性，分析主要极点和零点。",
                    "分析{circuit_name}的噪声性能，计算输入参考噪声。",
                    "分析{circuit_name}的非线性失真机制和改善方法。"
                ],
                "hard": [
                    "深入分析{circuit_name}在{specific_condition}条件下的工作机制，包括{technical_aspects}的相互作用。",
                    "分析{circuit_name}的稳定性问题，推导稳定性判据并提出补偿方案。",
                    "研究{circuit_name}在极端工艺角下的性能变化，分析敏感参数。"
                ]
            },
            
            QuestionType.DESIGN_OPTIMIZATION.value: {
                "easy": [
                    "设计一个{circuit_name}，满足基本的{performance_spec}要求。",
                    "优化{circuit_name}的功耗，在保证性能的前提下降低静态电流。",
                    "改进{circuit_name}的版图设计，提高匹配精度。"
                ],
                "medium": [
                    "设计{circuit_name}以满足{performance_specs}，分析关键设计权衡。",
                    "优化{circuit_name}的{key_parameter}，分析优化策略和限制因素。",
                    "设计{circuit_name}的偏置电路，确保温度稳定性和工艺鲁棒性。"
                ],
                "hard": [
                    "设计一个{advanced_spec}的{circuit_name}，要求同时优化{multiple_objectives}，分析设计权衡和实现方案。",
                    "针对{specific_application}应用，设计{circuit_name}并优化{complex_requirements}。",
                    "设计{circuit_name}以满足{stringent_specs}，分析极限性能的实现方法。"
                ]
            },
            
            QuestionType.PARAMETER_CALCULATION.value: {
                "easy": [
                    "计算{circuit_name}的直流增益和输入输出阻抗。",
                    "计算{circuit_name}的功耗和效率。",
                    "计算{circuit_name}的带宽和增益带宽积。"
                ],
                "medium": [
                    "计算{circuit_name}的{specific_parameter}，考虑{design_constraints}的影响。",
                    "推导{circuit_name}的传递函数，计算极点频率和相位裕度。",
                    "计算{circuit_name}的噪声系数和动态范围。"
                ],
                "hard": [
                    "计算{circuit_name}在{complex_conditions}下的{multiple_parameters}，分析参数间的相互影响。",
                    "推导{circuit_name}的高阶效应模型，计算非理想因素的影响。",
                    "计算{circuit_name}的蒙特卡洛分析结果，评估良率和设计裕量。"
                ]
            },
            
            QuestionType.PERFORMANCE_COMPARISON.value: {
                "easy": [
                    "比较{circuit_a}和{circuit_b}的基本性能差异。",
                    "分析{topology_a}和{topology_b}拓扑的优缺点。",
                    "比较不同偏置方案对{circuit_name}性能的影响。"
                ],
                "medium": [
                    "比较{circuit_a}和{circuit_b}在{specific_metrics}方面的性能，分析适用场景。",
                    "对比{technology_a}和{technology_b}工艺实现{circuit_name}的性能差异。",
                    "比较不同补偿方案对{circuit_name}稳定性和带宽的影响。"
                ],
                "hard": [
                    "全面比较{multiple_circuits}在{comprehensive_metrics}方面的性能，分析最优选择策略。",
                    "比较{advanced_techniques}对{circuit_name}性能提升的效果，分析实现复杂度。",
                    "对比{circuit_name}在{different_applications}中的性能表现，分析优化方向。"
                ]
            },
            
            QuestionType.TROUBLESHOOTING.value: {
                "easy": [
                    "诊断{circuit_name}输出异常的可能原因。",
                    "分析{circuit_name}功耗过大的原因和解决方法。",
                    "排查{circuit_name}振荡问题的根本原因。"
                ],
                "medium": [
                    "诊断{circuit_name}出现{specific_symptom}的原因，提出系统性排查方法。",
                    "分析{circuit_name}在{test_condition}下失效的机理，设计验证方案。",
                    "排查{circuit_name}的{performance_degradation}问题，分析根本原因。"
                ],
                "hard": [
                    "诊断{complex_circuit}在{challenging_conditions}下的{multiple_issues}，建立故障树分析。",
                    "分析{circuit_name}的{intermittent_failure}问题，设计可靠性测试方案。",
                    "排查{system_level}中{circuit_name}的{interaction_issues}，分析系统级影响。"
                ]
            },
            
            QuestionType.APPLICATION_DESIGN.value: {
                "easy": [
                    "为{application_scenario}设计合适的{circuit_name}方案。",
                    "设计{circuit_name}满足{basic_application_requirements}。",
                    "选择合适的{circuit_name}拓扑用于{simple_application}。"
                ],
                "medium": [
                    "为{specific_application}设计{circuit_name}，满足{detailed_requirements}。",
                    "设计{circuit_name}用于{application_context}，分析关键设计考虑。",
                    "针对{application_constraints}，设计优化的{circuit_name}方案。"
                ],
                "hard": [
                    "为{complex_application}设计完整的{circuit_name}系统，包括{system_components}的协同设计。",
                    "设计{circuit_name}满足{stringent_application_specs}，分析极限性能实现。",
                    "针对{emerging_application}，创新设计{circuit_name}架构，突破传统限制。"
                ]
            }
        }
    
    def _build_difficulty_indicators(self) -> Dict[str, Dict[str, List[str]]]:
        """构建难度指示器"""
        return {
            "technical_complexity": {
                "easy": ["基本", "简单", "直接", "常规"],
                "medium": ["详细", "深入", "系统", "综合"],
                "hard": ["复杂", "高级", "创新", "极限", "突破"]
            },
            "analysis_depth": {
                "easy": ["描述", "说明", "列举"],
                "medium": ["分析", "推导", "计算", "比较"],
                "hard": ["深入分析", "全面评估", "创新设计", "系统优化"]
            },
            "application_scope": {
                "easy": ["单一功能", "基础应用"],
                "medium": ["多功能", "特定应用", "性能优化"],
                "hard": ["系统级", "多目标优化", "新兴应用", "极端条件"]
            }
        }
    
    def get_question_template(self, question_type: str, difficulty: str) -> Optional[str]:
        """获取指定类型和难度的问题模板"""
        if question_type in self.question_templates:
            if difficulty in self.question_templates[question_type]:
                templates = self.question_templates[question_type][difficulty]
                return random.choice(templates) if templates else None
        return None
    
    def get_question_types_distribution(self, config: Dict[str, Any]) -> Dict[str, float]:
        """获取问题类型分布"""
        return config.get("question_generation.question_types", {
            QuestionType.CIRCUIT_ANALYSIS.value: 0.25,
            QuestionType.DESIGN_OPTIMIZATION.value: 0.20,
            QuestionType.PARAMETER_CALCULATION.value: 0.15,
            QuestionType.PERFORMANCE_COMPARISON.value: 0.15,
            QuestionType.TROUBLESHOOTING.value: 0.10,
            QuestionType.APPLICATION_DESIGN.value: 0.15
        })
    
    def get_difficulty_distribution(self, config: Dict[str, Any]) -> Dict[str, float]:
        """获取难度分布"""
        return config.get("question_generation.difficulty_distribution", {
            DifficultyLevel.EASY.value: 0.2,
            DifficultyLevel.MEDIUM.value: 0.5,
            DifficultyLevel.HARD.value: 0.3
        })
    
    def select_question_type_and_difficulty(self, config: Dict[str, Any]) -> tuple[str, str]:
        """根据配置选择问题类型和难度"""
        # 选择问题类型
        type_dist = self.get_question_types_distribution(config)
        question_type = self._weighted_random_choice(type_dist)
        
        # 选择难度等级
        difficulty_dist = self.get_difficulty_distribution(config)
        difficulty = self._weighted_random_choice(difficulty_dist)
        
        return question_type, difficulty
    
    def _weighted_random_choice(self, weights: Dict[str, float]) -> str:
        """根据权重随机选择"""
        items = list(weights.keys())
        weights_list = list(weights.values())
        return random.choices(items, weights=weights_list)[0]
    
    def get_question_type_description(self, question_type: str) -> str:
        """获取问题类型描述"""
        descriptions = {
            QuestionType.CIRCUIT_ANALYSIS.value: "电路分析类问题：分析电路工作原理、特性和行为",
            QuestionType.DESIGN_OPTIMIZATION.value: "设计优化类问题：电路设计、参数优化和性能改进",
            QuestionType.PARAMETER_CALCULATION.value: "参数计算类问题：具体参数计算、公式推导和数值分析",
            QuestionType.PERFORMANCE_COMPARISON.value: "性能比较类问题：不同方案、技术或拓扑的性能对比",
            QuestionType.TROUBLESHOOTING.value: "故障诊断类问题：问题排查、故障分析和解决方案",
            QuestionType.APPLICATION_DESIGN.value: "应用设计类问题：针对特定应用的电路设计和实现"
        }
        return descriptions.get(question_type, "未知问题类型")
