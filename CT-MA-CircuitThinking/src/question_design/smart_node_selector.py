#!/usr/bin/env python3
"""
智能节点选择器
根据问题内容选择性提取相关节点，而不是处理所有节点
"""

import asyncio
import json
import re
from typing import List, Dict, Any, Set
from ..utils.logger import get_logger
from ..agents.base_agent import BaseAgent


class SmartNodeSelector(BaseAgent):
    """智能节点选择器 - 根据问题选择相关节点"""
    
    def __init__(self, config):
        """初始化智能节点选择器"""
        super().__init__(config, "smart_node_selector")
        # logger属性已经通过LoggerMixin提供，无需重新设置

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """实现抽象方法execute"""
        application_topic = input_data.get('application_topic', '')
        subgraph = input_data.get('subgraph', {})
        max_nodes = input_data.get('max_nodes', 20)

        return await self.select_relevant_nodes_by_topic(application_topic, subgraph, max_nodes)
        
    async def select_relevant_nodes_by_topic(
        self,
        application_topic: str,
        subgraph: Dict[str, Any],
        max_nodes: int = 20
    ) -> Dict[str, Any]:
        """
        根据应用主题选择相关节点

        Args:
            application_topic: 应用主题（如"CMOS运算放大器"）
            subgraph: 完整子图
            max_nodes: 最大节点数量

        Returns:
            筛选后的子图
        """
        self.logger.info(f"Selecting relevant nodes for topic: {application_topic} (max: {max_nodes})")

        try:
            # 1. 提取主题中的关键技术词汇
            key_terms = self._extract_key_terms_from_topic(application_topic)
            self.logger.info(f"Extracted key terms: {key_terms}")

            # 2. 使用LLM进行智能节点选择
            selected_node_ids = await self._llm_select_nodes_by_topic(application_topic, subgraph, key_terms, max_nodes)

            # 3. 构建筛选后的子图
            filtered_subgraph = self._build_filtered_subgraph(subgraph, selected_node_ids)

            self.logger.info(f"Selected {len(selected_node_ids)} nodes from {len(subgraph.get('nodes', []))} total nodes")

            return {
                'success': True,
                'filtered_subgraph': filtered_subgraph,
                'selected_node_count': len(selected_node_ids),
                'key_terms': key_terms
            }

        except Exception as e:
            self.logger.error(f"Node selection failed: {e}")
            return {
                'success': False,
                'filtered_subgraph': subgraph,  # 失败时返回原始子图
                'error': str(e)
            }
    
    def _extract_key_terms_from_topic(self, topic: str) -> List[str]:
        """从应用主题中提取关键技术词汇"""
        # 技术词汇模式
        tech_patterns = [
            r'CMOS|MOSFET|BJT|JFET',  # 器件类型
            r'运算放大器|放大器|比较器|振荡器|滤波器',  # 电路类型
            r'增益|带宽|噪声|功耗|线性度|稳定性',  # 性能参数
            r'差分|共模|单端|推挽|共源|共栅',  # 电路结构
            r'频率补偿|相位裕度|增益带宽积|转换速率',  # 频域特性
            r'工艺|节点|尺寸|阈值电压|沟道长度',  # 工艺参数
            r'设计|优化|分析|计算|仿真|测试',  # 设计动作
            r'\d+nm|\d+μm|\d+MHz|\d+GHz|\d+V|\d+mA|\d+μA',  # 数值参数
        ]

        key_terms = []
        for pattern in tech_patterns:
            matches = re.findall(pattern, topic, re.IGNORECASE)
            key_terms.extend(matches)

        # 去重并转换为小写
        key_terms = list(set([term.lower() for term in key_terms]))

        return key_terms

    def _extract_key_terms_from_question(self, question: str) -> List[str]:
        """从问题中提取关键技术词汇（保留原方法以兼容）"""
        return self._extract_key_terms_from_topic(question)
    
    async def _llm_select_nodes_by_topic(
        self,
        application_topic: str,
        subgraph: Dict[str, Any],
        key_terms: List[str],
        max_nodes: int
    ) -> List[str]:
        """使用LLM基于应用主题选择相关节点"""

        # 构建节点信息摘要
        nodes_summary = []
        for node in subgraph.get('nodes', []):
            node_info = {
                'id': node.get('id'),
                'label': node.get('label', ''),
                'type': node.get('node_type', ''),
                'summary': node.get('summary', '')[:150]  # 增加摘要长度以提供更多信息
            }
            nodes_summary.append(node_info)

        # 构建选择提示
        prompt = f"""
你是电路设计专家。请从给定的知识图谱节点中选择与"{application_topic}"最相关的{max_nodes}个节点，用于构建一个小型知识图谱来生成深度技术问题。

应用主题：{application_topic}
关键技术词汇：{', '.join(key_terms)}

可选节点：
{json.dumps(nodes_summary, ensure_ascii=False, indent=2)}

选择标准（按重要性排序）：
1. 核心技术节点：直接实现该应用的关键技术
2. 基础概念节点：理解该应用所需的基本原理
3. 相关应用节点：与该应用有技术关联的其他电路
4. 设计方法节点：实现该应用的设计技术和方法

请选择能够支撑生成深度技术问题的最重要节点，确保覆盖：
- 核心工作原理
- 关键设计参数
- 性能优化技术
- 实际应用考虑

请以JSON格式返回：
{{
  "selected_node_ids": ["id1", "id2", "id3", ...],
  "selection_reasoning": "详细说明选择这些节点的理由，以及它们如何支撑深度技术问题的生成"
}}
"""
        
        try:
            # 调用LLM
            messages = [
                {"role": "system", "content": "你是电路设计专家，擅长根据应用主题选择相关的技术节点构建知识图谱。"},
                {"role": "user", "content": prompt}
            ]

            response = await self._call_llm(messages)
            self.logger.debug(f"LLM response: {response}")

            # 解析响应
            # 尝试提取JSON
            json_match = re.search(r'\{.*"selected_node_ids".*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                selected_ids = result.get('selected_node_ids', [])
                reasoning = result.get('selection_reasoning', '')

                # 验证节点ID的有效性
                valid_ids = [node['id'] for node in nodes_summary]
                selected_ids = [id for id in selected_ids if id in valid_ids]

                # 限制数量
                selected_ids = selected_ids[:max_nodes]

                self.logger.info(f"LLM selected {len(selected_ids)} nodes: {selected_ids}")
                self.logger.info(f"Selection reasoning: {reasoning}")
                return selected_ids
            else:
                self.logger.warning("Failed to extract JSON from LLM response")

        except Exception as e:
            self.logger.warning(f"LLM node selection failed: {e}, using fallback method")

        # 回退方法：基于关键词匹配
        return self._fallback_select_nodes_by_topic(subgraph, key_terms, max_nodes)

    async def _llm_select_nodes(self, question: str, subgraph: Dict[str, Any], key_terms: List[str], max_nodes: int) -> List[str]:
        """保留原方法以兼容"""
        return await self._llm_select_nodes_by_topic(question, subgraph, key_terms, max_nodes)
    
    def _fallback_select_nodes_by_topic(
        self,
        subgraph: Dict[str, Any],
        key_terms: List[str],
        max_nodes: int
    ) -> List[str]:
        """回退的节点选择方法 - 基于关键词匹配和节点重要性"""

        node_scores = []

        for node in subgraph.get('nodes', []):
            score = 0
            node_text = f"{node.get('label', '')} {node.get('summary', '')}".lower()

            # 计算关键词匹配分数
            for term in key_terms:
                if term.lower() in node_text:
                    score += 2  # 增加关键词匹配权重

            # 节点类型权重（优先选择核心技术和基础概念）
            node_type = node.get('node_type', '')
            if node_type == 'core_technology':
                score += 3  # 核心技术最重要
            elif node_type == 'basic_concept':
                score += 2  # 基础概念次重要
            elif node_type == 'circuit_application':
                score += 1  # 应用实例也重要

            # 根据节点标签中的关键词增加分数
            label = node.get('label', '').lower()
            if any(keyword in label for keyword in ['运算放大器', '放大器', 'cmos', '差分', '输出级']):
                score += 1

            node_scores.append((node.get('id'), score, node.get('label', '')))

        # 按分数排序并选择前N个
        node_scores.sort(key=lambda x: x[1], reverse=True)
        selected_ids = [node_id for node_id, score, label in node_scores[:max_nodes] if score > 0]

        # 如果没有匹配的节点，选择前几个核心技术节点
        if not selected_ids:
            core_nodes = [node for node in subgraph.get('nodes', [])
                         if node.get('node_type') in ['core_technology', 'circuit_application']]
            selected_ids = [node.get('id') for node in core_nodes[:max_nodes]]

        self.logger.info(f"Fallback method selected {len(selected_ids)} nodes")
        return selected_ids

    def _fallback_select_nodes(self, subgraph: Dict[str, Any], key_terms: List[str], max_nodes: int) -> List[str]:
        """保留原方法以兼容"""
        return self._fallback_select_nodes_by_topic(subgraph, key_terms, max_nodes)
    
    def _build_filtered_subgraph(
        self, 
        original_subgraph: Dict[str, Any], 
        selected_node_ids: List[str]
    ) -> Dict[str, Any]:
        """构建筛选后的子图"""
        
        # 筛选节点
        selected_nodes = [
            node for node in original_subgraph.get('nodes', [])
            if node.get('id') in selected_node_ids
        ]
        
        # 筛选边（只保留连接选中节点的边）
        selected_edges = []
        for edge in original_subgraph.get('edges', []):
            source = edge.get('source')
            target = edge.get('target')
            if source in selected_node_ids and target in selected_node_ids:
                selected_edges.append(edge)
        
        # 构建新的子图
        filtered_subgraph = {
            'nodes': selected_nodes,
            'edges': selected_edges,
            'application_label': original_subgraph.get('application_label', ''),
            'node_count': len(selected_nodes),
            'edge_count': len(selected_edges)
        }
        
        return filtered_subgraph
