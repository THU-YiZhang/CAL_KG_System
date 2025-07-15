"""
Knowledge Enhancer for CT-MA System.

Enhances knowledge graph nodes with external knowledge using RAG.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from pathlib import Path

from ..utils.logger import LoggerMixin
from ..utils.config_manager import ConfigManager
from .vector_store import VectorStore
from .retriever import Retriever


class KnowledgeEnhancer(LoggerMixin):
    """Enhances knowledge graph nodes with external knowledge."""
    
    def __init__(self, config: ConfigManager, vector_store: VectorStore):
        """
        Initialize Knowledge Enhancer.
        
        Args:
            config: Configuration manager instance
            vector_store: Vector store instance
        """
        self.config = config
        self.vector_store = vector_store
        self.retriever = Retriever(config, vector_store)
        
        # Configuration
        self.max_contexts_per_node = config.get("rag.knowledge_enhancement.max_contexts_per_node", 5)
        self.context_window = config.get("rag.knowledge_enhancement.context_window", 2048)
        
    async def initialize(self) -> None:
        """Initialize the knowledge enhancer."""
        self.logger.info("Initializing knowledge enhancer...")
        
        # Load knowledge base if not already loaded
        kb_path = self.config.get("data.knowledge_base_path")
        if kb_path and Path(kb_path).exists():
            await self.vector_store.load_knowledge_base(kb_path)
        
        self.logger.info("Knowledge enhancer initialized")
    
    async def enhance_subgraph(self, subgraph: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance a subgraph with external knowledge.
        
        Args:
            subgraph: Subgraph data
            
        Returns:
            Enhanced subgraph with additional knowledge
        """
        self.logger.info(f"Enhancing subgraph for application: {subgraph.get('application_label', 'unknown')}")
        
        enhanced_subgraph = subgraph.copy()
        enhanced_nodes = []
        
        for node in subgraph['nodes']:
            enhanced_node = await self.enhance_node(node)
            enhanced_nodes.append(enhanced_node)
        
        enhanced_subgraph['nodes'] = enhanced_nodes
        enhanced_subgraph['enhancement_summary'] = self._generate_enhancement_summary(enhanced_nodes)
        
        return enhanced_subgraph
    
    async def enhance_node(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance a single node with external knowledge.
        
        Args:
            node_data: Node data from knowledge graph
            
        Returns:
            Enhanced node data
        """
        node_type = node_data.get('node_type', '')
        
        # Skip enhancement for certain node types if configured
        if not self._should_enhance_node_type(node_type):
            return node_data
        
        enhanced_node = node_data.copy()
        
        try:
            # Retrieve relevant knowledge
            knowledge_items = await self.retriever.retrieve_for_node(node_data)
            
            # Process and structure the knowledge
            structured_knowledge = self._structure_knowledge(knowledge_items)
            
            # Add to node
            enhanced_node['external_knowledge'] = structured_knowledge
            enhanced_node['enhancement_metadata'] = {
                'enhanced_at': self._get_timestamp(),
                'knowledge_sources': len(knowledge_items),
                'enhancement_strategies': self._get_applied_strategies(knowledge_items)
            }
            
            self.logger.debug(f"Enhanced node {node_data.get('id', 'unknown')} with {len(knowledge_items)} knowledge items")
            
        except Exception as e:
            self.logger.warning(f"Failed to enhance node {node_data.get('id', 'unknown')}: {e}")
            enhanced_node['external_knowledge'] = {}
            enhanced_node['enhancement_metadata'] = {
                'enhanced_at': self._get_timestamp(),
                'error': str(e)
            }
        
        return enhanced_node
    
    def _should_enhance_node_type(self, node_type: str) -> bool:
        """Check if a node type should be enhanced."""
        enhance_types = {
            'basic_concept': self.config.get("rag.knowledge_enhancement.enhance_basic_concepts", True),
            'core_technology': self.config.get("rag.knowledge_enhancement.enhance_core_technologies", True),
            'circuit_application': self.config.get("rag.knowledge_enhancement.enhance_circuit_applications", True)
        }
        
        return enhance_types.get(node_type, False)
    
    def _structure_knowledge(self, knowledge_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Structure retrieved knowledge into categories."""
        structured = {
            'definitions': [],
            'formulas': [],
            'examples': [],
            'related_concepts': [],
            'technical_details': []
        }
        
        for item in knowledge_items:
            retrieval_type = item.get('retrieval_type', 'general')
            content = item['content']
            
            knowledge_entry = {
                'content': content,
                'source': item.get('metadata', {}).get('source', 'unknown'),
                'relevance_score': item.get('score', 0.0),
                'evidence_id': item.get('id', '')
            }
            
            if retrieval_type == 'definition':
                structured['definitions'].append(knowledge_entry)
            elif retrieval_type == 'formula':
                structured['formulas'].append(knowledge_entry)
            elif retrieval_type == 'example':
                structured['examples'].append(knowledge_entry)
            elif retrieval_type == 'related_concept':
                structured['related_concepts'].append(knowledge_entry)
            else:
                structured['technical_details'].append(knowledge_entry)
        
        # Limit items per category
        max_per_category = 3
        for category in structured:
            structured[category] = structured[category][:max_per_category]
        
        return structured
    
    async def get_reasoning_evidence(
        self, 
        subgraph: Dict[str, Any], 
        reasoning_step: str
    ) -> List[Dict[str, Any]]:
        """
        Get evidence for a specific reasoning step.
        
        Args:
            subgraph: Enhanced subgraph
            reasoning_step: Description of the reasoning step
            
        Returns:
            List of evidence items
        """
        # Extract key concepts from the reasoning step
        key_concepts = self._extract_concepts_from_reasoning(reasoning_step, subgraph)
        
        # Retrieve evidence
        evidence = await self.retriever.retrieve_evidence_for_reasoning(
            reasoning_step, key_concepts
        )
        
        return evidence
    
    def _extract_concepts_from_reasoning(
        self, 
        reasoning_step: str, 
        subgraph: Dict[str, Any]
    ) -> List[str]:
        """Extract key concepts mentioned in reasoning step."""
        concepts = []
        
        # Get all node labels from subgraph
        node_labels = [node.get('label', '') for node in subgraph.get('nodes', [])]
        
        # Find which labels are mentioned in the reasoning step
        for label in node_labels:
            if label and label in reasoning_step:
                concepts.append(label)
        
        # Add application label
        app_label = subgraph.get('application_label', '')
        if app_label and app_label not in concepts:
            concepts.append(app_label)
        
        return concepts
    
    def build_evidence_package(self, enhanced_subgraph: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build a comprehensive evidence package for the subgraph.
        
        Args:
            enhanced_subgraph: Enhanced subgraph data
            
        Returns:
            Evidence package for agent reasoning
        """
        evidence_package = {
            'subgraph_summary': {
                'application': enhanced_subgraph.get('application_label', ''),
                'total_nodes': len(enhanced_subgraph.get('nodes', [])),
                'key_bottleneck': enhanced_subgraph.get('path_analysis', {}).get('key_bottleneck', '')
            },
            'knowledge_evidence': {},
            'technical_evidence': {},
            'formula_evidence': {},
            'example_evidence': {}
        }
        
        # Collect evidence from all enhanced nodes
        for node in enhanced_subgraph.get('nodes', []):
            node_id = node.get('id', '')
            node_label = node.get('label', '')
            external_knowledge = node.get('external_knowledge', {})
            
            # Organize evidence by type
            if external_knowledge.get('definitions'):
                evidence_package['knowledge_evidence'][node_label] = external_knowledge['definitions']
            
            if external_knowledge.get('formulas'):
                evidence_package['formula_evidence'][node_label] = external_knowledge['formulas']
            
            if external_knowledge.get('examples'):
                evidence_package['example_evidence'][node_label] = external_knowledge['examples']
            
            if external_knowledge.get('technical_details'):
                evidence_package['technical_evidence'][node_label] = external_knowledge['technical_details']
        
        return evidence_package
    
    def format_evidence_for_agent(self, evidence_package: Dict[str, Any]) -> str:
        """
        Format evidence package for agent consumption.
        
        Args:
            evidence_package: Evidence package
            
        Returns:
            Formatted evidence string
        """
        formatted_evidence = []
        
        # Add knowledge evidence
        for concept, definitions in evidence_package.get('knowledge_evidence', {}).items():
            if definitions:
                formatted_evidence.append(f"【{concept}定义】")
                for i, def_item in enumerate(definitions[:2], 1):
                    formatted_evidence.append(f"定义{i}: {def_item['content'][:200]}...")
        
        # Add formula evidence
        for concept, formulas in evidence_package.get('formula_evidence', {}).items():
            if formulas:
                formatted_evidence.append(f"【{concept}公式】")
                for i, formula_item in enumerate(formulas[:2], 1):
                    formatted_evidence.append(f"公式{i}: {formula_item['content'][:150]}...")
        
        # Add technical evidence
        for concept, tech_details in evidence_package.get('technical_evidence', {}).items():
            if tech_details:
                formatted_evidence.append(f"【{concept}技术细节】")
                for i, tech_item in enumerate(tech_details[:1], 1):
                    formatted_evidence.append(f"技术{i}: {tech_item['content'][:200]}...")
        
        return "\n".join(formatted_evidence)
    
    def _generate_enhancement_summary(self, enhanced_nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary of enhancement process."""
        total_nodes = len(enhanced_nodes)
        enhanced_count = sum(1 for node in enhanced_nodes if 'external_knowledge' in node)
        
        knowledge_stats = {
            'definitions': 0,
            'formulas': 0,
            'examples': 0,
            'technical_details': 0
        }
        
        for node in enhanced_nodes:
            ext_knowledge = node.get('external_knowledge', {})
            for category in knowledge_stats:
                knowledge_stats[category] += len(ext_knowledge.get(category, []))
        
        return {
            'total_nodes': total_nodes,
            'enhanced_nodes': enhanced_count,
            'enhancement_rate': enhanced_count / total_nodes if total_nodes > 0 else 0,
            'knowledge_statistics': knowledge_stats,
            'timestamp': self._get_timestamp()
        }
    
    def _get_applied_strategies(self, knowledge_items: List[Dict[str, Any]]) -> List[str]:
        """Get list of applied retrieval strategies."""
        strategies = set()
        for item in knowledge_items:
            if 'retrieval_type' in item:
                strategies.add(item['retrieval_type'])
        return list(strategies)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
