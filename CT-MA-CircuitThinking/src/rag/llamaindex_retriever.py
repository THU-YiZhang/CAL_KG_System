"""
LlamaIndex-based Retriever for CT-MA System.

Uses LlamaIndex framework to retrieve from original circuit design books.
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import json

from llama_index.core import (
    VectorStoreIndex, 
    SimpleDirectoryReader, 
    StorageContext,
    load_index_from_storage,
    Settings
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

from ..utils.logger import LoggerMixin
from ..utils.config_manager import ConfigManager


class LlamaIndexRetriever(LoggerMixin):
    """LlamaIndex-based retriever for circuit design books."""
    
    def __init__(self, config: ConfigManager):
        """
        Initialize LlamaIndex Retriever.
        
        Args:
            config: Configuration manager instance
        """
        self.config = config
        self.index = None
        self.query_engine = None
        self.retriever = None
        
        # Configuration
        self.books_path = config.get("rag.books_path", "data/books/")
        self.index_path = config.get("rag.index_path", "data/llamaindex_storage/")
        self.chunk_size = config.get("rag.llamaindex.chunk_size", 1024)
        self.chunk_overlap = config.get("rag.llamaindex.chunk_overlap", 200)
        self.top_k = config.get("rag.llamaindex.top_k", 10)
        
    async def setup(self) -> None:
        """Setup LlamaIndex retriever."""
        self.logger.info("Setting up LlamaIndex retriever...")
        
        try:
            # Configure LlamaIndex settings
            Settings.embed_model = OpenAIEmbedding(
                model=self.config.get("models.embedding.model", "text-embedding-3-small"),
                api_key=self.config.get("models.embedding.api_key"),
                api_base=self.config.get("models.embedding.base_url")
            )
            
            # Use a compatible model name for LlamaIndex
            Settings.llm = OpenAI(
                model="gpt-3.5-turbo",  # Use compatible model name
                api_key=self.config.get("models.llm.api_key"),
                api_base=self.config.get("models.llm.base_url"),
                temperature=0.1
            )
            
            # Configure node parser
            Settings.node_parser = SentenceSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            
            # Load or create index
            index_path = Path(self.index_path)
            
            if index_path.exists() and any(index_path.iterdir()):
                # Load existing index
                self.logger.info("Loading existing LlamaIndex...")
                storage_context = StorageContext.from_defaults(persist_dir=str(index_path))
                self.index = load_index_from_storage(storage_context)
            else:
                # Create new index
                self.logger.info("Creating new LlamaIndex from books...")
                await self._create_index_from_books()
            
            # Setup retriever and query engine
            self.retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=self.top_k
            )
            
            self.query_engine = RetrieverQueryEngine(retriever=self.retriever)
            
            self.logger.info("LlamaIndex retriever setup completed")
            
        except Exception as e:
            self.logger.error(f"Failed to setup LlamaIndex retriever: {e}")
            raise
    
    async def _create_index_from_books(self) -> None:
        """Create index from circuit design books."""
        books_path = Path(self.books_path)
        
        if not books_path.exists():
            self.logger.warning(f"Books directory not found: {books_path}")
            books_path.mkdir(parents=True, exist_ok=True)
            
            # Create sample book content
            await self._create_sample_books(books_path)
        
        # Load documents
        self.logger.info(f"Loading documents from: {books_path}")
        reader = SimpleDirectoryReader(
            input_dir=str(books_path),
            recursive=True,
            file_extractor={
                ".pdf": "default",
                ".txt": "default", 
                ".md": "default",
                ".docx": "default"
            }
        )
        
        documents = reader.load_data()
        self.logger.info(f"Loaded {len(documents)} documents")
        
        if not documents:
            self.logger.warning("No documents found, creating sample content")
            await self._create_sample_books(books_path)
            documents = reader.load_data()
        
        # Create index
        self.index = VectorStoreIndex.from_documents(documents)
        
        # Persist index
        index_path = Path(self.index_path)
        index_path.mkdir(parents=True, exist_ok=True)
        self.index.storage_context.persist(persist_dir=str(index_path))
        
        self.logger.info(f"Index created and saved to: {index_path}")
    
    async def _create_sample_books(self, books_path: Path) -> None:
        """Create sample circuit design book content."""
        self.logger.info("Creating sample circuit design books...")
        
        # Sample book 1: Analog Circuit Design
        analog_book = """# 模拟电路设计基础

## 第1章 运算放大器基础

### 1.1 理想运放特性

理想运算放大器具有以下特性：
1. 无穷大输入阻抗（Rin = ∞）
2. 零输出阻抗（Rout = 0）
3. 无穷大开环增益（Aol = ∞）
4. 无穷大共模抑制比（CMRR = ∞）
5. 无穷大带宽（BW = ∞）

### 1.2 基本运放电路

#### 1.2.1 反相放大器

反相放大器的电压增益为：
Av = -Rf/Ri

其中：
- Rf：反馈电阻
- Ri：输入电阻

输入阻抗：Zin = Ri
输出阻抗：Zout ≈ 0

#### 1.2.2 同相放大器

同相放大器的电压增益为：
Av = 1 + Rf/Ri

输入阻抗：Zin ≈ ∞
输出阻抗：Zout ≈ 0

### 1.3 频率响应

运放的频率响应受到以下因素影响：
1. 增益带宽积（GBW）
2. 转换速率（Slew Rate）
3. 相位裕度（Phase Margin）

## 第2章 CMOS运算放大器设计

### 2.1 单级运放

#### 2.1.1 共源放大器

基本共源放大器的增益为：
Av = -gm × (ro1 || ro2)

其中：
- gm：跨导
- ro：输出电阻

### 2.2 两级运放

#### 2.2.1 Miller补偿

Miller补偿通过在第一级和第二级之间连接补偿电容Cc来实现稳定性。

补偿后的主极点频率：
fp1 ≈ 1/(2π × gm2 × Cc × Av1)

### 2.3 Cascode结构

#### 2.3.1 基本Cascode

Cascode结构通过级联两个晶体管来提高输出阻抗：
Rout = gm2 × ro2 × ro1

#### 2.3.2 折叠式Cascode

折叠式Cascode结构解决了电源电压限制问题，同时保持高增益特性。

## 第3章 滤波器设计

### 3.1 有源滤波器

#### 3.1.1 Sallen-Key拓扑

Sallen-Key低通滤波器的传递函数：
H(s) = K / (s²LC + sRC + 1)

### 3.2 开关电容滤波器

开关电容技术通过时钟控制的开关和电容来实现精确的时间常数。

等效电阻：
Req = 1/(fc × C)

其中fc为时钟频率。
"""
        
        # Sample book 2: Digital Circuit Design
        digital_book = """# 数字电路设计

## 第1章 CMOS逻辑门

### 1.1 CMOS反相器

#### 1.1.1 静态特性

CMOS反相器由一个PMOS和一个NMOS组成。

噪声容限：
NMH = VOH - VIH
NML = VIL - VOL

#### 1.1.2 动态特性

传播延迟：
tpd = (tpHL + tpLH) / 2

功耗：
P = Pstatic + Pdynamic + Pshort-circuit

### 1.2 复合逻辑门

#### 1.2.1 NAND门

两输入NAND门的逻辑函数：
Y = !(A · B)

#### 1.2.2 NOR门

两输入NOR门的逻辑函数：
Y = !(A + B)

## 第2章 时序电路

### 2.1 锁存器和触发器

#### 2.1.1 D锁存器

D锁存器在使能信号有效时，输出跟随输入。

#### 2.1.2 D触发器

D触发器在时钟边沿触发时更新输出。

建立时间：tsu
保持时间：th

### 2.2 计数器设计

#### 2.2.1 异步计数器

异步计数器的每一级都由前一级的输出触发。

最大计数频率受限于累积传播延迟。

#### 2.2.2 同步计数器

同步计数器的所有触发器都由同一时钟信号触发。

## 第3章 存储器设计

### 3.1 SRAM设计

#### 3.1.1 6T SRAM单元

标准6T SRAM单元由6个晶体管组成：
- 2个存储晶体管
- 2个负载晶体管  
- 2个访问晶体管

读噪声容限和写能力是关键设计参数。

### 3.2 DRAM设计

#### 3.2.1 1T1C DRAM单元

DRAM单元由一个访问晶体管和一个存储电容组成。

需要定期刷新以保持数据。
"""
        
        # Save sample books
        with open(books_path / "analog_circuit_design.md", 'w', encoding='utf-8') as f:
            f.write(analog_book)
        
        with open(books_path / "digital_circuit_design.md", 'w', encoding='utf-8') as f:
            f.write(digital_book)
        
        self.logger.info("Sample books created")
    
    async def retrieve_for_kg_node(self, node_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Retrieve relevant content for a knowledge graph node.
        
        Args:
            node_data: Node data from knowledge graph
            
        Returns:
            List of retrieved content with metadata
        """
        if not self.query_engine:
            raise RuntimeError("LlamaIndex retriever not initialized")
        
        # Build query from node data
        query_parts = []
        
        if 'label' in node_data:
            query_parts.append(node_data['label'])
        
        if 'summary' in node_data:
            query_parts.append(node_data['summary'])
        
        if 'keywords' in node_data:
            query_parts.extend(node_data['keywords'][:3])  # Top 3 keywords
        
        query = " ".join(query_parts)
        
        try:
            # Use retriever to get relevant nodes
            retrieved_nodes = self.retriever.retrieve(query)
            
            results = []
            for node in retrieved_nodes:
                result = {
                    'content': node.text,
                    'score': node.score,
                    'metadata': {
                        'source': node.metadata.get('file_name', 'unknown'),
                        'page': node.metadata.get('page_label', 'unknown'),
                        'node_id': node.node_id
                    },
                    'retrieval_type': 'llamaindex_book'
                }
                results.append(result)
            
            self.logger.debug(f"Retrieved {len(results)} items for node: {node_data.get('label', 'unknown')}")
            return results
            
        except Exception as e:
            self.logger.error(f"Retrieval failed for node {node_data.get('label', 'unknown')}: {e}")
            return []

    async def retrieve_evidence(self, query: str) -> Dict[str, Any]:
        """
        Retrieve evidence for a given query.

        Args:
            query: Search query string

        Returns:
            Dictionary containing retrieved evidence
        """
        if not self.retriever:
            self.logger.warning("LlamaIndex retriever not initialized, returning empty evidence")
            return {}

        try:
            # Use retriever to get relevant nodes
            retrieved_nodes = self.retriever.retrieve(query)

            evidence_package = {
                'query': query,
                'retrieved_content': [],
                'total_results': len(retrieved_nodes)
            }

            for node in retrieved_nodes:
                evidence_item = {
                    'content': node.text[:500],  # Limit content length
                    'score': node.score,
                    'source': node.metadata.get('file_name', 'unknown'),
                    'page': node.metadata.get('page_label', 'unknown')
                }
                evidence_package['retrieved_content'].append(evidence_item)

            self.logger.debug(f"Retrieved {len(retrieved_nodes)} evidence items for query: {query}")
            return evidence_package

        except Exception as e:
            self.logger.error(f"Evidence retrieval failed for query '{query}': {e}")
            return {}

    async def query_books(self, query: str) -> str:
        """
        Query books using natural language.
        
        Args:
            query: Natural language query
            
        Returns:
            Generated response based on book content
        """
        if not self.query_engine:
            raise RuntimeError("LlamaIndex retriever not initialized")
        
        try:
            response = self.query_engine.query(query)
            return str(response)
        except Exception as e:
            self.logger.error(f"Query failed: {e}")
            return f"查询失败: {e}"
    
    async def get_relevant_context_for_reasoning(
        self, 
        reasoning_step: str, 
        technical_terms: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Get relevant context for a specific reasoning step.
        
        Args:
            reasoning_step: Description of reasoning step
            technical_terms: List of technical terms involved
            
        Returns:
            List of relevant contexts
        """
        # Combine reasoning step with technical terms
        query = f"{reasoning_step} {' '.join(technical_terms)}"
        
        try:
            retrieved_nodes = self.retriever.retrieve(query)
            
            contexts = []
            for node in retrieved_nodes:
                context = {
                    'content': node.text,
                    'relevance_score': node.score,
                    'source': node.metadata.get('file_name', 'unknown'),
                    'reasoning_support': self._analyze_reasoning_support(node.text, reasoning_step)
                }
                contexts.append(context)
            
            return contexts[:5]  # Top 5 contexts
            
        except Exception as e:
            self.logger.error(f"Context retrieval failed: {e}")
            return []
    
    def _analyze_reasoning_support(self, content: str, reasoning_step: str) -> str:
        """Analyze how content supports reasoning step."""
        # Simple heuristic analysis
        if any(keyword in content.lower() for keyword in ['公式', '计算', '方程']):
            return 'formula_support'
        elif any(keyword in content.lower() for keyword in ['原理', '机制', '工作']):
            return 'principle_support'
        elif any(keyword in content.lower() for keyword in ['设计', '实现', '方法']):
            return 'design_support'
        elif any(keyword in content.lower() for keyword in ['优势', '缺点', '比较']):
            return 'analysis_support'
        else:
            return 'general_support'
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the index."""
        if not self.index:
            return {}
        
        try:
            # Get basic stats
            stats = {
                'index_type': type(self.index).__name__,
                'storage_path': self.index_path,
                'chunk_size': self.chunk_size,
                'chunk_overlap': self.chunk_overlap,
                'top_k': self.top_k
            }
            
            # Try to get document count
            if hasattr(self.index, 'docstore'):
                stats['document_count'] = len(self.index.docstore.docs)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get index stats: {e}")
            return {'error': str(e)}
