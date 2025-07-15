"""
Knowledge Graph Loader for CT-MA System.

Loads and processes unified knowledge graphs from the CAL-KG system.
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
import networkx as nx

from ..utils.logger import LoggerMixin
from ..utils.config_manager import ConfigManager


class KGLoader(LoggerMixin):
    """Knowledge Graph Loader for processing CAL-KG output."""
    
    def __init__(self, config: ConfigManager):
        """
        Initialize KG Loader.
        
        Args:
            config: Configuration manager instance
        """
        self.config = config
        self.kg_data = None
        self.graph = None
        
    async def load_knowledge_graph(self, kg_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load unified knowledge graph from CAL-KG system.
        
        Args:
            kg_path: Path to knowledge graph file. If None, uses config.
            
        Returns:
            Loaded knowledge graph data
        """
        if not kg_path:
            kg_path = self.config.get("data.input_kg_path")
        
        kg_file = Path(kg_path)
        if not kg_file.exists():
            raise FileNotFoundError(f"Knowledge graph file not found: {kg_file}")
        
        self.logger.info(f"Loading knowledge graph from: {kg_file}")
        
        try:
            with open(kg_file, 'r', encoding='utf-8') as f:
                self.kg_data = json.load(f)
            
            # Validate structure
            self._validate_kg_structure()
            
            # Build NetworkX graph
            self.graph = self._build_networkx_graph()
            
            self.logger.info(f"Loaded KG with {len(self.kg_data['nodes'])} nodes and {len(self.kg_data['edges'])} edges")
            
            return self.kg_data
            
        except Exception as e:
            self.logger.error(f"Failed to load knowledge graph: {e}")
            raise
    
    def _validate_kg_structure(self) -> None:
        """Validate the structure of loaded knowledge graph."""
        required_keys = ['nodes', 'edges']
        for key in required_keys:
            if key not in self.kg_data:
                raise ValueError(f"Missing required key in KG data: {key}")
        
        # Validate nodes
        for node in self.kg_data['nodes']:
            required_node_keys = ['id', 'label', 'node_type']
            for key in required_node_keys:
                if key not in node:
                    raise ValueError(f"Missing required key in node: {key}")
        
        # Validate edges
        for edge in self.kg_data['edges']:
            required_edge_keys = ['source_id', 'target_id']
            for key in required_edge_keys:
                if key not in edge:
                    raise ValueError(f"Missing required key in edge: {key}")
    
    def _build_networkx_graph(self) -> nx.DiGraph:
        """Build NetworkX directed graph from KG data."""
        graph = nx.DiGraph()
        
        # Add nodes
        for node in self.kg_data['nodes']:
            graph.add_node(
                node['id'],
                **{k: v for k, v in node.items() if k != 'id'}
            )
        
        # Add edges
        for edge in self.kg_data['edges']:
            graph.add_edge(
                edge['source_id'],
                edge['target_id'],
                **{k: v for k, v in edge.items() if k not in ['source_id', 'target_id']}
            )
        
        return graph
    
    def get_nodes_by_type(self, node_type: str) -> List[Dict[str, Any]]:
        """
        Get all nodes of a specific type.
        
        Args:
            node_type: Type of nodes to retrieve
            
        Returns:
            List of nodes matching the type
        """
        if not self.kg_data:
            raise RuntimeError("Knowledge graph not loaded")
        
        return [node for node in self.kg_data['nodes'] if node['node_type'] == node_type]
    
    def get_node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get node by ID.
        
        Args:
            node_id: Node ID to search for
            
        Returns:
            Node data if found, None otherwise
        """
        if not self.kg_data:
            raise RuntimeError("Knowledge graph not loaded")
        
        for node in self.kg_data['nodes']:
            if node['id'] == node_id:
                return node
        return None
    
    def get_circuit_applications(self) -> List[Dict[str, Any]]:
        """
        Get all circuit application nodes.
        
        Returns:
            List of circuit application nodes
        """
        return self.get_nodes_by_type('circuit_application')
    
    def get_basic_concepts(self) -> List[Dict[str, Any]]:
        """
        Get all basic concept nodes.
        
        Returns:
            List of basic concept nodes
        """
        return self.get_nodes_by_type('basic_concept')
    
    def get_core_technologies(self) -> List[Dict[str, Any]]:
        """
        Get all core technology nodes.
        
        Returns:
            List of core technology nodes
        """
        return self.get_nodes_by_type('core_technology')
    
    def get_main_logic_nodes(self) -> List[Dict[str, Any]]:
        """
        Get all main logic nodes.
        
        Returns:
            List of main logic nodes
        """
        return self.get_nodes_by_type('main_logic')
    
    def get_predecessors(self, node_id: str) -> List[str]:
        """
        Get predecessor nodes of a given node.
        
        Args:
            node_id: Target node ID
            
        Returns:
            List of predecessor node IDs
        """
        if not self.graph:
            raise RuntimeError("Graph not built")
        
        return list(self.graph.predecessors(node_id))
    
    def get_successors(self, node_id: str) -> List[str]:
        """
        Get successor nodes of a given node.
        
        Args:
            node_id: Source node ID
            
        Returns:
            List of successor node IDs
        """
        if not self.graph:
            raise RuntimeError("Graph not built")
        
        return list(self.graph.successors(node_id))
    
    def get_node_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the knowledge graph.
        
        Returns:
            Dictionary containing various statistics
        """
        if not self.kg_data:
            raise RuntimeError("Knowledge graph not loaded")
        
        node_types = {}
        for node in self.kg_data['nodes']:
            node_type = node['node_type']
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        return {
            'total_nodes': len(self.kg_data['nodes']),
            'total_edges': len(self.kg_data['edges']),
            'node_types': node_types,
            'graph_density': nx.density(self.graph) if self.graph else 0,
            'is_connected': nx.is_weakly_connected(self.graph) if self.graph else False
        }
