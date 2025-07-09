"""
知识图谱融合器
功能：将主逻辑知识图谱和子逻辑知识图谱融合成统一的大知识图谱
"""

import os
import json
from typing import List, Dict, Any
from datetime import datetime
from openai import OpenAI

from .utils import config_manager, file_manager, logger, retry_on_failure

class KnowledgeGraphFuser:
    """知识图谱融合器"""
    
    def __init__(self, workers: int = 8):
        """初始化"""
        self.client = OpenAI(
            api_key="sk-pBUBTdSpfx0ppYf30rzzmbr60WiffKq52EQzx45r9rntGjli",
            base_url="https://www.dmxapi.cn/v1",
        )
        self.model = "DMXAPI-DeepSeek-V3"
        self.workers = workers
        
        # 融合器状态
        self.unified_kg = None
        self.cross_connections = []
        
        # 颜色配置
        self.node_colors = {
            'main_logic': '#FF6B6B',           # 主逻辑 - 红色
            'basic_concept': '#4ECDC4',        # 基础概念 - 青色
            'core_technology': '#45B7D1',      # 核心技术 - 蓝色
            'circuit_application': '#96CEB4'   # 电路应用 - 绿色
        }
        
        print("🔗 [知识图谱融合器] 初始化完成")
        print(f"📡 使用模型: {self.model}")
        print(f"🚀 并发数: {workers}")
    
    def fuse_knowledge_graphs(self) -> Dict[str, Any]:
        """融合知识图谱"""
        print("\n" + "="*60)
        print("🔗 开始知识图谱融合")
        print("="*60)
        
        # 1. 加载主逻辑知识图谱
        main_logic_kg = self._load_main_logic_kg()
        if not main_logic_kg:
            print("❌ 无法加载主逻辑知识图谱")
            return {}
        
        # 2. 加载子逻辑知识图谱
        sub_logic_kgs = self._load_sub_logic_kgs()
        if not sub_logic_kgs:
            print("❌ 无法加载子逻辑知识图谱")
            return {}
        
        # 3. 加载跨章节连接
        cross_connections = self._load_cross_connections()
        
        # 4. 融合知识图谱
        unified_kg = self._fuse_graphs(main_logic_kg, sub_logic_kgs, cross_connections)
        
        # 5. 优化和验证
        optimized_kg = self._optimize_unified_kg(unified_kg)
        
        # 6. 保存结果
        self._save_unified_kg(optimized_kg)
        
        print(f"✅ 知识图谱融合完成")
        return optimized_kg
    
    def _load_main_logic_kg(self) -> Dict[str, Any]:
        """加载主逻辑知识图谱"""
        print("📂 加载主逻辑知识图谱...")
        
        try:
            main_logic_file = file_manager.get_path("main_logic", "main_logic_kg.json")
            with open(main_logic_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"✅ 成功加载主逻辑知识图谱")
            print(f"   - 节点数: {len(data.get('nodes', []))}")
            print(f"   - 边数: {len(data.get('edges', []))}")
            
            return data
            
        except Exception as e:
            print(f"❌ 加载失败: {e}")
            return {}
    
    def _load_sub_logic_kgs(self) -> List[Dict]:
        """加载子逻辑知识图谱"""
        print("📂 加载子逻辑知识图谱...")
        
        try:
            summary_file = file_manager.get_path("sub_logic", "sub_logic_summary.json")
            with open(summary_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            sub_logic_kgs = data.get('sub_logic_kgs', [])
            print(f"✅ 成功加载 {len(sub_logic_kgs)} 个子逻辑知识图谱")
            
            total_nodes = sum(len(kg.get('nodes', [])) for kg in sub_logic_kgs)
            total_edges = sum(len(kg.get('edges', [])) for kg in sub_logic_kgs)
            print(f"   - 总节点数: {total_nodes}")
            print(f"   - 总边数: {total_edges}")
            
            return sub_logic_kgs
            
        except Exception as e:
            print(f"❌ 加载失败: {e}")
            return []
    
    def _load_cross_connections(self) -> List[Dict]:
        """加载跨章节连接"""
        print("📂 加载跨章节连接...")
        
        try:
            connections_file = file_manager.get_path("connections", "cross_section_connections.json")
            with open(connections_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            connections = data.get('connections', [])
            print(f"✅ 成功加载 {len(connections)} 个跨章节连接")
            
            return connections
            
        except Exception as e:
            print(f"⚠️ 跨章节连接加载失败: {e}")
            return []
    
    def _fuse_graphs(self, main_logic_kg: Dict, sub_logic_kgs: List[Dict], cross_connections: List[Dict]) -> Dict[str, Any]:
        """融合知识图谱 - 实现层次化连接结构"""
        print("🔨 融合知识图谱 - 构建层次化连接结构...")

        # 初始化统一知识图谱
        unified_nodes = []
        unified_edges = []

        # 创建章节映射表
        section_mapping = {}
        for kg in sub_logic_kgs:
            section_mapping[kg.get('section_num', '')] = kg

        # 1. 添加主逻辑节点
        main_logic_nodes = []
        for node in main_logic_kg.get('nodes', []):
            unified_node = {
                'id': node.get('id', ''),
                'label': node.get('label', ''),
                'node_type': 'main_logic',
                'summary': node.get('summary', ''),
                'difficulty': node.get('difficulty', 3),
                'section_num': node.get('section_num', ''),
                'keywords': node.get('key_concepts', []),
                'formulas': [],
                'applications': node.get('learning_objectives', []),
                'properties': {
                    'knowledge_layer': node.get('knowledge_layer', ''),
                    'prerequisites': node.get('prerequisites', [])
                },
                'level': 0,  # 主逻辑层级
                'source': 'main_logic'
            }
            unified_nodes.append(unified_node)
            main_logic_nodes.append(unified_node)
        
        # 2. 添加主逻辑边
        for edge in main_logic_kg.get('edges', []):
            unified_edge = {
                'source_id': edge.get('source_id', ''),
                'target_id': edge.get('target_id', ''),
                'relationship': edge.get('relationship', ''),
                'description': edge.get('description', ''),
                'weight': edge.get('weight', 0.5),
                'evidence': edge.get('reasoning', ''),
                'bidirectional': False,
                'edge_type': 'main_logic',
                'source': 'main_logic'
            }
            unified_edges.append(unified_edge)

        # 3. 添加子逻辑节点并建立层次连接
        circuit_applications = []  # 收集所有电路应用节点

        for kg in sub_logic_kgs:
            section_num = kg.get('section_num', '')

            # 添加子逻辑节点
            section_nodes = {'basic_concepts': [], 'core_technologies': [], 'circuit_applications': []}

            for node in kg.get('nodes', []):
                unified_node = {
                    'id': node.get('id', ''),
                    'label': node.get('label', ''),
                    'node_type': node.get('node_type', 'basic_concept'),
                    'summary': node.get('summary', ''),
                    'difficulty': node.get('difficulty', 3),
                    'section_num': section_num,
                    'keywords': node.get('keywords', []),
                    'formulas': node.get('formulas', []),
                    'applications': node.get('applications', []),
                    'properties': node.get('properties', {}),
                    'level': self._get_node_level(node.get('node_type', 'basic_concept')),
                    'source': 'sub_logic'
                }
                unified_nodes.append(unified_node)

                # 按类型分类节点
                node_type = node.get('node_type', 'basic_concept')
                if node_type == 'basic_concept':
                    section_nodes['basic_concepts'].append(unified_node)
                elif node_type == 'core_technology':
                    section_nodes['core_technologies'].append(unified_node)
                elif node_type == 'circuit_application':
                    section_nodes['circuit_applications'].append(unified_node)
                    circuit_applications.append(unified_node)

            # 建立主逻辑到子逻辑的连接
            main_node = self._find_main_logic_node_for_section(main_logic_nodes, section_num)
            if main_node:
                # 主逻辑节点连接到该章节的电路应用节点
                for app_node in section_nodes['circuit_applications']:
                    unified_edges.append({
                        'source_id': main_node['id'],
                        'target_id': app_node['id'],
                        'relationship': 'contains_application',
                        'description': f"主逻辑章节{section_num}包含电路应用{app_node['label']}",
                        'weight': 0.9,
                        'evidence': f"章节{section_num}的主要应用",
                        'bidirectional': False,
                        'edge_type': 'main_to_sub',
                        'source': 'hierarchical_connection'
                    })

            # 建立子逻辑内部的层次连接：基础概念 → 核心技术 → 电路应用
            self._build_hierarchical_connections(section_nodes, unified_edges)
        
        # 4. 添加原有的子逻辑边
        for kg in sub_logic_kgs:
            for edge in kg.get('edges', []):
                unified_edge = {
                    'source_id': edge.get('source_id', ''),
                    'target_id': edge.get('target_id', ''),
                    'relationship': edge.get('relationship', ''),
                    'description': edge.get('description', ''),
                    'weight': edge.get('weight', 0.5),
                    'evidence': edge.get('evidence', ''),
                    'bidirectional': edge.get('bidirectional', False),
                    'edge_type': 'intra_section',
                    'source': 'sub_logic'
                }
                unified_edges.append(unified_edge)

        # 5. 建立以电路应用为中心的跨章节连接
        self._build_circuit_application_connections(circuit_applications, unified_edges, cross_connections)

        # 6. 添加跨章节连接（电路应用之间的技术关联）
        for conn in cross_connections:
            if conn.get('has_connection', False):
                unified_edge = {
                    'source_id': conn.get('source_id', ''),
                    'target_id': conn.get('target_id', ''),
                    'relationship': conn.get('connection_type', 'relates_to'),
                    'description': conn.get('description', ''),
                    'weight': conn.get('connection_strength', 0.5),
                    'evidence': conn.get('technical_evidence', ''),
                    'bidirectional': False,
                    'edge_type': 'inter_section',
                    'source': 'cross_connection'
                }
                unified_edges.append(unified_edge)

        # 7. 构建统一知识图谱
        unified_kg = {
            'title': 'CAL-KG统一知识图谱',
            'timestamp': datetime.now().isoformat(),
            'nodes': unified_nodes,
            'edges': unified_edges,
            'statistics': {
                'total_nodes': len(unified_nodes),
                'total_edges': len(unified_edges),
                'main_logic_nodes': len([n for n in unified_nodes if n['node_type'] == 'main_logic']),
                'basic_concept_nodes': len([n for n in unified_nodes if n['node_type'] == 'basic_concept']),
                'core_technology_nodes': len([n for n in unified_nodes if n['node_type'] == 'core_technology']),
                'circuit_application_nodes': len([n for n in unified_nodes if n['node_type'] == 'circuit_application']),
                'cross_section_edges': len([e for e in unified_edges if e['edge_type'] == 'inter_section'])
            },
            'metadata': {
                'fusion_method': 'hierarchical_integration',
                'main_logic_source': 'main_logic_kg.json',
                'sub_logic_source': 'sub_logic_summary.json',
                'cross_connections_source': 'cross_section_connections.json',
                'fusion_timestamp': datetime.now().isoformat()
            }
        }
        
        print(f"✅ 知识图谱融合完成")
        print(f"   - 总节点数: {len(unified_nodes)}")
        print(f"   - 总边数: {len(unified_edges)}")
        print(f"   - 主逻辑节点: {unified_kg['statistics']['main_logic_nodes']}")
        print(f"   - 基础概念节点: {unified_kg['statistics']['basic_concept_nodes']}")
        print(f"   - 核心技术节点: {unified_kg['statistics']['core_technology_nodes']}")
        print(f"   - 电路应用节点: {unified_kg['statistics']['circuit_application_nodes']}")
        print(f"   - 跨章节连接: {unified_kg['statistics']['cross_section_edges']}")
        
        return unified_kg
    
    def _get_node_level(self, node_type: str) -> int:
        """获取节点层级"""
        level_mapping = {
            'main_logic': 0,
            'basic_concept': 1,
            'core_technology': 2,
            'circuit_application': 3
        }
        return level_mapping.get(node_type, 1)

    def _find_main_logic_node_for_section(self, main_logic_nodes: List[Dict], section_num: str) -> Dict:
        """为章节找到对应的主逻辑节点"""
        # 尝试精确匹配
        for node in main_logic_nodes:
            if node.get('section_num') == section_num:
                return node

        # 尝试模糊匹配（章节号的前缀）
        section_prefix = section_num.split('.')[0] if '.' in section_num else section_num
        for node in main_logic_nodes:
            node_section = node.get('section_num', '')
            if node_section.startswith(section_prefix):
                return node

        return None

    def _build_hierarchical_connections(self, section_nodes: Dict, unified_edges: List[Dict]):
        """建立章节内的层次连接：基础概念 → 核心技术 → 电路应用"""

        # 基础概念 → 核心技术
        for concept in section_nodes['basic_concepts']:
            for tech in section_nodes['core_technologies']:
                # 基于关键词相似性建立连接
                if self._has_keyword_similarity(concept, tech):
                    unified_edges.append({
                        'source_id': concept['id'],
                        'target_id': tech['id'],
                        'relationship': 'enables',
                        'description': f"基础概念{concept['label']}使能核心技术{tech['label']}",
                        'weight': 0.7,
                        'evidence': '基于关键词相似性的层次连接',
                        'bidirectional': False,
                        'edge_type': 'hierarchical',
                        'source': 'hierarchical_connection'
                    })

        # 核心技术 → 电路应用
        for tech in section_nodes['core_technologies']:
            for app in section_nodes['circuit_applications']:
                # 基于关键词相似性建立连接
                if self._has_keyword_similarity(tech, app):
                    unified_edges.append({
                        'source_id': tech['id'],
                        'target_id': app['id'],
                        'relationship': 'implements',
                        'description': f"核心技术{tech['label']}实现电路应用{app['label']}",
                        'weight': 0.8,
                        'evidence': '基于关键词相似性的层次连接',
                        'bidirectional': False,
                        'edge_type': 'hierarchical',
                        'source': 'hierarchical_connection'
                    })

        # 基础概念 → 电路应用（直接支撑关系）
        for concept in section_nodes['basic_concepts']:
            for app in section_nodes['circuit_applications']:
                if self._has_strong_keyword_similarity(concept, app):
                    unified_edges.append({
                        'source_id': concept['id'],
                        'target_id': app['id'],
                        'relationship': 'supports',
                        'description': f"基础概念{concept['label']}支撑电路应用{app['label']}",
                        'weight': 0.6,
                        'evidence': '基于强关键词相似性的直接支撑',
                        'bidirectional': False,
                        'edge_type': 'hierarchical',
                        'source': 'hierarchical_connection'
                    })

    def _build_circuit_application_connections(self, circuit_applications: List[Dict], unified_edges: List[Dict], cross_connections: List[Dict]):
        """建立以电路应用为中心的知识点连接"""

        # 为每个电路应用建立与其他知识点的连接
        for app in circuit_applications:
            app_keywords = set(app.get('keywords', []))
            app_section = app.get('section_num', '')

            # 连接到相关的基础概念和核心技术（跨章节）
            for other_app in circuit_applications:
                if app['id'] != other_app['id'] and app_section != other_app.get('section_num', ''):
                    # 基于关键词相似性建立跨章节连接
                    if self._has_keyword_similarity(app, other_app):
                        unified_edges.append({
                            'source_id': app['id'],
                            'target_id': other_app['id'],
                            'relationship': 'relates_to_application',
                            'description': f"电路应用{app['label']}与{other_app['label']}技术相关",
                            'weight': 0.5,
                            'evidence': '基于关键词相似性的应用关联',
                            'bidirectional': True,
                            'edge_type': 'application_network',
                            'source': 'application_connection'
                        })

    def _has_keyword_similarity(self, node1: Dict, node2: Dict, threshold: float = 0.2) -> bool:
        """检查两个节点是否有关键词相似性"""
        keywords1 = set(node1.get('keywords', []))
        keywords2 = set(node2.get('keywords', []))

        if not keywords1 or not keywords2:
            return False

        intersection = keywords1.intersection(keywords2)
        union = keywords1.union(keywords2)

        similarity = len(intersection) / len(union) if union else 0
        return similarity >= threshold

    def _has_strong_keyword_similarity(self, node1: Dict, node2: Dict, threshold: float = 0.4) -> bool:
        """检查两个节点是否有强关键词相似性"""
        return self._has_keyword_similarity(node1, node2, threshold)

    def _optimize_unified_kg(self, unified_kg: Dict[str, Any]) -> Dict[str, Any]:
        """优化统一知识图谱"""
        print("🔧 优化统一知识图谱...")
        
        # 去重节点ID
        seen_node_ids = set()
        unique_nodes = []
        for node in unified_kg['nodes']:
            if node['id'] not in seen_node_ids:
                unique_nodes.append(node)
                seen_node_ids.add(node['id'])
        
        # 去重边
        seen_edges = set()
        unique_edges = []
        for edge in unified_kg['edges']:
            edge_key = (edge['source_id'], edge['target_id'], edge['relationship'])
            if edge_key not in seen_edges:
                unique_edges.append(edge)
                seen_edges.add(edge_key)
        
        # 更新统计信息
        unified_kg['nodes'] = unique_nodes
        unified_kg['edges'] = unique_edges
        unified_kg['statistics']['total_nodes'] = len(unique_nodes)
        unified_kg['statistics']['total_edges'] = len(unique_edges)
        
        print(f"✅ 优化完成")
        print(f"   - 去重后节点数: {len(unique_nodes)}")
        print(f"   - 去重后边数: {len(unique_edges)}")
        
        return unified_kg
    
    def _save_unified_kg(self, unified_kg: Dict[str, Any]):
        """保存统一知识图谱"""
        print("💾 保存统一知识图谱...")
        
        # 保存完整的统一知识图谱
        file_manager.save_json(unified_kg, "final", "unified_knowledge_graph.json")
        
        # 保存节点和边的单独文件
        file_manager.save_json(unified_kg['nodes'], "final", "unified_nodes.json")
        file_manager.save_json(unified_kg['edges'], "final", "unified_edges.json")
        
        # 保存统计信息
        file_manager.save_json(unified_kg['statistics'], "final", "kg_statistics.json")
        
        print(f"✅ 统一知识图谱保存完成")

def main():
    """测试函数"""
    fuser = KnowledgeGraphFuser(workers=8)
    
    # 融合知识图谱
    result = fuser.fuse_knowledge_graphs()
    
    if result:
        print(f"融合成功: {len(result.get('nodes', []))} 个节点")
    else:
        print("融合失败")

if __name__ == "__main__":
    main()
