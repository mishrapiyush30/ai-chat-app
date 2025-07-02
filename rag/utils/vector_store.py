"""
Vector Store Module

This module handles storing and retrieving document embeddings using FAISS.
"""

import os
import json
import pickle
import numpy as np
import faiss
from typing import List, Dict, Any, Optional, Tuple

class VectorStore:
    """Class for storing and retrieving document embeddings."""
    
    def __init__(self, dimension: int = 384):
        """
        Initialize the VectorStore.
        
        Args:
            dimension: Dimension of the embedding vectors
        """
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)  # L2 distance
        self.documents = []  # Store document data
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of document chunks with text, metadata, and embeddings
        """
        if not documents:
            return
            
        # Extract embeddings
        embeddings = [np.array(doc["embedding"], dtype=np.float32) for doc in documents]
        embeddings_matrix = np.vstack(embeddings)
        
        # Add to FAISS index
        self.index.add(embeddings_matrix)
        
        # Store documents (without embeddings to save memory)
        for doc in documents:
            doc_copy = doc.copy()
            # Remove the embedding from stored document to save memory
            if "embedding" in doc_copy:
                del doc_copy["embedding"]
            self.documents.append(doc_copy)
    
    def search(self, query_embedding: List[float], top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Search for documents similar to the query embedding.
        
        Args:
            query_embedding: Embedding vector of the query
            top_k: Number of top results to return
            
        Returns:
            List of document chunks with similarity scores
        """
        if not self.documents:
            return []
            
        # Convert query embedding to numpy array
        query_embedding_np = np.array([query_embedding], dtype=np.float32)
        
        # Search the index
        distances, indices = self.index.search(query_embedding_np, min(top_k, len(self.documents)))
        
        # Get the documents for the indices
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.documents) and idx != -1:  # Check if index is valid
                doc = self.documents[idx]
                results.append({
                    "document": doc,
                    "score": float(1.0 / (1.0 + distances[0][i]))  # Convert distance to similarity score
                })
        
        # Sort by score (highest first)
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return results
    
    def save(self, directory: str, name: str = "vector_store") -> None:
        """
        Save the vector store to disk.
        
        Args:
            directory: Directory to save the vector store
            name: Base name for the saved files
        """
        os.makedirs(directory, exist_ok=True)
        
        # Save the FAISS index
        index_path = os.path.join(directory, f"{name}.index")
        faiss.write_index(self.index, index_path)
        
        # Save the documents
        docs_path = os.path.join(directory, f"{name}.docs")
        with open(docs_path, "wb") as f:
            pickle.dump(self.documents, f)
        
        # Save metadata (dimension, etc.)
        meta_path = os.path.join(directory, f"{name}.meta")
        with open(meta_path, "w") as f:
            json.dump({"dimension": self.dimension}, f)
    
    @classmethod
    def load(cls, directory: str, name: str = "vector_store") -> 'VectorStore':
        """
        Load a vector store from disk.
        
        Args:
            directory: Directory containing the vector store files
            name: Base name of the saved files
            
        Returns:
            Loaded VectorStore
        """
        # Load metadata
        meta_path = os.path.join(directory, f"{name}.meta")
        with open(meta_path, "r") as f:
            metadata = json.load(f)
        
        # Create instance
        instance = cls(dimension=metadata["dimension"])
        
        # Load FAISS index
        index_path = os.path.join(directory, f"{name}.index")
        instance.index = faiss.read_index(index_path)
        
        # Load documents
        docs_path = os.path.join(directory, f"{name}.docs")
        with open(docs_path, "rb") as f:
            instance.documents = pickle.load(f)
        
        return instance 