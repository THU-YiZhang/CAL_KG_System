#!/usr/bin/env python3
"""
CT-MA-CircuitThinking Main Entry Point

This is the main entry point for the Circuit Thinking Multi-Agent System.
It orchestrates the entire pipeline from knowledge graph processing to CoT data generation.
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.config_manager import ConfigManager
from src.utils.logger import setup_logger, get_logger
from src.utils.metrics import MetricsCollector

# Import core components
from src.core.kg_loader import KGLoader
from src.core.subgraph_extractor import SubgraphExtractor
from src.rag.vector_store import VectorStore
from src.rag.knowledge_enhancer import KnowledgeEnhancer
from src.agents.coordinator import Coordinator
from src.cot.data_generator import COTDataGenerator


class CTMASystem:
    """Main CT-MA System orchestrator."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the CT-MA system."""
        self.config = ConfigManager(config_path)
        self.logger = get_logger(__name__)
        self.metrics = MetricsCollector()
        
        # Initialize components
        self.kg_loader = None
        self.subgraph_extractor = None
        self.vector_store = None
        self.knowledge_enhancer = None
        self.coordinator = None
        self.cot_generator = None
        
    async def initialize(self):
        """Initialize all system components."""
        self.logger.info("Initializing CT-MA system...")
        
        try:
            # Initialize core components
            self.kg_loader = KGLoader(self.config)
            self.subgraph_extractor = SubgraphExtractor(self.config)
            
            # Initialize RAG components
            self.vector_store = VectorStore(self.config)
            self.knowledge_enhancer = KnowledgeEnhancer(self.config, self.vector_store)
            
            # Initialize agent system
            self.coordinator = Coordinator(self.config)
            
            # Initialize CoT generator
            self.cot_generator = COTDataGenerator(
                self.config, 
                self.coordinator, 
                self.knowledge_enhancer
            )
            
            self.logger.info("CT-MA system initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize CT-MA system: {e}")
            raise
    
    async def run_full_pipeline(self):
        """Run the complete CT-MA pipeline."""
        self.logger.info("Starting full CT-MA pipeline...")
        
        try:
            # Step 1: Load knowledge graph
            self.logger.info("Step 1: Loading knowledge graph...")
            kg_data = await self.kg_loader.load_knowledge_graph()
            
            # Step 2: Extract subgraphs
            self.logger.info("Step 2: Extracting subgraphs...")
            subgraphs = await self.subgraph_extractor.extract_application_subgraphs(kg_data)
            
            # Step 3: Setup RAG system
            self.logger.info("Step 3: Setting up RAG system...")
            await self.vector_store.setup()
            await self.knowledge_enhancer.initialize()
            
            # Step 4: Generate CoT data
            self.logger.info("Step 4: Generating CoT data...")
            cot_data = await self.cot_generator.generate_batch(subgraphs)
            
            # Step 5: Save results
            self.logger.info("Step 5: Saving results...")
            await self.save_results(cot_data)
            
            self.logger.info("Full pipeline completed successfully")
            return cot_data
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            raise
    
    async def run_step(self, step: str):
        """Run a specific pipeline step."""
        self.logger.info(f"Running step: {step}")
        
        if step == "extract_subgraphs":
            kg_data = await self.kg_loader.load_knowledge_graph()
            return await self.subgraph_extractor.extract_application_subgraphs(kg_data)
        
        elif step == "setup_rag":
            await self.vector_store.setup()
            return await self.knowledge_enhancer.initialize()
        
        elif step == "generate_cot":
            # Load existing subgraphs
            subgraphs = await self.load_subgraphs()
            return await self.cot_generator.generate_batch(subgraphs)
        
        else:
            raise ValueError(f"Unknown step: {step}")
    
    async def save_results(self, cot_data):
        """Save generated CoT data and reports."""
        output_path = Path(self.config.get("data.cot_datasets_path"))
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save CoT dataset
        import json
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_path / f"cot_dataset_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(cot_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"CoT data saved to: {output_file}")
        
        # Generate report
        await self.generate_report(cot_data, timestamp)
    
    async def generate_report(self, cot_data, timestamp):
        """Generate analysis report."""
        report_path = Path(self.config.get("data.reports_path"))
        report_path.mkdir(parents=True, exist_ok=True)
        
        report_file = report_path / f"analysis_report_{timestamp}.md"
        
        # Basic statistics
        total_items = len(cot_data)
        avg_logic_length = sum(len(item.get('logic', '')) for item in cot_data) / total_items if total_items > 0 else 0
        avg_think_length = sum(len(item.get('think', '')) for item in cot_data) / total_items if total_items > 0 else 0
        avg_answer_length = sum(len(item.get('answer', '')) for item in cot_data) / total_items if total_items > 0 else 0
        
        report_content = f"""# CT-MA Analysis Report

Generated: {timestamp}

## Summary Statistics

- Total CoT items generated: {total_items}
- Average logic section length: {avg_logic_length:.1f} characters
- Average think section length: {avg_think_length:.1f} characters  
- Average answer section length: {avg_answer_length:.1f} characters

## Quality Metrics

- Format validation: {sum(1 for item in cot_data if self.validate_format(item))} / {total_items}
- Content completeness: {sum(1 for item in cot_data if self.validate_content(item))} / {total_items}

## Next Steps

1. Review generated CoT data for quality
2. Fine-tune agent prompts if needed
3. Expand knowledge base for better RAG performance
4. Scale up generation for larger datasets
"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        self.logger.info(f"Report saved to: {report_file}")
    
    def validate_format(self, item):
        """Validate CoT item format."""
        required_keys = ['logic', 'think', 'answer']
        return all(key in item and item[key].strip() for key in required_keys)
    
    def validate_content(self, item):
        """Validate CoT item content."""
        if not self.validate_format(item):
            return False
        
        # Check minimum lengths
        min_lengths = {
            'logic': self.config.get("quality.min_logic_length", 100),
            'think': self.config.get("quality.min_think_length", 500), 
            'answer': self.config.get("quality.min_answer_length", 100)
        }
        
        return all(len(item[key]) >= min_lengths[key] for key in min_lengths)
    
    async def load_subgraphs(self):
        """Load existing subgraphs from disk."""
        # Implementation to load previously extracted subgraphs
        pass


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="CT-MA-CircuitThinking System")
    parser.add_argument("--config", type=str, help="Path to config file")
    parser.add_argument("--mode", type=str, default="full", 
                       choices=["full", "extract_subgraphs", "setup_rag", "generate_cot"],
                       help="Execution mode")
    parser.add_argument("--batch_size", type=int, default=10, help="Batch size for processing")
    parser.add_argument("--workers", type=int, default=4, help="Number of worker threads")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logger(debug=args.debug)
    logger = get_logger(__name__)
    
    async def run():
        try:
            # Initialize system
            system = CTMASystem(args.config)
            await system.initialize()
            
            # Run based on mode
            if args.mode == "full":
                await system.run_full_pipeline()
            else:
                await system.run_step(args.mode)
                
            logger.info("CT-MA system completed successfully")
            
        except Exception as e:
            logger.error(f"CT-MA system failed: {e}")
            sys.exit(1)
    
    # Run the async main function
    asyncio.run(run())


if __name__ == "__main__":
    main()
