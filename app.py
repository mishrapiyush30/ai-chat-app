from flask import Flask, request, jsonify, render_template, Response, stream_with_context
from flask_cors import CORS
import os
import openai
from dotenv import load_dotenv
import json
import time
import requests

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, static_folder="static", template_folder="templates")
# Enable CORS for all routes
CORS(app)

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# RAG API URL
RAG_API_URL = os.getenv("RAG_API_URL", "http://localhost:5003")

# Available models
AVAILABLE_MODELS = {
    "gpt-3.5-turbo": "GPT-3.5 Turbo",
}

# Track token usage and cost
def calculate_cost(model, prompt_tokens, completion_tokens):
    costs = {
        "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
        "gpt-4": {"prompt": 0.03, "completion": 0.06},
    }
    
    if model in costs:
        prompt_cost = prompt_tokens * costs[model]["prompt"] / 1000
        completion_cost = completion_tokens * costs[model]["completion"] / 1000
        return prompt_cost + completion_cost
    return 0

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/models', methods=['GET'])
def get_models():
    return jsonify({"models": list(AVAILABLE_MODELS.keys())})

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    messages = data.get('messages', [])
    model = data.get('model', 'gpt-3.5-turbo')
    stream = data.get('stream', True)
    temperature = data.get('temperature', 0.7)
    max_tokens = data.get('max_tokens', 1000)
    use_rag = data.get('use_rag', False)
    
    # Force using gpt-3.5-turbo as default
    if model not in AVAILABLE_MODELS:
        model = 'gpt-3.5-turbo'
    
    if not messages:
        return jsonify({"error": "No messages provided"}), 400
    
    try:
        # If RAG is enabled, use the RAG API for the latest user message
        if use_rag and len(messages) > 0 and messages[-1]['role'] == 'user':
            user_query = messages[-1]['content']
            
            try:
                # Call RAG API
                rag_response = requests.post(
                    f"{RAG_API_URL}/api/rag/query",
                    json={"query": user_query, "top_k": 3},
                    timeout=10
                )
                
                if rag_response.status_code == 200:
                    rag_data = rag_response.json()
                    
                    if rag_data['status'] == 'success' and rag_data['has_context']:
                        # Format sources for citation
                        sources_text = "\n\nSources:\n"
                        for i, source in enumerate(rag_data['sources']):
                            source_name = source['source']
                            page = f", Page {source['page']}" if source['page'] else ""
                            sources_text += f"[{i+1}] {source_name}{page}\n"
                        
                        # For streaming response
                        if stream:
                            def generate():
                                # Send the RAG answer
                                answer = rag_data['answer']
                                answer_with_sources = answer + sources_text
                                
                                # Split into smaller chunks to simulate streaming
                                chunks = [answer_with_sources[i:i+10] for i in range(0, len(answer_with_sources), 10)]
                                
                                # Track tokens for cost calculation
                                prompt_tokens = len(user_query.split())
                                completion_tokens = len(answer_with_sources.split())
                                start_time = time.time()
                                
                                for chunk in chunks:
                                    data = {
                                        "choices": [{
                                            "delta": {
                                                "content": chunk
                                            }
                                        }]
                                    }
                                    yield f"data: {json.dumps(data)}\n\n"
                                    time.sleep(0.01)  # Simulate streaming delay
                                
                                # Calculate metrics
                                latency = time.time() - start_time
                                cost = calculate_cost(model, prompt_tokens, completion_tokens)
                                
                                # Send final message with metrics
                                final_data = {
                                    "metrics": {
                                        "promptTokens": prompt_tokens,
                                        "completionTokens": completion_tokens,
                                        "totalTokens": prompt_tokens + completion_tokens,
                                        "latency": round(latency, 2),
                                        "estimatedCost": round(cost, 6),
                                        "isRagResponse": True
                                    }
                                }
                                yield f"data: {json.dumps(final_data)}\n\n"
                                yield f"data: [DONE]\n\n"
                            
                            return Response(stream_with_context(generate()), content_type='text/event-stream')
                        else:
                            # Non-streaming RAG response
                            answer = rag_data['answer']
                            answer_with_sources = answer + sources_text
                            
                            prompt_tokens = len(user_query.split())
                            completion_tokens = len(answer_with_sources.split())
                            cost = calculate_cost(model, prompt_tokens, completion_tokens)
                            
                            return jsonify({
                                "choices": [{
                                    "message": {
                                        "content": answer_with_sources
                                    }
                                }],
                                "metrics": {
                                    "promptTokens": prompt_tokens,
                                    "completionTokens": completion_tokens,
                                    "totalTokens": prompt_tokens + completion_tokens,
                                    "estimatedCost": round(cost, 6),
                                    "isRagResponse": True
                                }
                            })
            
            except requests.exceptions.RequestException as e:
                print(f"Error connecting to RAG API: {str(e)}")
                # Fall back to standard OpenAI response
                pass
        
        # Standard OpenAI response (if RAG is disabled or failed)
        if stream:
            def generate():
                try:
                    response = openai.ChatCompletion.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stream=True
                    )
                    
                    # Track tokens for cost calculation
                    prompt_tokens = 0
                    completion_tokens = 0
                    start_time = time.time()
                    
                    for chunk in response:
                        if 'choices' in chunk and len(chunk['choices']) > 0:
                            if 'delta' in chunk['choices'][0] and 'content' in chunk['choices'][0]['delta']:
                                content = chunk['choices'][0]['delta']['content']
                                completion_tokens += len(content.split())
                                
                                # Format as SSE
                                data = {
                                    "choices": [{
                                        "delta": {
                                            "content": content
                                        }
                                    }]
                                }
                                yield f"data: {json.dumps(data)}\n\n"
                    
                    # Calculate metrics
                    latency = time.time() - start_time
                    cost = calculate_cost(model, prompt_tokens, completion_tokens)
                    
                    # Send final message with metrics
                    final_data = {
                        "metrics": {
                            "promptTokens": prompt_tokens,
                            "completionTokens": completion_tokens,
                            "totalTokens": prompt_tokens + completion_tokens,
                            "latency": round(latency, 2),
                            "estimatedCost": round(cost, 6),
                            "isRagResponse": False
                        }
                    }
                    yield f"data: {json.dumps(final_data)}\n\n"
                    yield f"data: [DONE]\n\n"
                
                except Exception as e:
                    error_data = {
                        "error": str(e)
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
            
            return Response(stream_with_context(generate()), content_type='text/event-stream')
        else:
            # Non-streaming response
            try:
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False
                )
                
                content = response['choices'][0]['message']['content']
                prompt_tokens = response['usage']['prompt_tokens']
                completion_tokens = response['usage']['completion_tokens']
                
                cost = calculate_cost(model, prompt_tokens, completion_tokens)
                
                return jsonify({
                    "choices": [{
                        "message": {
                            "content": content
                        }
                    }],
                    "metrics": {
                        "promptTokens": prompt_tokens,
                        "completionTokens": completion_tokens,
                        "totalTokens": prompt_tokens + completion_tokens,
                        "estimatedCost": round(cost, 6),
                        "isRagResponse": False
                    }
                })
            except Exception as e:
                return jsonify({
                    "error": str(e)
                }), 500
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/rag/health', methods=['GET'])
def rag_health():
    """Check if RAG API is available."""
    try:
        response = requests.get(f"{RAG_API_URL}/api/rag/health", timeout=5)
        if response.status_code == 200:
            return jsonify({"status": "ok", "message": "RAG API is available"})
        else:
            return jsonify({"status": "error", "message": "RAG API returned an error"}), 500
    except requests.exceptions.RequestException:
        return jsonify({"status": "error", "message": "RAG API is not available"}), 500

@app.route('/api/rag/index', methods=['POST'])
def rag_index():
    """Trigger document indexing in RAG API."""
    try:
        response = requests.post(f"{RAG_API_URL}/api/rag/index", timeout=30)
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"status": "error", "message": f"Error connecting to RAG API: {str(e)}"}), 500

if __name__ == '__main__':
    # Use port 5002 to avoid conflicts with AirPlay on macOS (port 5000)
    app.run(debug=True, port=5002) 