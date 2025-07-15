#!/usr/bin/env python3
"""
Batch Generation Script

Runs batch CoT generation with monitoring and progress tracking.
"""

import sys
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.utils.config_manager import ConfigManager
from src.utils.logger import setup_logger, get_logger
from src.utils.metrics import MetricsCollector
from src.core.kg_loader import KGLoader
from src.core.subgraph_extractor import SubgraphExtractor
from src.rag.vector_store import VectorStore
from src.rag.knowledge_enhancer import KnowledgeEnhancer
from src.agents.coordinator import Coordinator
from src.cot.data_generator import COTDataGenerator


class BatchGenerator:
    """Batch CoT generation with progress monitoring."""
    
    def __init__(self, config_path: str = None):
        """Initialize batch generator."""
        self.config = ConfigManager(config_path)
        self.logger = get_logger(__name__)
        self.metrics = MetricsCollector(self.config)
        
        # Components
        self.kg_loader = None
        self.subgraph_extractor = None
        self.vector_store = None
        self.knowledge_enhancer = None
        self.coordinator = None
        self.cot_generator = None
    
    async def initialize(self):
        """Initialize all components."""
        self.logger.info("Initializing batch generator...")
        
        # Initialize components
        self.kg_loader = KGLoader(self.config)
        self.subgraph_extractor = SubgraphExtractor(self.config)
        self.vector_store = VectorStore(self.config)
        self.knowledge_enhancer = KnowledgeEnhancer(self.config, self.vector_store)
        self.coordinator = Coordinator(self.config)
        
        # Setup vector store and knowledge enhancer
        await self.vector_store.setup()
        await self.knowledge_enhancer.initialize()
        await self.coordinator.initialize()
        
        # Initialize CoT generator
        self.cot_generator = COTDataGenerator(
            self.config, self.coordinator, self.knowledge_enhancer
        )
        
        self.logger.info("Batch generator initialized")
    
    async def run_batch_generation(
        self, 
        max_subgraphs: int = None,
        batch_size: int = None
    ):
        """Run complete batch generation."""
        start_time = datetime.now()
        self.logger.info(f"Starting batch generation at {start_time}")
        
        try:
            # Step 1: Load knowledge graph
            self.logger.info("Step 1: Loading knowledge graph...")
            kg_data = await self.kg_loader.load_knowledge_graph()
            
            # Step 2: Extract subgraphs
            self.logger.info("Step 2: Extracting subgraphs...")
            all_subgraphs = await self.subgraph_extractor.extract_application_subgraphs(kg_data)
            
            # Limit subgraphs if specified
            if max_subgraphs and len(all_subgraphs) > max_subgraphs:
                all_subgraphs = all_subgraphs[:max_subgraphs]
                self.logger.info(f"Limited to {max_subgraphs} subgraphs")
            
            # Step 3: Generate CoT data in batches
            self.logger.info(f"Step 3: Generating CoT data for {len(all_subgraphs)} subgraphs...")
            
            if batch_size:
                self.cot_generator.batch_size = batch_size
            
            cot_data = await self.cot_generator.generate_batch(all_subgraphs)
            
            # Step 4: Generate final report
            self.logger.info("Step 4: Generating final report...")
            report = self.cot_generator.get_generation_report(cot_data)
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            self.logger.info(f"Batch generation completed in {duration}")
            
            # Print summary
            self._print_summary(report, duration)
            
            return cot_data
            
        except Exception as e:
            self.logger.error(f"Batch generation failed: {e}")
            raise
    
    def _print_summary(self, report: dict, duration):
        """Print generation summary."""
        stats = report.get('statistics', {})
        
        print("\n" + "="*60)
        print("BATCH GENERATION SUMMARY")
        print("="*60)
        print(f"Duration: {duration}")
        print(f"Total items: {stats.get('total_items', 0)}")
        print(f"Successful items: {stats.get('successful_items', 0)}")
        print(f"Success rate: {stats.get('success_rate', 0):.1%}")
        
        if 'average_lengths' in stats:
            avg_lengths = stats['average_lengths']
            print(f"\nAverage section lengths:")
            print(f"  Logic: {avg_lengths.get('logic', 0):.0f} chars")
            print(f"  Think: {avg_lengths.get('think', 0):.0f} chars")
            print(f"  Answer: {avg_lengths.get('answer', 0):.0f} chars")
        
        print(f"\nAverage quality score: {stats.get('average_quality_score', 0):.2f}")
        print("\nOutput files saved to: data/output/cot_datasets/")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="CT-MA Batch Generation")
    parser.add_argument("--config", type=str, help="Path to config file")
    parser.add_argument("--max-subgraphs", type=int, help="Maximum number of subgraphs to process")
    parser.add_argument("--batch-size", type=int, default=5, help="Batch size for processing")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logger(debug=args.debug)
    logger = get_logger(__name__)
    
    try:
        # Initialize generator
        generator = BatchGenerator(args.config)
        await generator.initialize()
        
        # Run batch generation
        await generator.run_batch_generation(
            max_subgraphs=args.max_subgraphs,
            batch_size=args.batch_size
        )
        
        logger.info("Batch generation completed successfully")
        
    except KeyboardInterrupt:
        logger.info("Batch generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Batch generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
