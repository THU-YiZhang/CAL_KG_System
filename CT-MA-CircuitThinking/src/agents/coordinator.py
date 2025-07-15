"""
Coordinator for CT-MA System.

Orchestrates the collaboration between Logic, Think, and Answer agents.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple

from .logic_agent import LogicAgent
from .think_agent import ThinkAgent
from .answer_agent import AnswerAgent
from ..utils.logger import LoggerMixin
from ..utils.config_manager import ConfigManager


class Coordinator(LoggerMixin):
    """Coordinates the multi-agent workflow for CoT generation."""
    
    def __init__(self, config: ConfigManager):
        """
        Initialize Coordinator.
        
        Args:
            config: Configuration manager instance
        """
        self.config = config
        self.logic_agent = LogicAgent(config)
        self.think_agent = ThinkAgent(config)
        self.answer_agent = AnswerAgent(config)
        
        # Validation rules from config
        self.validation_rules = config.get("agents.coordinator.validation_rules", {})
        
    async def initialize(self) -> None:
        """Initialize all agents."""
        self.logger.info("Initializing coordinator and agents...")
        
        await self.logic_agent.initialize()
        await self.think_agent.initialize()
        await self.answer_agent.initialize()
        
        self.logger.info("All agents initialized successfully")
    
    async def generate_cot(
        self, 
        subgraph: Dict[str, Any], 
        evidence_package: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate complete CoT data using multi-agent collaboration.
        
        Args:
            subgraph: Enhanced subgraph data
            evidence_package: RAG evidence package
            
        Returns:
            Complete CoT data with logic, think, and answer sections
        """
        start_time = time.time()
        app_label = subgraph.get('application_label', 'unknown')
        
        self.logger.info(f"Starting CoT generation for: {app_label}")
        
        try:
            # Step 1: Logic Analysis
            self.logger.info("Step 1: Logic analysis...")
            logic_result = await self.logic_agent.execute({'subgraph': subgraph})
            
            # Validate logic output
            if not self._validate_logic_output(logic_result):
                raise ValueError("Logic output validation failed")
            
            # Step 2: Detailed Thinking
            self.logger.info("Step 2: Detailed thinking...")
            think_input = {
                'logic': logic_result['logic'],
                'evidence_package': evidence_package,
                'subgraph': subgraph
            }
            think_result = await self.think_agent.execute(think_input)
            
            # Validate think output
            if not self._validate_think_output(think_result):
                raise ValueError("Think output validation failed")
            
            # Step 3: Answer Synthesis
            self.logger.info("Step 3: Answer synthesis...")
            answer_input = {
                'think': think_result['think'],
                'logic': logic_result['logic'],
                'subgraph': subgraph
            }
            answer_result = await self.answer_agent.execute(answer_input)
            
            # Validate answer output
            if not self._validate_answer_output(answer_result):
                raise ValueError("Answer output validation failed")
            
            # Combine results
            cot_data = self._combine_results(
                logic_result, think_result, answer_result, subgraph
            )
            
            # Final validation
            if not self._validate_final_cot(cot_data):
                raise ValueError("Final CoT validation failed")
            
            execution_time = time.time() - start_time
            self.logger.info(f"CoT generation completed for {app_label} in {execution_time:.2f}s")
            
            return cot_data
            
        except Exception as e:
            self.logger.error(f"CoT generation failed for {app_label}: {e}")
            raise
    
    def _validate_logic_output(self, logic_result: Dict[str, Any]) -> bool:
        """Validate logic agent output."""
        format_rules = self.validation_rules.get('format_check', [])
        
        # Check required keys
        if 'logic' not in logic_result:
            self.logger.error("Logic result missing 'logic' key")
            return False
        
        logic_content = logic_result['logic']
        
        # Check required sections
        required_sections = ['目标应用', '关键瓶颈', '支撑路径', '因果链']
        for section in required_sections:
            if f'【{section}】' not in logic_content:
                self.logger.error(f"Logic missing required section: {section}")
                return False
        
        # Check minimum length
        min_length = self.config.get("quality.min_logic_length", 100)
        if len(logic_content) < min_length:
            self.logger.error(f"Logic content too short: {len(logic_content)} < {min_length}")
            return False
        
        return True
    
    def _validate_think_output(self, think_result: Dict[str, Any]) -> bool:
        """Validate think agent output."""
        if 'think' not in think_result:
            self.logger.error("Think result missing 'think' key")
            return False
        
        think_content = think_result['think']
        
        # Check for reasoning steps
        step_patterns = ['第一步', '第二步', '第三步', '第四步']
        step_count = sum(1 for pattern in step_patterns if pattern in think_content)
        
        if step_count < 3:
            self.logger.error(f"Think content has insufficient reasoning steps: {step_count}")
            return False
        
        # Check for RAG references
        rag_count = think_result.get('rag_references_count', 0)
        if rag_count < 3:
            self.logger.error(f"Think content has insufficient RAG references: {rag_count}")
            return False
        
        # Check minimum length
        min_length = self.config.get("quality.min_think_length", 500)
        if len(think_content) < min_length:
            self.logger.error(f"Think content too short: {len(think_content)} < {min_length}")
            return False
        
        return True
    
    def _validate_answer_output(self, answer_result: Dict[str, Any]) -> bool:
        """Validate answer agent output."""
        if 'answer' not in answer_result:
            self.logger.error("Answer result missing 'answer' key")
            return False
        
        answer_content = answer_result['answer']
        
        # Check minimum length
        min_length = self.config.get("quality.min_answer_length", 100)
        if len(answer_content) < min_length:
            self.logger.error(f"Answer content too short: {len(answer_content)} < {min_length}")
            return False
        
        # Check for key components
        required_components = ['原理', '技术', '解决']
        component_count = sum(1 for comp in required_components if comp in answer_content)
        
        if component_count < 2:
            self.logger.error(f"Answer missing key components: {component_count}/3")
            return False
        
        return True
    
    def _validate_final_cot(self, cot_data: Dict[str, Any]) -> bool:
        """Validate final CoT data."""
        required_sections = self.config.get("quality.required_sections", ["logic", "think", "answer"])
        
        for section in required_sections:
            if section not in cot_data or not cot_data[section]:
                self.logger.error(f"Final CoT missing section: {section}")
                return False
        
        # Check total length
        total_length = sum(len(cot_data.get(section, '')) for section in required_sections)
        max_length = self.config.get("quality.max_total_length", 5000)
        
        if total_length > max_length:
            self.logger.error(f"CoT total length too long: {total_length} > {max_length}")
            return False
        
        return True
    
    def _combine_results(
        self, 
        logic_result: Dict[str, Any], 
        think_result: Dict[str, Any], 
        answer_result: Dict[str, Any],
        subgraph: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Combine agent results into final CoT data."""
        from datetime import datetime
        
        cot_data = {
            'data_id': f"cot_{subgraph.get('application_node_id', 'unknown')}",
            'source_application': subgraph.get('application_label', ''),
            'application_node_id': subgraph.get('application_node_id', ''),
            'logic': logic_result['logic'],
            'think': think_result['think'],
            'answer': answer_result['answer'],
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'subgraph_nodes': len(subgraph.get('nodes', [])),
                'subgraph_edges': len(subgraph.get('edges', [])),
                'logic_execution_time': logic_result.get('execution_time', 0),
                'think_execution_time': think_result.get('execution_time', 0),
                'answer_execution_time': answer_result.get('execution_time', 0),
                'rag_references_count': think_result.get('rag_references_count', 0)
            },
            'quality_metrics': {
                'logic_length': len(logic_result['logic']),
                'think_length': len(think_result['think']),
                'answer_length': len(answer_result['answer']),
                'total_length': len(logic_result['logic']) + len(think_result['think']) + len(answer_result['answer'])
            }
        }
        
        return cot_data
    
    async def generate_batch_cot(
        self, 
        subgraphs_with_evidence: List[Tuple[Dict[str, Any], Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Generate CoT data for multiple subgraphs.
        
        Args:
            subgraphs_with_evidence: List of (subgraph, evidence_package) tuples
            
        Returns:
            List of generated CoT data
        """
        self.logger.info(f"Starting batch CoT generation for {len(subgraphs_with_evidence)} subgraphs")
        
        cot_results = []
        successful = 0
        failed = 0
        
        for i, (subgraph, evidence_package) in enumerate(subgraphs_with_evidence, 1):
            app_label = subgraph.get('application_label', f'unknown_{i}')
            
            try:
                self.logger.info(f"Processing {i}/{len(subgraphs_with_evidence)}: {app_label}")
                
                cot_data = await self.generate_cot(subgraph, evidence_package)
                cot_results.append(cot_data)
                successful += 1
                
            except Exception as e:
                self.logger.error(f"Failed to generate CoT for {app_label}: {e}")
                failed += 1
                
                # Add error entry
                error_entry = {
                    'data_id': f"error_{subgraph.get('application_node_id', f'unknown_{i}')}",
                    'source_application': app_label,
                    'error': str(e),
                    'metadata': {
                        'generated_at': time.time(),
                        'status': 'failed'
                    }
                }
                cot_results.append(error_entry)
        
        self.logger.info(f"Batch CoT generation completed: {successful} successful, {failed} failed")
        
        return cot_results
    
    def get_generation_statistics(self, cot_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about generated CoT data."""
        total_items = len(cot_results)
        successful_items = [item for item in cot_results if 'error' not in item]
        failed_items = [item for item in cot_results if 'error' in item]
        
        if not successful_items:
            return {
                'total_items': total_items,
                'successful_items': 0,
                'failed_items': len(failed_items),
                'success_rate': 0.0
            }
        
        # Calculate averages for successful items
        avg_logic_length = sum(len(item.get('logic', '')) for item in successful_items) / len(successful_items)
        avg_think_length = sum(len(item.get('think', '')) for item in successful_items) / len(successful_items)
        avg_answer_length = sum(len(item.get('answer', '')) for item in successful_items) / len(successful_items)
        
        return {
            'total_items': total_items,
            'successful_items': len(successful_items),
            'failed_items': len(failed_items),
            'success_rate': len(successful_items) / total_items,
            'average_lengths': {
                'logic': avg_logic_length,
                'think': avg_think_length,
                'answer': avg_answer_length
            },
            'total_rag_references': sum(
                item.get('metadata', {}).get('rag_references_count', 0) 
                for item in successful_items
            )
        }
