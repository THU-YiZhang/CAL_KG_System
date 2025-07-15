#!/usr/bin/env python3
"""
Import Knowledge Graph Script

Imports unified knowledge graph from CAL-KG system into CT-MA project.
"""

import sys
import json
import shutil
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.config_manager import ConfigManager
from src.utils.logger import setup_logger, get_logger


def import_knowledge_graph(source_path: str, target_path: str) -> bool:
    """
    Import knowledge graph from source to target location.
    
    Args:
        source_path: Path to source knowledge graph file
        target_path: Path to target location
        
    Returns:
        True if successful, False otherwise
    """
    logger = get_logger(__name__)
    
    try:
        source_file = Path(source_path)
        target_file = Path(target_path)
        
        if not source_file.exists():
            logger.error(f"Source file not found: {source_file}")
            return False
        
        # Create target directory if needed
        target_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file
        shutil.copy2(source_file, target_file)
        
        # Validate the imported file
        with open(target_file, 'r', encoding='utf-8') as f:
            kg_data = json.load(f)
        
        # Basic validation
        required_keys = ['nodes', 'edges']
        for key in required_keys:
            if key not in kg_data:
                logger.error(f"Invalid knowledge graph: missing {key}")
                return False
        
        logger.info(f"Successfully imported knowledge graph:")
        logger.info(f"  Source: {source_file}")
        logger.info(f"  Target: {target_file}")
        logger.info(f"  Nodes: {len(kg_data['nodes'])}")
        logger.info(f"  Edges: {len(kg_data['edges'])}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to import knowledge graph: {e}")
        return False


def main():
    """Main function."""
    setup_logger()
    logger = get_logger(__name__)
    
    # Load configuration
    config = ConfigManager()
    
    # Default paths
    cal_kg_output = Path("../output/final/unified_knowledge_graph.json")
    ct_ma_input = Path(config.get("data.input_kg_path"))
    
    # Check if source exists
    if not cal_kg_output.exists():
        logger.error(f"CAL-KG output not found at: {cal_kg_output}")
        logger.info("Please ensure CAL-KG system has been run and generated the unified knowledge graph")
        sys.exit(1)
    
    # Import the knowledge graph
    success = import_knowledge_graph(str(cal_kg_output), str(ct_ma_input))
    
    if success:
        logger.info("Knowledge graph import completed successfully")
        
        # Print next steps
        print("\n" + "="*60)
        print("KNOWLEDGE GRAPH IMPORT COMPLETED")
        print("="*60)
        print(f"✅ Imported: {ct_ma_input}")
        print("\nNext steps:")
        print("1. Set up your knowledge base in data/knowledge_base/")
        print("2. Configure API keys in config/system_config.yaml")
        print("3. Run: python scripts/setup_environment.py")
        print("4. Start generating CoT data: python main.py")
        
    else:
        logger.error("Knowledge graph import failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
