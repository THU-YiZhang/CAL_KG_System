"""
Retriever for CT-MA System.

Advanced retrieval strategies for knowledge enhancement.
"""

import asyncio
import re
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict

from ..utils.logger import LoggerMixin
from ..utils.config_manager import ConfigManager
from .vector_store import VectorStore


class Retriever(LoggerMixin):
    """Advanced retriever with multiple search strategies."""
    
    def __init__(self, config: ConfigManager, vector_store: VectorStore):
        """
        Initialize Retriever.
        
        Args:
            config: Configuration manager instance
            vector_store: Vector store instance
        """
        self.config = config
        self.vector_store = vector_store
        
        # Configuration
        self.top_k = config.get("rag.retrieval.top_k", 10)
        self.score_threshold = config.get("rag.retrieval.score_threshold", 0.7)
        self.enable_reranking = config.get("rag.retrieval.enable_reranking", True)
        self.enable_query_expansion = config.get("rag.retrieval.enable_query_expansion", True)
        
    async def retrieve_for_node(
        self, 
        node_data: Dict[str, Any], 
        strategies: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant knowledge for a knowledge graph node.
        
        Args:
            node_data: Node data from knowledge graph
            strategies: List of retrieval strategies to use
            
        Returns:
            List of retrieved knowledge items
        """
        if not strategies:
            strategies = self.config.get("rag.knowledge_enhancement.strategies", 
                                       ["definition_lookup", "formula_extraction", "example_retrieval"])
        
        all_results = []
        
        for strategy in strategies:
            try:
                results = await self._apply_strategy(strategy, node_data)
                all_results.extend(results)
            except Exception as e:
                self.logger.warning(f"Strategy {strategy} failed for node {node_data.get('id', 'unknown')}: {e}")
        
        # Deduplicate and rank results
        final_results = self._deduplicate_and_rank(all_results)
        
        return final_results[:self.top_k]
    
    async def _apply_strategy(self, strategy: str, node_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply a specific retrieval strategy."""
        if strategy == "definition_lookup":
            return await self._definition_lookup(node_data)
        elif strategy == "formula_extraction":
            return await self._formula_extraction(node_data)
        elif strategy == "example_retrieval":
            return await self._example_retrieval(node_data)
        elif strategy == "related_concepts":
            return await self._related_concepts(node_data)
        else:
            self.logger.warning(f"Unknown strategy: {strategy}")
            return []
    
    async def _definition_lookup(self, node_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Look up definitions for the node."""
        label = node_data.get('label', '')
        node_type = node_data.get('node_type', '')
        
        # Build definition-focused query
        if node_type == 'basic_concept':
            query = f"{label} 定义 概念 原理"
        elif node_type == 'core_technology':
            query = f"{label} 技术 方法 原理"
        elif node_type == 'circuit_application':
            query = f"{label} 应用 电路 设计"
        else:
            query = f"{label} 定义"
        
        results = await self.vector_store.search(query, top_k=5)
        
        # Filter for definition-like content
        definition_results = []
        for result in results:
            content = result['content']
            if self._is_definition_content(content, label):
                result['retrieval_type'] = 'definition'
                definition_results.append(result)
        
        return definition_results
    
    async def _formula_extraction(self, node_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract formulas related to the node."""
        label = node_data.get('label', '')
        keywords = node_data.get('keywords', [])
        
        # Build formula-focused query
        query_terms = [label] + keywords + ['公式', '方程', '计算']
        query = " ".join(query_terms)
        
        results = await self.vector_store.search(query, top_k=8)
        
        # Filter for formula-containing content
        formula_results = []
        for result in results:
            content = result['content']
            if self._contains_formula(content):
                result['retrieval_type'] = 'formula'
                formula_results.append(result)
        
        return formula_results
    
    async def _example_retrieval(self, node_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Retrieve examples related to the node."""
        label = node_data.get('label', '')
        
        # Build example-focused query
        query = f"{label} 例子 示例 案例 实例"
        
        results = await self.vector_store.search(query, top_k=5)
        
        # Filter for example-like content
        example_results = []
        for result in results:
            content = result['content']
            if self._is_example_content(content):
                result['retrieval_type'] = 'example'
                example_results.append(result)
        
        return example_results
    
    async def _related_concepts(self, node_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Retrieve related concepts."""
        keywords = node_data.get('keywords', [])
        summary = node_data.get('summary', '')
        
        # Extract key terms from summary
        key_terms = self._extract_key_terms(summary)
        
        # Build query from keywords and key terms
        query_terms = keywords + key_terms
        query = " ".join(query_terms[:10])  # Limit query length
        
        results = await self.vector_store.search(query, top_k=6)
        
        for result in results:
            result['retrieval_type'] = 'related_concept'
        
        return results
    
    def _is_definition_content(self, content: str, term: str) -> bool:
        """Check if content contains definition-like information."""
        definition_patterns = [
            f"{term}是",
            f"{term}指",
            f"{term}定义为",
            "定义",
            "概念",
            "是指",
            "是一种"
        ]
        
        content_lower = content.lower()
        term_lower = term.lower()
        
        return any(pattern.lower() in content_lower for pattern in definition_patterns)
    
    def _contains_formula(self, content: str) -> bool:
        """Check if content contains mathematical formulas."""
        formula_indicators = [
            '=',
            '∫',
            '∑',
            '∂',
            '√',
            'log',
            'sin',
            'cos',
            'exp',
            '²',
            '³',
            'V_',
            'I_',
            'R_',
            'C_'
        ]
        
        # Check for mathematical symbols
        for indicator in formula_indicators:
            if indicator in content:
                return True
        
        # Check for equation-like patterns
        equation_patterns = [
            r'[A-Za-z_]\s*=\s*[A-Za-z0-9_\+\-\*/\(\)]+',
            r'\([A-Za-z0-9_\+\-\*/\s]+\)',
            r'[0-9]+\.[0-9]+',
            r'[A-Z][a-z]*_[0-9]+',
        ]
        
        for pattern in equation_patterns:
            if re.search(pattern, content):
                return True
        
        return False
    
    def _is_example_content(self, content: str) -> bool:
        """Check if content contains example-like information."""
        example_indicators = [
            '例如',
            '比如',
            '举例',
            '示例',
            '案例',
            '实例',
            '例子',
            '如图',
            '如下',
            '考虑'
        ]
        
        return any(indicator in content for indicator in example_indicators)
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from text."""
        if not text:
            return []
        
        # Simple key term extraction
        # Remove common words and extract meaningful terms
        common_words = {'的', '是', '在', '和', '与', '或', '但', '而', '等', '及', '以', '为', '由', '从', '到'}
        
        # Split by common delimiters
        terms = re.split(r'[，。、；：！？\s]+', text)
        
        # Filter and clean terms
        key_terms = []
        for term in terms:
            term = term.strip()
            if len(term) > 1 and term not in common_words:
                key_terms.append(term)
        
        return key_terms[:10]  # Return top 10 terms
    
    def _deduplicate_and_rank(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate and rank results."""
        # Group by content similarity
        unique_results = {}
        
        for result in results:
            content = result['content']
            content_hash = hash(content[:100])  # Use first 100 chars as hash
            
            if content_hash not in unique_results:
                unique_results[content_hash] = result
            else:
                # Keep the one with higher score
                if result['score'] > unique_results[content_hash]['score']:
                    unique_results[content_hash] = result
        
        # Convert back to list and sort by score
        final_results = list(unique_results.values())
        final_results.sort(key=lambda x: x['score'], reverse=True)
        
        # Filter by threshold
        filtered_results = [r for r in final_results if r['score'] >= self.score_threshold]
        
        return filtered_results
    
    async def retrieve_evidence_for_reasoning(
        self, 
        reasoning_context: str, 
        key_concepts: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Retrieve evidence for reasoning process.
        
        Args:
            reasoning_context: Context of the reasoning
            key_concepts: Key concepts involved in reasoning
            
        Returns:
            List of evidence items
        """
        evidence_results = []
        
        # Search for each key concept
        for concept in key_concepts:
            concept_query = f"{concept} {reasoning_context}"
            results = await self.vector_store.search(concept_query, top_k=3)
            
            for result in results:
                result['evidence_type'] = 'concept_support'
                result['related_concept'] = concept
                evidence_results.append(result)
        
        # Search for general reasoning context
        context_results = await self.vector_store.search(reasoning_context, top_k=5)
        for result in context_results:
            result['evidence_type'] = 'context_support'
            evidence_results.append(result)
        
        # Deduplicate and rank
        final_evidence = self._deduplicate_and_rank(evidence_results)
        
        return final_evidence[:8]  # Return top 8 evidence items
