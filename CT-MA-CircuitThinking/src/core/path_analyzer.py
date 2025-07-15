"""
Path Analyzer for CT-MA System.

Analyzes knowledge paths and dependencies in extracted subgraphs.
"""

import asyncio
from typing import Dict, List, Any, Set, Tuple, Optional
import networkx as nx

from ..utils.logger import LoggerMixin
from ..utils.config_manager import ConfigManager


class PathAnalyzer(LoggerMixin):
    """Analyzes knowledge paths and dependencies in subgraphs."""
    
    def __init__(self, config: ConfigManager):
        """
        Initialize Path Analyzer.
        
        Args:
            config: Configuration manager instance
        """
        self.config = config
    
    async def analyze_subgraph_paths(self, subgraph: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze paths in a subgraph.
        
        Args:
            subgraph: Subgraph data
            
        Returns:
            Path analysis results
        """
        # Build graph from subgraph
        graph = self._build_subgraph_graph(subgraph)
        
        # Analyze different aspects
        analysis = {
            'dependency_chains': self._analyze_dependency_chains(graph, subgraph),
            'critical_paths': self._find_critical_paths(graph, subgraph),
            'knowledge_layers': self._identify_knowledge_layers(graph, subgraph),
            'bottleneck_analysis': self._analyze_bottlenecks(graph, subgraph),
            'path_complexity': self._calculate_path_complexity(graph, subgraph)
        }
        
        return analysis
    
    def _build_subgraph_graph(self, subgraph: Dict[str, Any]) -> nx.DiGraph:
        """Build NetworkX graph from subgraph data."""
        graph = nx.DiGraph()
        
        # Add nodes
        for node in subgraph['nodes']:
            graph.add_node(node['id'], **node)
        
        # Add edges
        for edge in subgraph['edges']:
            graph.add_edge(edge['source_id'], edge['target_id'], **edge)
        
        return graph
    
    def _analyze_dependency_chains(
        self, 
        graph: nx.DiGraph, 
        subgraph: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Analyze dependency chains from basic concepts to application.
        
        Args:
            graph: NetworkX graph
            subgraph: Subgraph data
            
        Returns:
            List of dependency chains
        """
        app_node_id = subgraph['application_node_id']
        
        # Find all basic concepts
        basic_concepts = [
            node['id'] for node in subgraph['nodes']
            if node['node_type'] == 'basic_concept'
        ]
        
        chains = []
        for concept_id in basic_concepts:
            try:
                # Find all simple paths from concept to application
                paths = list(nx.all_simple_paths(
                    graph, concept_id, app_node_id, cutoff=6
                ))
                
                for path in paths:
                    chain = self._build_dependency_chain(graph, path)
                    chains.append(chain)
                    
            except nx.NetworkXNoPath:
                continue
        
        # Sort by importance (length and node types)
        chains.sort(key=lambda x: (x['importance_score'], len(x['path'])), reverse=True)
        
        return chains[:5]  # Return top 5 chains
    
    def _build_dependency_chain(self, graph: nx.DiGraph, path: List[str]) -> Dict[str, Any]:
        """Build dependency chain from path."""
        chain_nodes = []
        for node_id in path:
            node_data = graph.nodes[node_id]
            chain_nodes.append({
                'id': node_id,
                'label': node_data.get('label', ''),
                'type': node_data.get('node_type', ''),
                'summary': node_data.get('summary', '')
            })
        
        # Calculate importance score
        importance_score = self._calculate_chain_importance(graph, path)
        
        return {
            'path': chain_nodes,
            'length': len(path),
            'importance_score': importance_score,
            'description': self._generate_chain_description(chain_nodes)
        }
    
    def _calculate_chain_importance(self, graph: nx.DiGraph, path: List[str]) -> float:
        """Calculate importance score for a dependency chain."""
        score = 0.0
        
        # Length bonus (longer chains are more comprehensive)
        score += len(path) * 0.5
        
        # Node type diversity bonus
        node_types = set()
        for node_id in path:
            node_types.add(graph.nodes[node_id].get('node_type', ''))
        score += len(node_types) * 2.0
        
        # Centrality bonus
        for node_id in path:
            in_degree = graph.in_degree(node_id)
            out_degree = graph.out_degree(node_id)
            score += (in_degree + out_degree) * 0.1
        
        return score
    
    def _generate_chain_description(self, chain_nodes: List[Dict[str, Any]]) -> str:
        """Generate description for dependency chain."""
        if len(chain_nodes) < 2:
            return "单节点链"
        
        start_node = chain_nodes[0]
        end_node = chain_nodes[-1]
        
        return f"从{start_node['label']}到{end_node['label']}的技术路径"
    
    def _find_critical_paths(
        self, 
        graph: nx.DiGraph, 
        subgraph: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Find critical paths in the knowledge graph.
        
        Args:
            graph: NetworkX graph
            subgraph: Subgraph data
            
        Returns:
            List of critical paths
        """
        app_node_id = subgraph['application_node_id']
        
        # Find nodes that are critical (removing them disconnects the graph)
        critical_nodes = []
        for node_id in graph.nodes():
            if node_id == app_node_id:
                continue
                
            # Check if removing this node disconnects basic concepts from application
            temp_graph = graph.copy()
            temp_graph.remove_node(node_id)
            
            basic_concepts = [
                n for n in temp_graph.nodes()
                if temp_graph.nodes[n].get('node_type') == 'basic_concept'
            ]
            
            disconnected = False
            for concept_id in basic_concepts:
                if not nx.has_path(temp_graph, concept_id, app_node_id):
                    disconnected = True
                    break
            
            if disconnected:
                critical_nodes.append(node_id)
        
        # Build critical paths
        critical_paths = []
        for node_id in critical_nodes:
            node_data = graph.nodes[node_id]
            critical_paths.append({
                'node_id': node_id,
                'label': node_data.get('label', ''),
                'type': node_data.get('node_type', ''),
                'criticality_reason': self._analyze_criticality(graph, node_id, app_node_id)
            })
        
        return critical_paths
    
    def _analyze_criticality(
        self, 
        graph: nx.DiGraph, 
        node_id: str, 
        app_node_id: str
    ) -> str:
        """Analyze why a node is critical."""
        node_data = graph.nodes[node_id]
        node_type = node_data.get('node_type', '')
        
        if node_type == 'core_technology':
            return f"核心技术节点，是实现{graph.nodes[app_node_id].get('label', '应用')}的关键技术"
        elif node_type == 'basic_concept':
            return f"基础概念节点，为后续技术提供理论基础"
        else:
            return f"关键连接节点，连接基础概念与应用实现"
    
    def _identify_knowledge_layers(
        self, 
        graph: nx.DiGraph, 
        subgraph: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Identify knowledge layers in the subgraph.
        
        Args:
            graph: NetworkX graph
            subgraph: Subgraph data
            
        Returns:
            Dictionary of knowledge layers
        """
        app_node_id = subgraph['application_node_id']
        
        # Calculate distances from application node (reverse direction)
        try:
            distances = nx.single_source_shortest_path_length(
                graph.reverse(), app_node_id
            )
        except:
            distances = {node_id: 0 for node_id in graph.nodes()}
        
        # Group nodes by distance (layer)
        layers = {}
        for node_id, distance in distances.items():
            if distance not in layers:
                layers[distance] = []
            
            node_data = graph.nodes[node_id]
            layers[distance].append({
                'id': node_id,
                'label': node_data.get('label', ''),
                'type': node_data.get('node_type', ''),
                'summary': node_data.get('summary', '')
            })
        
        # Convert to named layers
        named_layers = {}
        max_distance = max(layers.keys()) if layers else 0
        
        for distance, nodes in layers.items():
            if distance == 0:
                layer_name = "应用层"
            elif distance == max_distance:
                layer_name = "基础层"
            else:
                layer_name = f"技术层{distance}"
            
            named_layers[layer_name] = nodes
        
        return named_layers
    
    def _analyze_bottlenecks(
        self, 
        graph: nx.DiGraph, 
        subgraph: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze potential bottlenecks in the knowledge path.
        
        Args:
            graph: NetworkX graph
            subgraph: Subgraph data
            
        Returns:
            Bottleneck analysis
        """
        app_node_id = subgraph['application_node_id']
        app_node = graph.nodes[app_node_id]
        
        # Identify technical bottlenecks
        bottlenecks = {
            'primary_challenge': self._extract_primary_challenge(app_node),
            'technical_barriers': self._identify_technical_barriers(graph, subgraph),
            'complexity_factors': self._analyze_complexity_factors(graph, subgraph)
        }
        
        return bottlenecks
    
    def _extract_primary_challenge(self, app_node: Dict[str, Any]) -> str:
        """Extract primary challenge from application node."""
        summary = app_node.get('summary', '')
        label = app_node.get('label', '')
        
        # Simple heuristic to extract challenge
        challenge_keywords = ['挑战', '难点', '瓶颈', '问题', '限制', '困难']
        
        for keyword in challenge_keywords:
            if keyword in summary:
                sentences = summary.split('。')
                for sentence in sentences:
                    if keyword in sentence:
                        return sentence.strip()
        
        # Fallback
        return f"实现{label}的核心技术挑战"
    
    def _identify_technical_barriers(
        self, 
        graph: nx.DiGraph, 
        subgraph: Dict[str, Any]
    ) -> List[str]:
        """Identify technical barriers from core technology nodes."""
        barriers = []
        
        for node in subgraph['nodes']:
            if node['node_type'] == 'core_technology':
                summary = node.get('summary', '')
                if any(keyword in summary for keyword in ['挑战', '难点', '限制']):
                    barriers.append(f"{node['label']}: {summary[:100]}...")
        
        return barriers[:3]  # Top 3 barriers
    
    def _analyze_complexity_factors(
        self, 
        graph: nx.DiGraph, 
        subgraph: Dict[str, Any]
    ) -> List[str]:
        """Analyze factors that contribute to complexity."""
        factors = []
        
        # Path length complexity
        max_path_length = subgraph['statistics'].get('max_depth', 0)
        if max_path_length > 3:
            factors.append(f"技术路径较长，需要{max_path_length}层技术积累")
        
        # Node type diversity
        node_types = subgraph['statistics'].get('node_types', {})
        if len(node_types) > 3:
            factors.append(f"涉及{len(node_types)}种不同类型的知识点")
        
        # Interconnection complexity
        edge_count = subgraph['statistics'].get('total_edges', 0)
        node_count = subgraph['statistics'].get('total_nodes', 1)
        if edge_count / node_count > 1.5:
            factors.append("知识点之间存在复杂的相互依赖关系")
        
        return factors
    
    def _calculate_path_complexity(
        self, 
        graph: nx.DiGraph, 
        subgraph: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate various complexity metrics for the path."""
        node_count = len(subgraph['nodes'])
        edge_count = len(subgraph['edges'])
        
        complexity = {
            'structural_complexity': edge_count / node_count if node_count > 0 else 0,
            'depth_complexity': subgraph['statistics'].get('max_depth', 0) / 5.0,  # Normalized
            'type_diversity': len(subgraph['statistics'].get('node_types', {})) / 4.0,  # Normalized
            'overall_complexity': 0.0
        }
        
        # Calculate overall complexity
        complexity['overall_complexity'] = (
            complexity['structural_complexity'] * 0.4 +
            complexity['depth_complexity'] * 0.3 +
            complexity['type_diversity'] * 0.3
        )
        
        return complexity
