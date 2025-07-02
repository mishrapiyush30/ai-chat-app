"""
Test script for the RAG system.

This script demonstrates how to use the RAG system to index documents and answer questions.
"""

import os
import sys
from dotenv import load_dotenv
from rag.models.rag_engine import RAGEngine

# Load environment variables
load_dotenv()

def main():
    """Main function to test the RAG system."""
    
    # Check if OpenAI API key is available
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not found in environment variables.")
        print("Using local models for embeddings and falling back to OpenAI for LLM.")
        use_openai_embeddings = False
    else:
        print("OpenAI API key found. Using OpenAI for embeddings and LLM.")
        use_openai_embeddings = True
    
    # Initialize RAG engine
    rag_engine = RAGEngine(
        use_openai_embeddings=use_openai_embeddings,
        embedding_model_name="all-MiniLM-L6-v2",  # Local model if not using OpenAI
        llm_model_name="gpt-3.5-turbo",
        temperature=0.7,
        chunk_size=500,
        chunk_overlap=50
    )
    
    # Check if data directory exists
    data_dir = "rag/data"
    if not os.path.exists(data_dir):
        print(f"Data directory {data_dir} not found.")
        return
    
    # Check if vector store exists
    vector_store_path = os.path.join(data_dir, "vector_store.index")
    if os.path.exists(vector_store_path):
        print("Loading existing vector store...")
        rag_engine.load_index(data_dir)
    else:
        print("Indexing documents...")
        rag_engine.index_documents(data_dir)
        rag_engine.save_index(data_dir)
    
    # Interactive question answering
    print("\n=== RAG Question Answering System ===")
    print("Type 'exit' to quit.")
    
    while True:
        query = input("\nEnter your question: ")
        
        if query.lower() in ["exit", "quit", "q"]:
            break
        
        print("\nSearching knowledge base...")
        response = rag_engine.answer_question(query, top_k=3)
        
        print("\n=== Answer ===")
        print(response["answer"])
        
        print("\n=== Sources ===")
        for i, source in enumerate(response["sources"]):
            source_name = source["source"]
            page = f", Page {source['page']}" if source["page"] else ""
            score = source["score"]
            print(f"[{i+1}] {source_name}{page} (Relevance: {score:.2f})")

if __name__ == "__main__":
    main() 