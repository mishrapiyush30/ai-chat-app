import axios from 'axios';

// API URL - replace with your Flask backend URL or use a proxy in package.json
const API_URL = 'http://localhost:5002';

// Message interface
export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

// Metrics interface
export interface Metrics {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  latency: number;
  cost: number;
}

// API response interface
export interface ApiResponse {
  content: string;
  done?: boolean;
  error?: boolean;
  metrics?: Metrics;
}

// Create a new axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Function to stream chat completions
export const streamChatCompletion = async (
  messages: Message[],
  model: string = 'gpt-3.5-turbo',
  onData: (data: ApiResponse) => void,
  onError: (error: any) => void,
  onComplete: (metrics?: Metrics) => void
) => {
  try {
    const response = await fetch(`${API_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        messages,
        model,
        stream: true,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('Response body is null');
    }

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.substring(6)) as ApiResponse;
            
            if (data.error) {
              onError(new Error(data.content));
              break;
            } else if (data.done) {
              if (data.metrics) {
                onComplete(data.metrics);
              } else {
                onComplete();
              }
            } else if (data.content) {
              onData(data);
            }
          } catch (e) {
            console.error('Error parsing SSE data:', e);
          }
        }
      }
    }
  } catch (error) {
    onError(error);
  }
};

export interface ChatRequest {
  messages: Message[];
  model: string;
  temperature: number;
  max_tokens: number;
  stream: boolean;
}

export interface TokenMetrics {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
  estimatedCost: number;
  latency?: number;
}

export const sendMessage = async (
  messages: Message[],
  model: string,
  temperature: number,
  maxTokens: number,
  onChunk: (chunk: string) => void,
  onComplete: (metrics: TokenMetrics) => void
) => {
  try {
    const response = await fetch(`${API_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        messages,
        model,
        temperature,
        max_tokens: maxTokens,
        stream: true,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API error: ${response.status} - ${errorText}`);
    }

    if (!response.body) {
      throw new Error('ReadableStream not supported');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let metrics: TokenMetrics | null = null;

    const processStream = async () => {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        // Process complete JSON objects from the buffer
        let startIdx = 0;
        let endIdx = buffer.indexOf('\n', startIdx);

        while (endIdx !== -1) {
          const line = buffer.substring(startIdx, endIdx).trim();
          startIdx = endIdx + 1;

          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6);
            
            if (jsonStr === '[DONE]') {
              // Stream is done
              break;
            }

            try {
              const data = JSON.parse(jsonStr);
              
              if (data.choices && data.choices[0]?.delta?.content) {
                onChunk(data.choices[0].delta.content);
              } else if (data.metrics) {
                metrics = data.metrics;
              }
            } catch (err) {
              console.error('Error parsing JSON:', err);
            }
          }

          endIdx = buffer.indexOf('\n', startIdx);
        }

        // Keep the unprocessed part of the buffer
        buffer = buffer.substring(startIdx);
      }

      if (metrics) {
        onComplete(metrics);
      }
    };

    await processStream();
  } catch (error) {
    console.error('Error in sendMessage:', error);
    throw error;
  }
};

export const getAvailableModels = async () => {
  try {
    const response = await axios.get(`${API_URL}/api/models`);
    return response.data.models;
  } catch (error) {
    console.error('Error fetching models:', error);
    return ['gpt-3.5-turbo']; // Fallback to default model
  }
};

export default api; 