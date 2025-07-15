"""
Subgraph Extractor for CT-MA System.

Extracts application-centered subgraphs from the unified knowledge graph.
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple, Optional
import networkx as nx

from ..utils.logger import LoggerMixin
from ..utils.config_manager import ConfigManager
from .kg_loader import KGLoader


class SubgraphExtractor(LoggerMixin):
    """Extracts subgraphs centered on circuit applications."""
    
    def __init__(self, config: ConfigManager):
        """
        Initialize Subgraph Extractor.
        
        Args:
            config: Configuration manager instance
        """
        self.config = config
        self.max_depth = config.get("subgraph.max_depth", 5)
        self.min_nodes = config.get("subgraph.min_nodes", 3)
        self.max_nodes = config.get("subgraph.max_nodes", 20)
        self.target_node_types = config.get("subgraph.target_node_types", ["circuit_application"])
        self.include_node_types = config.get("subgraph.include_node_types", 
                                           ["basic_concept", "core_technology", "circuit_application"])
    
    async def extract_application_subgraphs(self, kg_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract subgraphs for all circuit applications.
        
        Args:
            kg_data: Unified knowledge graph data
            
        Returns:
            List of extracted subgraphs
        """
        self.logger.info("Starting subgraph extraction for circuit applications")
        
        # Build graph
        graph = self._build_graph(kg_data)
        
        # Get all circuit application nodes
        app_nodes = [node for node in kg_data['nodes'] 
                    if node['node_type'] in self.target_node_types]
        
        self.logger.info(f"Found {len(app_nodes)} circuit application nodes")
        
        subgraphs = []
        for app_node in app_nodes:
            try:
                subgraph = await self._extract_single_subgraph(
                    graph, kg_data, app_node['id']
                )
                if subgraph:
                    subgraphs.append(subgraph)
            except Exception as e:
                self.logger.warning(f"Failed to extract subgraph for {app_node['id']}: {e}")
        
        # Save subgraphs
        await self._save_subgraphs(subgraphs)
        
        self.logger.info(f"Extracted {len(subgraphs)} valid subgraphs")
        return subgraphs
    
    def _build_graph(self, kg_data: Dict[str, Any]) -> nx.DiGraph:
        """Build NetworkX graph from KG data."""
        graph = nx.DiGraph()
        
        # Add nodes
        for node in kg_data['nodes']:
            graph.add_node(node['id'], **node)
        
        # Add edges
        for edge in kg_data['edges']:
            graph.add_edge(edge['source_id'], edge['target_id'], **edge)
        
        return graph
    
    async def _extract_single_subgraph(
        self, 
        graph: nx.DiGraph, 
        kg_data: Dict[str, Any], 
        app_node_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract subgraph for a single circuit application.
        
        Args:
            graph: NetworkX graph
            kg_data: Original KG data
            app_node_id: Application node ID
            
        Returns:
            Extracted subgraph data or None if invalid
        """
        # Find path from basic concepts to application
        path_nodes = self._find_application_path(graph, app_node_id)
        
        if len(path_nodes) < self.min_nodes:
            self.logger.debug(f"Subgraph for {app_node_id} too small: {len(path_nodes)} nodes")
            return None
        
        if len(path_nodes) > self.max_nodes:
            # Trim to most important nodes
            path_nodes = self._trim_path(graph, path_nodes, app_node_id)
        
        # Build subgraph
        subgraph_data = self._build_subgraph_data(graph, kg_data, path_nodes, app_node_id)
        
        return subgraph_data
    
    def _find_application_path(self, graph: nx.DiGraph, app_node_id: str) -> Set[str]:
        """
        Find all nodes in the path leading to the application.
        
        Args:
            graph: NetworkX graph
            app_node_id: Application node ID
            
        Returns:
            Set of node IDs in the path
        """
        path_nodes = set()
        visited = set()
        
        def dfs_backward(node_id: str, depth: int = 0):
            if depth > self.max_depth or node_id in visited:
                return
            
            visited.add(node_id)
            node_data = graph.nodes[node_id]
            
            # Include node if it's of the right type
            if node_data.get('node_type') in self.include_node_types:
                path_nodes.add(node_id)
            
            # Continue backward search
            for pred in graph.predecessors(node_id):
                dfs_backward(pred, depth + 1)
        
        # Start from application node
        dfs_backward(app_node_id)
        
        return path_nodes
    
    def _trim_path(self, graph: nx.DiGraph, path_nodes: Set[str], app_node_id: str) -> Set[str]:
        """
        Trim path to most important nodes.
        
        Args:
            graph: NetworkX graph
            path_nodes: Current path nodes
            app_node_id: Application node ID
            
        Returns:
            Trimmed set of node IDs
        """
        # Calculate node importance based on centrality and type
        node_scores = {}
        
        for node_id in path_nodes:
            node_data = graph.nodes[node_id]
            score = 0
            
            # Type-based scoring
            if node_data.get('node_type') == 'circuit_application':
                score += 10
            elif node_data.get('node_type') == 'core_technology':
                score += 5
            elif node_data.get('node_type') == 'basic_concept':
                score += 3
            
            # Centrality-based scoring
            in_degree = graph.in_degree(node_id)
            out_degree = graph.out_degree(node_id)
            score += (in_degree + out_degree) * 0.5
            
            node_scores[node_id] = score
        
        # Keep top nodes
        sorted_nodes = sorted(node_scores.items(), key=lambda x: x[1], reverse=True)
        trimmed_nodes = set([node_id for node_id, _ in sorted_nodes[:self.max_nodes]])
        
        # Always include the application node
        trimmed_nodes.add(app_node_id)
        
        return trimmed_nodes
    
    def _build_subgraph_data(
        self, 
        graph: nx.DiGraph, 
        kg_data: Dict[str, Any], 
        path_nodes: Set[str], 
        app_node_id: str
    ) -> Dict[str, Any]:
        """
        Build subgraph data structure.
        
        Args:
            graph: NetworkX graph
            kg_data: Original KG data
            path_nodes: Nodes to include in subgraph
            app_node_id: Application node ID
            
        Returns:
            Subgraph data structure
        """
        # Get node data
        nodes = []
        node_lookup = {node['id']: node for node in kg_data['nodes']}
        
        for node_id in path_nodes:
            if node_id in node_lookup:
                nodes.append(node_lookup[node_id])
        
        # Get edges within subgraph
        edges = []
        for edge in kg_data['edges']:
            if edge['source_id'] in path_nodes and edge['target_id'] in path_nodes:
                edges.append(edge)
        
        # Analyze path structure
        path_analysis = self._analyze_path_structure(graph, path_nodes, app_node_id)
        
        # Build subgraph
        subgraph = {
            'application_node_id': app_node_id,
            'application_label': node_lookup[app_node_id]['label'],
            'nodes': nodes,
            'edges': edges,
            'path_analysis': path_analysis,
            'statistics': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'node_types': self._count_node_types(nodes),
                'max_depth': self._calculate_max_depth(graph, path_nodes, app_node_id)
            }
        }
        
        return subgraph
    
    def _analyze_path_structure(
        self, 
        graph: nx.DiGraph, 
        path_nodes: Set[str], 
        app_node_id: str
    ) -> Dict[str, Any]:
        """
        Analyze the structure of the extracted path.
        
        Args:
            graph: NetworkX graph
            path_nodes: Nodes in the path
            app_node_id: Application node ID
            
        Returns:
            Path analysis data
        """
        # Find basic concepts (nodes with no predecessors in subgraph)
        basic_concepts = []
        core_technologies = []
        
        for node_id in path_nodes:
            node_data = graph.nodes[node_id]
            node_type = node_data.get('node_type')
            
            if node_type == 'basic_concept':
                basic_concepts.append({
                    'id': node_id,
                    'label': node_data.get('label', ''),
                    'summary': node_data.get('summary', '')
                })
            elif node_type == 'core_technology':
                core_technologies.append({
                    'id': node_id,
                    'label': node_data.get('label', ''),
                    'summary': node_data.get('summary', '')
                })
        
        # Find logical path from concepts to application
        logical_path = self._find_logical_path(graph, path_nodes, app_node_id)
        
        return {
            'basic_concepts': basic_concepts,
            'core_technologies': core_technologies,
            'logical_path': logical_path,
            'key_bottleneck': self._identify_key_bottleneck(graph, path_nodes, app_node_id)
        }
    
    def _find_logical_path(
        self, 
        graph: nx.DiGraph, 
        path_nodes: Set[str], 
        app_node_id: str
    ) -> List[Dict[str, str]]:
        """Find the main logical path from concepts to application."""
        # Simple implementation: find shortest path from any basic concept to application
        basic_concepts = [
            node_id for node_id in path_nodes 
            if graph.nodes[node_id].get('node_type') == 'basic_concept'
        ]
        
        if not basic_concepts:
            return []
        
        # Find shortest path
        shortest_path = None
        min_length = float('inf')
        
        for concept_id in basic_concepts:
            try:
                path = nx.shortest_path(graph, concept_id, app_node_id)
                if len(path) < min_length:
                    min_length = len(path)
                    shortest_path = path
            except nx.NetworkXNoPath:
                continue
        
        if not shortest_path:
            return []
        
        # Convert to structured format
        logical_path = []
        for node_id in shortest_path:
            node_data = graph.nodes[node_id]
            logical_path.append({
                'id': node_id,
                'label': node_data.get('label', ''),
                'type': node_data.get('node_type', ''),
                'summary': node_data.get('summary', '')
            })
        
        return logical_path
    
    def _identify_key_bottleneck(
        self, 
        graph: nx.DiGraph, 
        path_nodes: Set[str], 
        app_node_id: str
    ) -> str:
        """Identify the key technical bottleneck for the application."""
        app_node = graph.nodes[app_node_id]
        
        # Simple heuristic: use application summary or generate from context
        summary = app_node.get('summary', '')
        if summary:
            # Extract key challenge from summary
            challenge_keywords = ['挑战', '难点', '瓶颈', '问题', '限制']
            for keyword in challenge_keywords:
                if keyword in summary:
                    # Extract sentence containing the keyword
                    sentences = summary.split('。')
                    for sentence in sentences:
                        if keyword in sentence:
                            return sentence.strip()
        
        # Fallback: generic bottleneck description
        return f"实现{app_node.get('label', '该应用')}的关键技术挑战"
    
    def _count_node_types(self, nodes: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count nodes by type."""
        counts = {}
        for node in nodes:
            node_type = node.get('node_type', 'unknown')
            counts[node_type] = counts.get(node_type, 0) + 1
        return counts
    
    def _calculate_max_depth(
        self, 
        graph: nx.DiGraph, 
        path_nodes: Set[str], 
        app_node_id: str
    ) -> int:
        """Calculate maximum depth from basic concepts to application."""
        basic_concepts = [
            node_id for node_id in path_nodes 
            if graph.nodes[node_id].get('node_type') == 'basic_concept'
        ]
        
        if not basic_concepts:
            return 0
        
        max_depth = 0
        for concept_id in basic_concepts:
            try:
                path_length = nx.shortest_path_length(graph, concept_id, app_node_id)
                max_depth = max(max_depth, path_length)
            except nx.NetworkXNoPath:
                continue
        
        return max_depth
    
    async def _save_subgraphs(self, subgraphs: List[Dict[str, Any]]) -> None:
        """Save extracted subgraphs to disk."""
        output_dir = Path(self.config.get("data.subgraphs_path"))
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save individual subgraphs
        for i, subgraph in enumerate(subgraphs):
            app_id = subgraph['application_node_id']
            filename = f"subgraph_{app_id}.json"
            filepath = output_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(subgraph, f, ensure_ascii=False, indent=2)
        
        # Save summary
        summary = {
            'total_subgraphs': len(subgraphs),
            'applications': [
                {
                    'id': sg['application_node_id'],
                    'label': sg['application_label'],
                    'nodes': sg['statistics']['total_nodes'],
                    'edges': sg['statistics']['total_edges']
                }
                for sg in subgraphs
            ]
        }
        
        summary_file = output_dir / "subgraphs_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Saved {len(subgraphs)} subgraphs to {output_dir}")
