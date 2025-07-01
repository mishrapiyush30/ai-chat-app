from flask import Flask, request, jsonify, render_template, Response, stream_with_context
from flask_cors import CORS
import os
import openai
from dotenv import load_dotenv
import json
import time

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, static_folder="static", template_folder="templates")
# Enable CORS for all routes
CORS(app)

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

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
    
    # Force using gpt-3.5-turbo as default
    if model not in AVAILABLE_MODELS:
        model = 'gpt-3.5-turbo'
    
    if not messages:
        return jsonify({"error": "No messages provided"}), 400
    
    try:
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
                            "estimatedCost": round(cost, 6)
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
                        "estimatedCost": round(cost, 6)
                    }
                })
            except Exception as e:
                return jsonify({
                    "error": str(e)
                }), 500
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Use port 5002 to avoid conflicts with AirPlay on macOS (port 5000)
    app.run(debug=True, port=5002) 