"""
Mermaid Knowledge Graph Extractor for CT-MA System.

Extracts circuit application-oriented knowledge graphs and converts to Mermaid format.
"""

import json
from typing import Dict, List, Any, Set
from pathlib import Path

from ..utils.logger import LoggerMixin
from ..utils.config_manager import ConfigManager


class MermaidKGExtractor(LoggerMixin):
    """Extract and convert knowledge graphs to Mermaid format."""
    
    def __init__(self, config: ConfigManager):
        """Initialize Mermaid KG Extractor."""
        self.config = config
        
    def extract_circuit_application_graphs(self, kg_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract circuit application-oriented subgraphs.
        
        Args:
            kg_data: Complete knowledge graph data
            
        Returns:
            List of circuit application subgraphs with Mermaid format
        """
        self.logger.info("Extracting circuit application-oriented knowledge graphs...")
        
        nodes = kg_data.get('nodes', [])
        edges = kg_data.get('edges', [])
        
        # Find all circuit application nodes
        circuit_apps = [node for node in nodes if node.get('node_type') == 'circuit_application']
        
        self.logger.info(f"Found {len(circuit_apps)} circuit applications")
        
        extracted_graphs = []
        
        for app_node in circuit_apps:
            app_id = app_node.get('id')
            app_label = app_node.get('label', 'Unknown Application')
            
            # Extract subgraph for this application
            subgraph_data = self._extract_application_subgraph(app_node, nodes, edges)
            
            # Convert to Mermaid format
            mermaid_graph = self._convert_to_mermaid(subgraph_data, app_label)
            
            # Create comprehensive graph data
            graph_info = {
                'application_id': app_id,
                'application_label': app_label,
                'application_summary': app_node.get('summary', ''),
                'subgraph_data': subgraph_data,
                'mermaid_syntax': mermaid_graph,
                'statistics': {
                    'total_nodes': len(subgraph_data['nodes']),
                    'total_edges': len(subgraph_data['edges']),
                    'node_types': self._count_node_types(subgraph_data['nodes']),
                    'max_depth': self._calculate_max_depth(subgraph_data, app_id)
                }
            }
            
            extracted_graphs.append(graph_info)
        
        self.logger.info(f"Extracted {len(extracted_graphs)} circuit application graphs")
        return extracted_graphs
    
    def _extract_application_subgraph(
        self,
        app_node: Dict[str, Any],
        all_nodes: List[Dict[str, Any]],
        all_edges: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract subgraph for a specific circuit application."""
        app_id = app_node.get('id')
        app_label = app_node.get('label', app_id)

        self.logger.info(f"Extracting subgraph for application: {app_label} (ID: {app_id})")

        # Create node lookup
        node_lookup = {node['id']: node for node in all_nodes}

        # Find all edges related to this application
        related_edges = []
        for edge in all_edges:
            source = edge.get('source_id') or edge.get('source')
            target = edge.get('target_id') or edge.get('target')

            # Include edge if it connects to or from the application
            if source == app_id or target == app_id:
                related_edges.append(edge)

        self.logger.info(f"Found {len(related_edges)} direct edges for {app_label}")

        # Collect all directly connected nodes
        connected_nodes = set([app_id])
        for edge in related_edges:
            source = edge.get('source_id') or edge.get('source')
            target = edge.get('target_id') or edge.get('target')
            if source:
                connected_nodes.add(source)
            if target:
                connected_nodes.add(target)

        # Expand to include nodes connected to the directly connected nodes
        # This captures the broader context around the application
        second_level_edges = []
        for node_id in list(connected_nodes):
            if node_id == app_id:  # Skip the application itself for second level
                continue

            for edge in all_edges:
                source = edge.get('source_id') or edge.get('source')
                target = edge.get('target_id') or edge.get('target')

                # Add edges where current connected node is source or target
                if (source == node_id or target == node_id) and edge not in related_edges:
                    second_level_edges.append(edge)
                    # Add the other end of the edge to connected nodes
                    if source == node_id and target:
                        connected_nodes.add(target)
                    elif target == node_id and source:
                        connected_nodes.add(source)

        # Combine all relevant edges
        all_relevant_edges = related_edges + second_level_edges

        self.logger.info(f"Total connected nodes: {len(connected_nodes)}, Total edges: {len(all_relevant_edges)}")

        # Extract subgraph nodes and edges
        subgraph_nodes = [node_lookup[node_id] for node_id in connected_nodes if node_id in node_lookup]

        # Use the relevant edges we collected (both direct and second-level)
        subgraph_edges = []
        for edge in all_relevant_edges:
            source = edge.get('source_id') or edge.get('source')
            target = edge.get('target_id') or edge.get('target')

            if source in connected_nodes and target in connected_nodes:
                # Normalize edge format
                normalized_edge = {
                    'source': source,
                    'target': target,
                    'relation': edge.get('relationship') or edge.get('relation', 'relates_to'),
                    'description': edge.get('description', ''),
                    'weight': edge.get('weight', 1.0)
                }
                subgraph_edges.append(normalized_edge)

        self.logger.info(f"Extracted subgraph for {app_label}: {len(subgraph_nodes)} nodes, {len(subgraph_edges)} edges")

        # Log node types for debugging
        node_types = {}
        for node in subgraph_nodes:
            node_type = node.get('node_type', 'unknown')
            node_types[node_type] = node_types.get(node_type, 0) + 1
        self.logger.info(f"Node types in subgraph: {node_types}")

        # Generate Mermaid syntax
        mermaid_syntax = self._convert_to_mermaid({'nodes': subgraph_nodes, 'edges': subgraph_edges}, app_label)

        # Create readable description for LLM
        readable_description = self._create_readable_description(app_node, subgraph_nodes, subgraph_edges)

        return {
            'application_id': app_id,
            'application_label': app_label,
            'nodes': subgraph_nodes,
            'edges': subgraph_edges,
            'mermaid_syntax': mermaid_syntax,
            'readable_description': readable_description,
            'node_count': len(subgraph_nodes),
            'edge_count': len(subgraph_edges),
            'center_application': app_node
        }
    
    def _convert_to_mermaid(self, subgraph_data: Dict[str, Any], app_label: str) -> str:
        """Convert subgraph to Mermaid syntax."""
        nodes = subgraph_data['nodes']
        edges = subgraph_data['edges']
        
        mermaid_lines = [
            f"graph TD",
            f"    %% Circuit Application: {app_label}",
            ""
        ]
        
        # Define node styles
        node_styles = {
            'basic_concept': 'fill:#e1f5fe,stroke:#01579b,stroke-width:2px',
            'core_technology': 'fill:#f3e5f5,stroke:#4a148c,stroke-width:2px', 
            'circuit_application': 'fill:#e8f5e8,stroke:#1b5e20,stroke-width:3px'
        }
        
        # Add nodes with proper formatting
        for node in nodes:
            node_id = node.get('id', '').replace('-', '_').replace('.', '_')
            node_label = node.get('label', 'Unknown')
            node_type = node.get('node_type', 'unknown')
            
            # Clean label for Mermaid
            clean_label = node_label.replace('"', "'").replace('\n', ' ')
            if len(clean_label) > 20:
                clean_label = clean_label[:17] + "..."
            
            # Add node definition
            mermaid_lines.append(f'    {node_id}["{clean_label}"]')
        
        mermaid_lines.append("")
        
        # Add edges
        for edge in edges:
            source = edge.get('source', '').replace('-', '_').replace('.', '_')
            target = edge.get('target', '').replace('-', '_').replace('.', '_')
            relation = edge.get('relation', 'relates_to')
            
            # Clean relation label
            clean_relation = relation.replace('_', ' ').title()
            if len(clean_relation) > 15:
                clean_relation = clean_relation[:12] + "..."
            
            mermaid_lines.append(f'    {source} -->|{clean_relation}| {target}')
        
        mermaid_lines.append("")
        
        # Add node styling
        for node in nodes:
            node_id = node.get('id', '').replace('-', '_').replace('.', '_')
            node_type = node.get('node_type', 'unknown')
            
            if node_type in node_styles:
                mermaid_lines.append(f'    classDef {node_type}_style {node_styles[node_type]}')
                mermaid_lines.append(f'    class {node_id} {node_type}_style')
        
        return '\n'.join(mermaid_lines)
    
    def _count_node_types(self, nodes: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count nodes by type."""
        type_counts = {}
        for node in nodes:
            node_type = node.get('node_type', 'unknown')
            type_counts[node_type] = type_counts.get(node_type, 0) + 1
        return type_counts
    
    def _calculate_max_depth(self, subgraph_data: Dict[str, Any], center_id: str) -> int:
        """Calculate maximum depth from center application node."""
        # Simple BFS to calculate depth
        nodes = {node['id']: node for node in subgraph_data['nodes']}
        edges = subgraph_data['edges']
        
        visited = {center_id: 0}
        queue = [(center_id, 0)]
        max_depth = 0
        
        while queue:
            current_id, depth = queue.pop(0)
            max_depth = max(max_depth, depth)
            
            # Find connected nodes
            for edge in edges:
                next_id = None
                if edge['source'] == current_id and edge['target'] not in visited:
                    next_id = edge['target']
                elif edge['target'] == current_id and edge['source'] not in visited:
                    next_id = edge['source']
                
                if next_id and next_id in nodes:
                    visited[next_id] = depth + 1
                    queue.append((next_id, depth + 1))
        
        return max_depth
    
    def save_mermaid_graphs(self, extracted_graphs: List[Dict[str, Any]], output_path: str) -> None:
        """Save extracted graphs to JSON file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare data for saving
        save_data = {
            'metadata': {
                'total_applications': len(extracted_graphs),
                'extraction_timestamp': self._get_timestamp(),
                'description': 'Circuit application-oriented knowledge graphs in Mermaid format'
            },
            'graphs': extracted_graphs
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Saved {len(extracted_graphs)} Mermaid graphs to: {output_path}")
    
    def generate_readable_text_description(self, graph_data: Dict[str, Any]) -> str:
        """
        Generate readable text description of the knowledge graph structure.

        Args:
            graph_data: Single graph data with subgraph information

        Returns:
            Readable text description for logic analysis
        """
        app_label = graph_data['application_label']
        nodes = graph_data['subgraph_data']['nodes']
        edges = graph_data['subgraph_data']['edges']

        # Categorize nodes by type
        basic_concepts = [n for n in nodes if n.get('node_type') == 'basic_concept']
        core_technologies = [n for n in nodes if n.get('node_type') == 'core_technology']
        main_logic = [n for n in nodes if n.get('node_type') == 'main_logic']
        related_applications = [n for n in nodes if n.get('node_type') == 'circuit_application' and n.get('id') != graph_data['application_id']]

        # Analyze direct connections
        app_id = graph_data['application_id']
        direct_connections = self._find_direct_connections(app_id, edges, nodes)

        # Analyze technology layers
        tech_layers = self._analyze_technology_layers(nodes, edges)

        # Generate comprehensive readable description
        description = f"""为了解决{app_label}的设计问题，我需要整理相关的技术逻辑脉络：

【目标应用分析】:
应用名称: {app_label}
技术复杂度: 涉及 {len(basic_concepts)} 个基础概念、{len(core_technologies)} 个核心技术
系统集成度: 通过 {len(edges)} 条技术关联实现系统整合

【直接关联的核心技术】:"""

        direct_techs = [conn for conn in direct_connections if conn.get('node_type') == 'core_technology']
        if direct_techs:
            for i, tech in enumerate(direct_techs[:5], 1):  # 显示前5个最重要的
                keywords = ', '.join(tech.get('keywords', [])[:3])
                description += f"\n{i}. {tech['label']}: {tech.get('summary', '核心技术节点')[:80]}..."
                if keywords:
                    description += f"\n   关键词: {keywords}"
        else:
            description += "\n暂未发现直接关联的核心技术，需要通过间接路径分析。"

        description += f"""

【支撑的基础概念】:"""

        # Find concepts connected to core technologies
        tech_concepts = self._find_concepts_for_technologies(direct_techs + core_technologies[:3], edges, basic_concepts)
        if tech_concepts:
            for i, concept in enumerate(tech_concepts[:6], 1):  # 显示前6个概念
                keywords = ', '.join(concept.get('keywords', [])[:3])
                description += f"\n{i}. {concept['label']}: {concept.get('summary', '基础概念节点')[:80]}..."
                if keywords:
                    description += f"\n   关键词: {keywords}"
        else:
            description += "\n需要进一步分析基础概念的支撑关系。"

        description += f"""

【其他关联的核心技术】:"""

        indirect_techs = [tech for tech in core_technologies if tech not in direct_techs][:4]
        if indirect_techs:
            for i, tech in enumerate(indirect_techs, 1):
                keywords = ', '.join(tech.get('keywords', [])[:3])
                description += f"\n{i}. {tech['label']}: {tech.get('summary', '相关技术节点')[:80]}..."
                if keywords:
                    description += f"\n   关键词: {keywords}"

        # Add main logic connections if available
        if main_logic:
            description += f"""

【主要逻辑支撑】:"""
            for i, logic in enumerate(main_logic[:3], 1):
                description += f"\n{i}. {logic['label']}: {logic.get('summary', '主逻辑节点')[:80]}..."

        if related_applications:
            description += f"""

【相关的电路应用】:"""
            for i, app in enumerate(related_applications[:3], 1):
                description += f"\n{i}. {app['label']}: {app.get('summary', '相关应用')[:80]}..."

        # Add technology layer analysis
        if tech_layers:
            description += f"""

【技术层次分析】:"""
            for layer_name, layer_nodes in tech_layers.items():
                if layer_nodes:
                    description += f"\n{layer_name}: {len(layer_nodes)} 个节点"
                    for node in layer_nodes[:2]:  # 显示每层前2个节点
                        description += f"\n  - {node['label']}"

        description += f"""

【技术路径分析】:
从 {len(basic_concepts)} 个基础概念出发，通过 {len(core_technologies)} 个核心技术的有机组合，最终实现{app_label}的设计目标。
技术演进路径体现了从理论基础→技术实现→系统应用的完整逻辑链条。
需要重点分析各技术节点之间的因果关系、依赖关系和协同效应，确保技术选择的合理性和实现路径的可行性。

【关键技术挑战】:
1. 基础概念的深度理解和准确应用
2. 核心技术之间的协调配合和性能优化
3. 系统级集成中的技术权衡和设计约束
4. 实际应用中的工程实现和性能验证
"""

        return description
    
    def _find_direct_connections(self, app_id: str, edges: List[Dict[str, Any]], nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find nodes directly connected to the application."""
        node_lookup = {node['id']: node for node in nodes}
        connected_ids = set()

        for edge in edges:
            source = edge.get('source_id') or edge.get('source')
            target = edge.get('target_id') or edge.get('target')

            if source == app_id:
                connected_ids.add(target)
            elif target == app_id:
                connected_ids.add(source)

        return [node_lookup[node_id] for node_id in connected_ids if node_id in node_lookup]
    
    def _find_concepts_for_technologies(
        self,
        technologies: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        concepts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find concepts connected to given technologies."""
        tech_ids = {tech['id'] for tech in technologies}
        concept_lookup = {concept['id']: concept for concept in concepts}
        connected_concept_ids = set()

        for edge in edges:
            source = edge.get('source_id') or edge.get('source')
            target = edge.get('target_id') or edge.get('target')

            if source in tech_ids and target in concept_lookup:
                connected_concept_ids.add(target)
            elif target in tech_ids and source in concept_lookup:
                connected_concept_ids.add(source)

        return [concept_lookup[concept_id] for concept_id in connected_concept_ids]

    def _analyze_technology_layers(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Analyze technology layers based on node properties."""
        layers = {
            '基础理论层': [],
            '器件技术层': [],
            '电路技术层': [],
            '系统应用层': []
        }

        for node in nodes:
            # Check if node has knowledge_layer property
            knowledge_layer = node.get('properties', {}).get('knowledge_layer', '')

            if '基础理论' in knowledge_layer or node.get('node_type') == 'basic_concept':
                layers['基础理论层'].append(node)
            elif '器件技术' in knowledge_layer:
                layers['器件技术层'].append(node)
            elif '电路技术' in knowledge_layer or node.get('node_type') == 'core_technology':
                layers['电路技术层'].append(node)
            elif '系统应用' in knowledge_layer or node.get('node_type') == 'circuit_application':
                layers['系统应用层'].append(node)
            elif node.get('node_type') == 'main_logic':
                layers['基础理论层'].append(node)

        # Remove empty layers
        return {k: v for k, v in layers.items() if v}
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def create_mermaid_visualization_file(self, graph_data: Dict[str, Any], output_path: str) -> None:
        """Create standalone Mermaid visualization file."""
        mermaid_content = f"""# {graph_data['application_label']} - Knowledge Graph

## Application Summary
{graph_data.get('application_summary', 'No summary available')}

## Statistics
- Total Nodes: {graph_data['statistics']['total_nodes']}
- Total Edges: {graph_data['statistics']['total_edges']}
- Max Depth: {graph_data['statistics']['max_depth']}
- Node Types: {graph_data['statistics']['node_types']}

## Mermaid Diagram

```mermaid
{graph_data['mermaid_syntax']}
```

## Readable Description

{self.generate_readable_text_description(graph_data)}
"""
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(mermaid_content)
        
        self.logger.info(f"Created Mermaid visualization file: {output_path}")

    def _create_readable_description(self, app_node: Dict[str, Any], nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> str:
        """Create a readable description of the subgraph for LLM processing."""
        app_label = app_node.get('label', 'Unknown Application')

        # Categorize nodes by type
        node_categories = {}
        for node in nodes:
            node_type = node.get('node_type', 'unknown')
            if node_type not in node_categories:
                node_categories[node_type] = []
            node_categories[node_type].append(node)

        # Build description
        description_parts = [
            f"电路应用：{app_label}",
            f"总节点数：{len(nodes)}，总连接数：{len(edges)}",
            ""
        ]

        # Describe each category
        for node_type, type_nodes in node_categories.items():
            if node_type == 'circuit_application':
                continue  # Skip the main application itself

            type_name_map = {
                'basic_concept': '基础概念',
                'core_technology': '核心技术',
                'main_logic': '主要逻辑',
                'sub_logic': '子逻辑'
            }

            type_name = type_name_map.get(node_type, node_type)
            description_parts.append(f"{type_name}节点 ({len(type_nodes)}个):")

            for node in type_nodes[:5]:  # Limit to first 5 nodes per category
                label = node.get('label', 'Unknown')
                summary = node.get('summary', '')
                if summary:
                    description_parts.append(f"  - {label}: {summary[:100]}...")
                else:
                    description_parts.append(f"  - {label}")

            if len(type_nodes) > 5:
                description_parts.append(f"  ... 还有 {len(type_nodes) - 5} 个节点")
            description_parts.append("")

        # Describe key relationships
        if edges:
            description_parts.append("主要连接关系:")
            relation_counts = {}
            for edge in edges:
                relation = edge.get('relation', 'unknown')
                relation_counts[relation] = relation_counts.get(relation, 0) + 1

            for relation, count in sorted(relation_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                description_parts.append(f"  - {relation}: {count} 个连接")

        return "\n".join(description_parts)
