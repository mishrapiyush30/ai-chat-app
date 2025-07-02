"""
Embedding Manager Module

This module handles generating embeddings for document chunks and queries.
"""

from typing import List, Dict, Any, Union
import numpy as np
from langchain_openai import OpenAIEmbeddings
from sentence_transformers import SentenceTransformer

class EmbeddingManager:
    """Class for generating and managing embeddings."""
    
    def __init__(self, use_openai: bool = False, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the EmbeddingManager.
        
        Args:
            use_openai: Whether to use OpenAI's embedding API (requires API key)
            model_name: Name of the local model to use if not using OpenAI
        """
        self.use_openai = use_openai
        
        if use_openai:
            self.embedder = OpenAIEmbeddings(model="text-embedding-ada-002")
        else:
            self.embedder = SentenceTransformer(model_name)
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
            
        if self.use_openai:
            # OpenAI embeddings
            embeddings = self.embedder.embed_documents(texts)
            return embeddings
        else:
            # Sentence Transformers embeddings
            embeddings = self.embedder.encode(texts)
            return embeddings.tolist()
    
    def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for a single query text.
        
        Args:
            query: Query text to embed
            
        Returns:
            Embedding vector
        """
        if self.use_openai:
            # OpenAI query embedding
            embedding = self.embedder.embed_query(query)
            return embedding
        else:
            # Sentence Transformers query embedding
            embedding = self.embedder.encode(query)
            return embedding.tolist()
    
    def process_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process documents by adding embeddings to each chunk.
        
        Args:
            documents: List of document chunks with text and metadata
            
        Returns:
            Documents with embeddings added
        """
        if not documents:
            return []
            
        # Extract text from documents
        texts = [doc["text"] for doc in documents]
        
        # Generate embeddings
        embeddings = self.generate_embeddings(texts)
        
        # Add embeddings to documents
        for i, doc in enumerate(documents):
            doc["embedding"] = embeddings[i]
        
        return documents 