"""
Flask API for the RAG system.

This module provides API endpoints for the RAG system to be used by the chat application.
"""

import os
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from .models.rag_engine import RAGEngine

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Initialize RAG engine
use_openai_embeddings = os.getenv("OPENAI_API_KEY") is not None
rag_engine = RAGEngine(
    use_openai_embeddings=use_openai_embeddings,
    embedding_model_name="all-MiniLM-L6-v2",
    llm_model_name="gpt-3.5-turbo",
    temperature=0.7,
    chunk_size=500,
    chunk_overlap=50
)

# Data directory
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

@app.route("/api/rag/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "ok", "message": "RAG API is running"})

@app.route("/api/rag/index", methods=["POST"])
def index_documents():
    """
    Index documents from the data directory.
    
    Returns:
        JSON response with status and message
    """
    try:
        # Check if data directory exists
        if not os.path.exists(DATA_DIR):
            return jsonify({
                "status": "error",
                "message": f"Data directory {DATA_DIR} not found"
            }), 404
        
        # Index documents
        rag_engine.index_documents(DATA_DIR)
        
        # Save index
        rag_engine.save_index(DATA_DIR)
        
        return jsonify({
            "status": "success",
            "message": "Documents indexed successfully"
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error indexing documents: {str(e)}"
        }), 500

@app.route("/api/rag/query", methods=["POST"])
def query():
    """
    Query the RAG system.
    
    Request body:
        query: User query
        top_k: (optional) Number of documents to retrieve
    
    Returns:
        JSON response with answer and sources
    """
    try:
        # Parse request
        data = request.json
        if not data or "query" not in data:
            return jsonify({
                "status": "error",
                "message": "Missing required parameter: query"
            }), 400
        
        query = data["query"]
        top_k = data.get("top_k", 3)
        
        # Check if vector store exists, if not, index documents
        vector_store_path = os.path.join(DATA_DIR, "vector_store.index")
        if not os.path.exists(vector_store_path):
            rag_engine.index_documents(DATA_DIR)
            rag_engine.save_index(DATA_DIR)
        else:
            # Load existing index if not already loaded
            if len(rag_engine.vector_store.documents) == 0:
                rag_engine.load_index(DATA_DIR)
        
        # Answer question
        response = rag_engine.answer_question(query, top_k=top_k)
        
        return jsonify({
            "status": "success",
            "answer": response["answer"],
            "sources": response["sources"],
            "has_context": response["has_context"]
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error processing query: {str(e)}"
        }), 500

def create_app():
    """Create and configure the Flask app."""
    return app

if __name__ == "__main__":
    # Run the app
    app.run(debug=True, port=5003) 