"""
Document Processor Module

This module handles loading documents from various formats and chunking them for embedding.
"""

import os
from typing import List, Dict, Any, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, PyPDFLoader

class DocumentProcessor:
    """Class for loading and processing documents."""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        Initialize the DocumentProcessor.
        
        Args:
            chunk_size: The size of text chunks for splitting documents
            chunk_overlap: The overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
    
    def load_document(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Load a document from a file path.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            List of document chunks with text and metadata
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_ext == '.pdf':
                loader = PyPDFLoader(file_path)
                documents = loader.load()
            elif file_ext == '.txt':
                loader = TextLoader(file_path)
                documents = loader.load()
            else:
                raise ValueError(f"Unsupported file format: {file_ext}")
            
            # Extract filename for metadata
            filename = os.path.basename(file_path)
            
            # Add metadata to documents
            for doc in documents:
                if not doc.metadata:
                    doc.metadata = {}
                doc.metadata["source"] = filename
            
            # Split documents into chunks
            chunks = self.text_splitter.split_documents(documents)
            
            # Convert to dictionary format for easier handling
            processed_chunks = []
            for i, chunk in enumerate(chunks):
                processed_chunks.append({
                    "id": f"{filename}-chunk-{i}",
                    "text": chunk.page_content,
                    "metadata": {
                        "source": chunk.metadata.get("source", filename),
                        "page": chunk.metadata.get("page", None),
                        "chunk_id": i
                    }
                })
            
            return processed_chunks
            
        except Exception as e:
            print(f"Error loading document {file_path}: {str(e)}")
            return []
    
    def load_documents_from_directory(self, directory_path: str, 
                                      file_extensions: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Load all documents from a directory.
        
        Args:
            directory_path: Path to the directory containing documents
            file_extensions: List of file extensions to include (e.g., ['.pdf', '.txt'])
            
        Returns:
            List of document chunks with text and metadata
        """
        if file_extensions is None:
            file_extensions = ['.pdf', '.txt']
            
        all_chunks = []
        
        for filename in os.listdir(directory_path):
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext in file_extensions:
                file_path = os.path.join(directory_path, filename)
                chunks = self.load_document(file_path)
                all_chunks.extend(chunks)
        
        return all_chunks 