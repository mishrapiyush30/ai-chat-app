"""
Script to run the RAG API.
"""

import os
from rag.api import app

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get("RAG_API_PORT", 5003))
    
    # Run the app
    app.run(debug=True, host="0.0.0.0", port=port) 