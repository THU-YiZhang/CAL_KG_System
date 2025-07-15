#!/usr/bin/env python3
"""
Environment Setup Script

Sets up the CT-MA environment including vector database and knowledge base.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.config_manager import ConfigManager
from src.utils.logger import setup_logger, get_logger
from src.rag.vector_store import VectorStore


async def setup_vector_database(config: ConfigManager) -> bool:
    """Setup vector database."""
    logger = get_logger(__name__)
    
    try:
        logger.info("Setting up vector database...")
        
        vector_store = VectorStore(config)
        await vector_store.setup()
        
        # Check if knowledge base exists and load it
        kb_path = config.get("data.knowledge_base_path")
        if Path(kb_path).exists():
            logger.info("Loading knowledge base into vector store...")
            await vector_store.load_knowledge_base(kb_path)
        else:
            logger.warning(f"Knowledge base directory not found: {kb_path}")
            logger.info("You can add documents to the knowledge base later")
        
        # Get statistics
        stats = vector_store.get_collection_stats()
        logger.info(f"Vector database setup completed: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"Vector database setup failed: {e}")
        return False


def check_api_configuration(config: ConfigManager) -> bool:
    """Check API configuration."""
    logger = get_logger(__name__)
    
    # Check LLM API key
    llm_api_key = config.get("models.llm.api_key")
    if not llm_api_key or llm_api_key.startswith("${"):
        logger.error("LLM API key not configured")
        logger.info("Please set DEEPSEEK_API_KEY environment variable or update config")
        return False
    
    # Check embedding API key
    embedding_api_key = config.get("models.embedding.api_key")
    if not embedding_api_key or embedding_api_key.startswith("${"):
        logger.error("Embedding API key not configured")
        logger.info("Please set OPENAI_API_KEY environment variable or update config")
        return False
    
    logger.info("API configuration validated")
    return True


def create_sample_knowledge_base(kb_path: Path) -> None:
    """Create sample knowledge base files."""
    logger = get_logger(__name__)
    
    kb_path.mkdir(parents=True, exist_ok=True)
    
    # Create sample circuit document
    sample_doc = """# 电路设计基础知识

## 运算放大器基础

运算放大器（Operational Amplifier，简称运放）是模拟电路中最重要的基本器件之一。

### 理想运放特性

1. **无穷大输入阻抗**: 理想运放的输入阻抗为无穷大，因此输入电流为零。
2. **零输出阻抗**: 理想运放的输出阻抗为零，能够驱动任何负载。
3. **无穷大开环增益**: 理想运放的开环电压增益为无穷大。

### 基本运放电路

#### 反相放大器

反相放大器的增益公式为：
Av = -Rf/Ri

其中Rf为反馈电阻，Ri为输入电阻。

#### 同相放大器

同相放大器的增益公式为：
Av = 1 + Rf/Ri

## 滤波器设计

滤波器是用来滤除不需要的频率成分，保留需要的频率成分的电路。

### 低通滤波器

低通滤波器允许低频信号通过，阻止高频信号。

一阶RC低通滤波器的截止频率为：
fc = 1/(2πRC)

### 高通滤波器

高通滤波器允许高频信号通过，阻止低频信号。

## 反馈控制

反馈是电路设计中的重要概念，分为正反馈和负反馈。

### 负反馈的优点

1. 稳定增益
2. 减少失真
3. 扩展带宽
4. 改善输入输出阻抗

### 稳定性分析

系统稳定性可以通过相位裕度和增益裕度来判断。
"""
    
    sample_file = kb_path / "circuit_basics.md"
    with open(sample_file, 'w', encoding='utf-8') as f:
        f.write(sample_doc)
    
    logger.info(f"Created sample knowledge base file: {sample_file}")


def check_knowledge_graph(config: ConfigManager) -> bool:
    """Check if knowledge graph is available."""
    logger = get_logger(__name__)
    
    kg_path = Path(config.get("data.input_kg_path"))
    
    if not kg_path.exists():
        logger.error(f"Knowledge graph not found: {kg_path}")
        logger.info("Please run: python scripts/import_kg.py")
        return False
    
    logger.info(f"Knowledge graph found: {kg_path}")
    return True


async def main():
    """Main setup function."""
    setup_logger()
    logger = get_logger(__name__)
    
    logger.info("Starting CT-MA environment setup...")
    
    # Load configuration
    try:
        config = ConfigManager()
        logger.info("Configuration loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Check knowledge graph
    if not check_knowledge_graph(config):
        sys.exit(1)
    
    # Check API configuration
    if not check_api_configuration(config):
        sys.exit(1)
    
    # Create knowledge base if it doesn't exist
    kb_path = Path(config.get("data.knowledge_base_path"))
    if not kb_path.exists():
        logger.info("Creating sample knowledge base...")
        create_sample_knowledge_base(kb_path)
    
    # Setup vector database
    if not await setup_vector_database(config):
        sys.exit(1)
    
    # Create output directories
    output_dirs = [
        config.get("data.subgraphs_path"),
        config.get("data.cot_datasets_path"),
        config.get("data.reports_path")
    ]
    
    for dir_path in output_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    logger.info("Output directories created")
    
    print("\n" + "="*60)
    print("CT-MA ENVIRONMENT SETUP COMPLETED")
    print("="*60)
    print("✅ Configuration validated")
    print("✅ Knowledge graph available")
    print("✅ Vector database initialized")
    print("✅ Output directories created")
    print("\nYou can now run the main system:")
    print("  python main.py --mode full")
    print("\nOr run individual steps:")
    print("  python main.py --mode extract_subgraphs")
    print("  python main.py --mode generate_cot")


if __name__ == "__main__":
    asyncio.run(main())
