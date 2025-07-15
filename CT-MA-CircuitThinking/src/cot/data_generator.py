"""
CoT Data Generator for CT-MA System.

Orchestrates the generation of Chain-of-Thought data using the multi-agent system.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from ..utils.logger import LoggerMixin
from ..utils.config_manager import ConfigManager
from ..utils.metrics import MetricsCollector
from ..agents.coordinator import Coordinator
from ..rag.knowledge_enhancer import KnowledgeEnhancer
from .format_validator import FormatValidator
from .quality_checker import QualityChecker


class COTDataGenerator(LoggerMixin):
    """Main CoT data generator orchestrating the entire pipeline."""
    
    def __init__(
        self, 
        config: ConfigManager, 
        coordinator: Coordinator, 
        knowledge_enhancer: KnowledgeEnhancer
    ):
        """
        Initialize CoT Data Generator.
        
        Args:
            config: Configuration manager instance
            coordinator: Agent coordinator
            knowledge_enhancer: Knowledge enhancer for RAG
        """
        self.config = config
        self.coordinator = coordinator
        self.knowledge_enhancer = knowledge_enhancer
        self.format_validator = FormatValidator(config)
        self.quality_checker = QualityChecker(config)
        self.metrics_collector = MetricsCollector(config)
        
        # Configuration
        self.batch_size = config.get("processing.batch_size", 10)
        self.save_intermediate = config.get("processing.save_intermediate", True)
        
    async def generate_batch(self, subgraphs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate CoT data for a batch of subgraphs.
        
        Args:
            subgraphs: List of subgraph data
            
        Returns:
            List of generated CoT data
        """
        self.logger.info(f"Starting CoT generation for {len(subgraphs)} subgraphs")
        self.metrics_collector.start_timer("batch_generation")
        
        try:
            # Step 1: Enhance subgraphs with external knowledge
            enhanced_subgraphs = await self._enhance_subgraphs_batch(subgraphs)
            
            # Step 2: Generate CoT data using agents
            cot_data = await self._generate_cot_batch(enhanced_subgraphs)
            
            # Step 3: Validate and filter results
            validated_data = await self._validate_and_filter_batch(cot_data)
            
            # Step 4: Save results
            if self.save_intermediate:
                await self._save_batch_results(validated_data)
            
            generation_time = self.metrics_collector.end_timer("batch_generation")
            self.logger.info(f"Batch CoT generation completed in {generation_time:.2f}s")
            
            return validated_data
            
        except Exception as e:
            self.logger.error(f"Batch CoT generation failed: {e}")
            raise
    
    async def _enhance_subgraphs_batch(
        self, 
        subgraphs: List[Dict[str, Any]]
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """Enhance subgraphs with external knowledge."""
        self.logger.info("Enhancing subgraphs with external knowledge...")
        self.metrics_collector.start_timer("knowledge_enhancement")
        
        enhanced_pairs = []
        
        for i, subgraph in enumerate(subgraphs, 1):
            try:
                app_label = subgraph.get('application_label', f'unknown_{i}')
                self.logger.debug(f"Enhancing subgraph {i}/{len(subgraphs)}: {app_label}")
                
                # Enhance subgraph
                enhanced_subgraph = await self.knowledge_enhancer.enhance_subgraph(subgraph)
                
                # Build evidence package
                evidence_package = self.knowledge_enhancer.build_evidence_package(enhanced_subgraph)
                
                enhanced_pairs.append((enhanced_subgraph, evidence_package))
                
                # Record metrics
                self.metrics_collector.record_subgraph_metrics(enhanced_subgraph)
                
            except Exception as e:
                self.logger.warning(f"Failed to enhance subgraph {i}: {e}")
                # Use original subgraph with empty evidence
                enhanced_pairs.append((subgraph, {}))
        
        enhancement_time = self.metrics_collector.end_timer("knowledge_enhancement")
        self.logger.info(f"Knowledge enhancement completed in {enhancement_time:.2f}s")
        
        return enhanced_pairs
    
    async def _generate_cot_batch(
        self, 
        enhanced_pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Generate CoT data using the multi-agent system."""
        self.logger.info("Generating CoT data using multi-agent system...")
        self.metrics_collector.start_timer("cot_generation")
        
        # Process in batches to manage memory and API limits
        all_cot_data = []
        
        for i in range(0, len(enhanced_pairs), self.batch_size):
            batch = enhanced_pairs[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (len(enhanced_pairs) + self.batch_size - 1) // self.batch_size
            
            self.logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} items)")
            
            # Generate CoT for this batch
            batch_results = await self.coordinator.generate_batch_cot(batch)
            all_cot_data.extend(batch_results)
            
            # Record metrics for each item
            for cot_item in batch_results:
                if 'error' not in cot_item:
                    self.metrics_collector.record_cot_metrics(cot_item)
        
        generation_time = self.metrics_collector.end_timer("cot_generation")
        self.logger.info(f"CoT generation completed in {generation_time:.2f}s")
        
        return all_cot_data
    
    async def _validate_and_filter_batch(
        self, 
        cot_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Validate and filter CoT data."""
        self.logger.info("Validating and filtering CoT data...")
        self.metrics_collector.start_timer("validation")
        
        validated_data = []
        validation_stats = {
            'total': len(cot_data),
            'format_valid': 0,
            'quality_passed': 0,
            'final_valid': 0
        }
        
        for cot_item in cot_data:
            # Skip error entries
            if 'error' in cot_item:
                continue
            
            try:
                # Format validation
                format_result = self.format_validator.validate(cot_item)
                if format_result['is_valid']:
                    validation_stats['format_valid'] += 1
                    
                    # Quality check
                    quality_result = self.quality_checker.check_quality(cot_item)
                    if quality_result['overall_score'] >= 0.7:  # Quality threshold
                        validation_stats['quality_passed'] += 1
                        
                        # Add validation metadata
                        cot_item['validation'] = {
                            'format_validation': format_result,
                            'quality_assessment': quality_result,
                            'validated_at': datetime.now().isoformat()
                        }
                        
                        validated_data.append(cot_item)
                        validation_stats['final_valid'] += 1
                    else:
                        self.logger.debug(f"Quality check failed for {cot_item.get('data_id', 'unknown')}")
                else:
                    self.logger.debug(f"Format validation failed for {cot_item.get('data_id', 'unknown')}")
                    
            except Exception as e:
                self.logger.warning(f"Validation failed for {cot_item.get('data_id', 'unknown')}: {e}")
        
        validation_time = self.metrics_collector.end_timer("validation")
        
        self.logger.info(f"Validation completed in {validation_time:.2f}s")
        self.logger.info(f"Validation stats: {validation_stats}")
        
        return validated_data
    
    async def _save_batch_results(self, cot_data: List[Dict[str, Any]]) -> None:
        """Save batch results to disk."""
        if not cot_data:
            self.logger.warning("No CoT data to save")
            return
        
        output_dir = Path(self.config.get("data.cot_datasets_path"))
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save main dataset
        dataset_file = output_dir / f"cot_dataset_{timestamp}.json"
        with open(dataset_file, 'w', encoding='utf-8') as f:
            json.dump(cot_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Saved {len(cot_data)} CoT items to {dataset_file}")
        
        # Save metadata
        metadata = {
            'generation_timestamp': timestamp,
            'total_items': len(cot_data),
            'generation_statistics': self.coordinator.get_generation_statistics(cot_data),
            'metrics_summary': self.metrics_collector.get_summary_stats()
        }
        
        metadata_file = output_dir / f"metadata_{timestamp}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        # Save metrics
        metrics_file = output_dir / f"metrics_{timestamp}.json"
        self.metrics_collector.save_metrics(str(metrics_file))
    
    async def generate_single(
        self, 
        subgraph: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate CoT data for a single subgraph.
        
        Args:
            subgraph: Subgraph data
            
        Returns:
            Generated CoT data or None if failed
        """
        try:
            # Enhance subgraph
            enhanced_subgraph = await self.knowledge_enhancer.enhance_subgraph(subgraph)
            evidence_package = self.knowledge_enhancer.build_evidence_package(enhanced_subgraph)
            
            # Generate CoT
            cot_data = await self.coordinator.generate_cot(enhanced_subgraph, evidence_package)
            
            # Validate
            format_result = self.format_validator.validate(cot_data)
            if not format_result['is_valid']:
                self.logger.warning(f"Format validation failed for {subgraph.get('application_label', 'unknown')}")
                return None
            
            quality_result = self.quality_checker.check_quality(cot_data)
            if quality_result['overall_score'] < 0.7:
                self.logger.warning(f"Quality check failed for {subgraph.get('application_label', 'unknown')}")
                return None
            
            # Add validation metadata
            cot_data['validation'] = {
                'format_validation': format_result,
                'quality_assessment': quality_result,
                'validated_at': datetime.now().isoformat()
            }
            
            return cot_data
            
        except Exception as e:
            self.logger.error(f"Single CoT generation failed: {e}")
            return None
    
    def get_generation_report(self, cot_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive generation report."""
        successful_items = [item for item in cot_data if 'error' not in item]
        
        if not successful_items:
            return {
                'summary': 'No successful CoT items generated',
                'statistics': {'total': len(cot_data), 'successful': 0}
            }
        
        # Calculate statistics
        total_logic_length = sum(len(item.get('logic', '')) for item in successful_items)
        total_think_length = sum(len(item.get('think', '')) for item in successful_items)
        total_answer_length = sum(len(item.get('answer', '')) for item in successful_items)
        
        avg_logic = total_logic_length / len(successful_items)
        avg_think = total_think_length / len(successful_items)
        avg_answer = total_answer_length / len(successful_items)
        
        # Quality distribution
        quality_scores = []
        for item in successful_items:
            validation = item.get('validation', {})
            quality_assessment = validation.get('quality_assessment', {})
            overall_score = quality_assessment.get('overall_score', 0)
            quality_scores.append(overall_score)
        
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        return {
            'summary': f"Generated {len(successful_items)} high-quality CoT items",
            'statistics': {
                'total_items': len(cot_data),
                'successful_items': len(successful_items),
                'success_rate': len(successful_items) / len(cot_data),
                'average_lengths': {
                    'logic': avg_logic,
                    'think': avg_think,
                    'answer': avg_answer
                },
                'average_quality_score': avg_quality
            },
            'metrics': self.metrics_collector.get_performance_report()
        }
