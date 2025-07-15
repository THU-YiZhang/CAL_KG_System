"""
Vector Store for CT-MA System.

Manages vector storage and retrieval using ChromaDB.
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
import hashlib

from ..utils.logger import LoggerMixin
from ..utils.config_manager import ConfigManager


class VectorStore(LoggerMixin):
    """Vector store implementation using ChromaDB."""
    
    def __init__(self, config: ConfigManager):
        """
        Initialize Vector Store.
        
        Args:
            config: Configuration manager instance
        """
        self.config = config
        self.client = None
        self.collection = None
        self.embeddings = None
        self.text_splitter = None
        
        # Configuration
        self.collection_name = config.get("rag.vector_store.collection_name", "circuit_knowledge")
        self.persist_directory = config.get("rag.vector_store.persist_directory", "./data/chroma_db")
        self.chunk_size = config.get("rag.document_processing.chunk_size", 512)
        self.chunk_overlap = config.get("rag.document_processing.chunk_overlap", 50)
        
    async def setup(self) -> None:
        """Setup vector store and initialize components."""
        self.logger.info("Setting up vector store...")
        
        try:
            # Initialize ChromaDB client
            persist_dir = Path(self.persist_directory)
            persist_dir.mkdir(parents=True, exist_ok=True)
            
            self.client = chromadb.PersistentClient(
                path=str(persist_dir),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
                self.logger.info(f"Loaded existing collection: {self.collection_name}")
            except:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Circuit domain knowledge base"}
                )
                self.logger.info(f"Created new collection: {self.collection_name}")
            
            # Initialize embeddings
            self.embeddings = OpenAIEmbeddings(
                model=self.config.get("models.embedding.model", "text-embedding-3-small"),
                openai_api_key=self.config.get("models.embedding.api_key"),
                openai_api_base=self.config.get("models.embedding.base_url")
            )
            
            # Initialize text splitter
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=["\n\n", "\n", "。", ".", " ", ""]
            )
            
            self.logger.info("Vector store setup completed")
            
        except Exception as e:
            self.logger.error(f"Failed to setup vector store: {e}")
            raise
    
    async def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of documents with 'content' and 'metadata' keys
        """
        if not self.collection:
            raise RuntimeError("Vector store not initialized")
        
        self.logger.info(f"Adding {len(documents)} documents to vector store...")
        
        all_chunks = []
        all_embeddings = []
        all_metadatas = []
        all_ids = []
        
        for doc in documents:
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            
            # Split document into chunks
            chunks = self.text_splitter.split_text(content)
            
            for i, chunk in enumerate(chunks):
                if len(chunk.strip()) < 50:  # Skip very short chunks
                    continue
                
                # Generate unique ID
                chunk_id = self._generate_chunk_id(content, i)
                
                # Prepare metadata
                chunk_metadata = {
                    **metadata,
                    'chunk_index': i,
                    'chunk_length': len(chunk),
                    'source_length': len(content)
                }
                
                all_chunks.append(chunk)
                all_metadatas.append(chunk_metadata)
                all_ids.append(chunk_id)
        
        if not all_chunks:
            self.logger.warning("No valid chunks to add")
            return
        
        # Generate embeddings in batches
        batch_size = self.config.get("models.embedding.batch_size", 100)
        
        for i in range(0, len(all_chunks), batch_size):
            batch_chunks = all_chunks[i:i + batch_size]
            batch_embeddings = await self._generate_embeddings(batch_chunks)
            all_embeddings.extend(batch_embeddings)
        
        # Add to collection
        self.collection.add(
            documents=all_chunks,
            embeddings=all_embeddings,
            metadatas=all_metadatas,
            ids=all_ids
        )
        
        self.logger.info(f"Added {len(all_chunks)} chunks to vector store")
    
    async def search(
        self, 
        query: str, 
        top_k: int = 10, 
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents.
        
        Args:
            query: Search query
            top_k: Number of results to return
            filter_metadata: Optional metadata filter
            
        Returns:
            List of search results
        """
        if not self.collection:
            raise RuntimeError("Vector store not initialized")
        
        # Generate query embedding
        query_embedding = await self._generate_embeddings([query])
        
        # Search
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            where=filter_metadata
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results['documents'][0])):
            result = {
                'content': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'score': 1 - results['distances'][0][i],  # Convert distance to similarity
                'id': results['ids'][0][i]
            }
            formatted_results.append(result)
        
        return formatted_results
    
    async def search_by_keywords(
        self, 
        keywords: List[str], 
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search by keywords using semantic similarity.
        
        Args:
            keywords: List of keywords
            top_k: Number of results to return
            
        Returns:
            List of search results
        """
        # Combine keywords into query
        query = " ".join(keywords)
        return await self.search(query, top_k)
    
    async def get_relevant_context(
        self, 
        node_data: Dict[str, Any], 
        max_contexts: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get relevant context for a knowledge graph node.
        
        Args:
            node_data: Node data from knowledge graph
            max_contexts: Maximum number of contexts to return
            
        Returns:
            List of relevant contexts
        """
        # Build search query from node data
        query_parts = []
        
        if 'label' in node_data:
            query_parts.append(node_data['label'])
        
        if 'summary' in node_data:
            query_parts.append(node_data['summary'])
        
        if 'keywords' in node_data:
            query_parts.extend(node_data['keywords'])
        
        query = " ".join(query_parts)
        
        # Search for relevant contexts
        results = await self.search(query, top_k=max_contexts)
        
        # Filter by relevance threshold
        threshold = self.config.get("rag.retrieval.score_threshold", 0.7)
        filtered_results = [r for r in results if r['score'] >= threshold]
        
        return filtered_results
    
    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        try:
            embeddings = await asyncio.to_thread(
                self.embeddings.embed_documents, texts
            )
            return embeddings
        except Exception as e:
            self.logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    def _generate_chunk_id(self, content: str, chunk_index: int) -> str:
        """Generate unique ID for a chunk."""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"chunk_{content_hash}_{chunk_index}"
    
    async def load_knowledge_base(self, knowledge_base_path: str) -> None:
        """
        Load documents from knowledge base directory.
        
        Args:
            knowledge_base_path: Path to knowledge base directory
        """
        kb_dir = Path(knowledge_base_path)
        if not kb_dir.exists():
            self.logger.warning(f"Knowledge base directory not found: {kb_dir}")
            return
        
        documents = []
        supported_formats = self.config.get("rag.document_processing.supported_formats", 
                                           ["pdf", "txt", "md", "docx"])
        
        for file_path in kb_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix[1:] in supported_formats:
                try:
                    content = await self._load_document(file_path)
                    if content:
                        documents.append({
                            'content': content,
                            'metadata': {
                                'source': str(file_path),
                                'filename': file_path.name,
                                'file_type': file_path.suffix[1:]
                            }
                        })
                except Exception as e:
                    self.logger.warning(f"Failed to load {file_path}: {e}")
        
        if documents:
            await self.add_documents(documents)
            self.logger.info(f"Loaded {len(documents)} documents from knowledge base")
        else:
            self.logger.warning("No documents found in knowledge base")
    
    async def _load_document(self, file_path: Path) -> Optional[str]:
        """Load content from a document file."""
        try:
            if file_path.suffix == '.txt' or file_path.suffix == '.md':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            elif file_path.suffix == '.pdf':
                # Would need PyPDF2 or similar
                self.logger.warning(f"PDF loading not implemented: {file_path}")
                return None
            elif file_path.suffix == '.docx':
                # Would need python-docx
                self.logger.warning(f"DOCX loading not implemented: {file_path}")
                return None
            else:
                return None
        except Exception as e:
            self.logger.error(f"Error loading {file_path}: {e}")
            return None
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        if not self.collection:
            return {}
        
        count = self.collection.count()
        return {
            'total_chunks': count,
            'collection_name': self.collection_name,
            'persist_directory': self.persist_directory
        }
