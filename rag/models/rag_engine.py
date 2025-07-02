"""
RAG Engine Module

This module combines document processing, embedding, and retrieval with LLM generation.
"""

import os
from typing import List, Dict, Any, Optional, Union
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser

from ..utils.document_processor import DocumentProcessor
from ..utils.embedding_manager import EmbeddingManager
from ..utils.vector_store import VectorStore

class RAGEngine:
    """Class for performing Retrieval-Augmented Generation."""
    
    def __init__(self, 
                 use_openai_embeddings: bool = False,
                 embedding_model_name: str = "all-MiniLM-L6-v2",
                 llm_model_name: str = "gpt-3.5-turbo",
                 temperature: float = 0.7,
                 chunk_size: int = 500,
                 chunk_overlap: int = 50):
        """
        Initialize the RAG Engine.
        
        Args:
            use_openai_embeddings: Whether to use OpenAI's embedding API
            embedding_model_name: Name of the local embedding model if not using OpenAI
            llm_model_name: Name of the LLM model to use
            temperature: Temperature for LLM generation
            chunk_size: Size of document chunks
            chunk_overlap: Overlap between chunks
        """
        self.document_processor = DocumentProcessor(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        self.embedding_manager = EmbeddingManager(
            use_openai=use_openai_embeddings,
            model_name=embedding_model_name
        )
        
        # Determine embedding dimension based on model
        if use_openai_embeddings:
            self.embedding_dim = 1536  # OpenAI ada-002 dimension
        else:
            # For sentence-transformers, dimension depends on model
            # all-MiniLM-L6-v2 has 384 dimensions
            self.embedding_dim = 384
        
        self.vector_store = VectorStore(dimension=self.embedding_dim)
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model_name=llm_model_name,
            temperature=temperature
        )
        
        # Initialize prompt template
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant that answers questions based on the provided context. "
                      "If the answer cannot be found in the context, say that you don't know."),
            ("human", "Context:\n{context}\n\nQuestion: {query}")
        ])
        
        # Create generation chain
        self.generation_chain = self.prompt_template | self.llm | StrOutputParser()
    
    def index_documents(self, directory_path: str) -> None:
        """
        Index documents from a directory.
        
        Args:
            directory_path: Path to directory containing documents
        """
        # Load and process documents
        document_chunks = self.document_processor.load_documents_from_directory(directory_path)
        
        if not document_chunks:
            print(f"No documents found in {directory_path}")
            return
            
        print(f"Loaded {len(document_chunks)} document chunks")
        
        # Generate embeddings
        documents_with_embeddings = self.embedding_manager.process_documents(document_chunks)
        
        # Add to vector store
        self.vector_store.add_documents(documents_with_embeddings)
        print(f"Indexed {len(documents_with_embeddings)} document chunks")
    
    def save_index(self, directory: str = "rag/data", name: str = "vector_store") -> None:
        """
        Save the vector index to disk.
        
        Args:
            directory: Directory to save the index
            name: Base name for the index files
        """
        self.vector_store.save(directory, name)
        print(f"Saved vector store to {directory}/{name}.*")
    
    def load_index(self, directory: str = "rag/data", name: str = "vector_store") -> None:
        """
        Load a vector index from disk.
        
        Args:
            directory: Directory containing the index
            name: Base name of the index files
        """
        self.vector_store = VectorStore.load(directory, name)
        print(f"Loaded vector store from {directory}/{name}.*")
    
    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: User query
            top_k: Number of top results to retrieve
            
        Returns:
            List of relevant document chunks with scores
        """
        # Generate query embedding
        query_embedding = self.embedding_manager.generate_query_embedding(query)
        
        # Search vector store
        results = self.vector_store.search(query_embedding, top_k=top_k)
        
        return results
    
    def format_context(self, results: List[Dict[str, Any]]) -> str:
        """
        Format retrieval results into context for the LLM.
        
        Args:
            results: List of retrieval results
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for i, result in enumerate(results):
            doc = result["document"]
            score = result["score"]
            
            # Format document with source information
            source = doc["metadata"].get("source", "Unknown")
            page = doc["metadata"].get("page", "")
            page_info = f", Page {page}" if page else ""
            
            context_part = f"[Document {i+1}] (Source: {source}{page_info}, Relevance: {score:.2f})\n{doc['text']}\n"
            context_parts.append(context_part)
        
        return "\n".join(context_parts)
    
    def answer_question(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        """
        Answer a question using RAG.
        
        Args:
            query: User question
            top_k: Number of documents to retrieve
            
        Returns:
            Dictionary with answer and retrieval information
        """
        # Retrieve relevant documents
        results = self.retrieve(query, top_k=top_k)
        
        if not results:
            return {
                "answer": "I don't have enough information to answer this question.",
                "sources": [],
                "has_context": False
            }
        
        # Format context
        context = self.format_context(results)
        
        # Generate answer
        answer = self.generation_chain.invoke({"context": context, "query": query})
        
        # Format sources for citation
        sources = []
        for result in results:
            doc = result["document"]
            source = doc["metadata"].get("source", "Unknown")
            page = doc["metadata"].get("page", "")
            score = result["score"]
            
            sources.append({
                "source": source,
                "page": page,
                "score": score
            })
        
        return {
            "answer": answer,
            "sources": sources,
            "has_context": True
        } 