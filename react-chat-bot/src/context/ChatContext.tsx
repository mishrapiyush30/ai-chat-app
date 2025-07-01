import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Message, TokenMetrics, sendMessage, getAvailableModels } from '../services/api';

// Prompt templates
export const PROMPT_TEMPLATES = {
  GENERAL: {
    name: 'General',
    content: 'You are a helpful AI assistant. Answer the following question or respond to the following request:'
  },
  ELI5: {
    name: 'Explain Like I\'m 5',
    content: 'You are a helpful AI assistant. Explain the following concept in simple terms that a 5-year-old would understand:'
  },
  SUMMARIZE: {
    name: 'Summarize',
    content: 'You are a helpful AI assistant. Summarize the following text concisely while retaining the key points:'
  }
};

interface ChatContextType {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  metrics: TokenMetrics | null;
  models: string[];
  selectedModel: string;
  temperature: number;
  maxTokens: number;
  activePromptTemplate: keyof typeof PROMPT_TEMPLATES;
  sendUserMessage: (content: string) => Promise<void>;
  clearChat: () => void;
  setSelectedModel: (model: string) => void;
  setTemperature: (temp: number) => void;
  setMaxTokens: (tokens: number) => void;
  setActivePromptTemplate: (template: keyof typeof PROMPT_TEMPLATES) => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

interface ChatProviderProps {
  children: ReactNode;
}

export const ChatProvider: React.FC<ChatProviderProps> = ({ children }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<TokenMetrics | null>(null);
  const [models, setModels] = useState<string[]>(['gpt-3.5-turbo']);
  const [selectedModel, setSelectedModel] = useState('gpt-3.5-turbo');
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(1000);
  const [activePromptTemplate, setActivePromptTemplate] = useState<keyof typeof PROMPT_TEMPLATES>('GENERAL');

  // Load messages from localStorage on component mount
  useEffect(() => {
    const savedMessages = localStorage.getItem('chatMessages');
    if (savedMessages) {
      try {
        setMessages(JSON.parse(savedMessages));
      } catch (err) {
        console.error('Error parsing saved messages:', err);
      }
    }

    // Fetch available models
    getAvailableModels()
      .then(availableModels => {
        setModels(availableModels);
        // Set default model to GPT-4 if available, otherwise use GPT-3.5
        if (availableModels.includes('gpt-4')) {
          setSelectedModel('gpt-4');
        }
      })
      .catch(err => {
        console.error('Error fetching models:', err);
      });
  }, []);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    // Keep only the last 8 messages to avoid localStorage size limits
    const messagesToSave = messages.slice(-8);
    localStorage.setItem('chatMessages', JSON.stringify(messagesToSave));
  }, [messages]);

  const sendUserMessage = async (content: string) => {
    try {
      setError(null);
      setIsLoading(true);

      // Add system message with the selected prompt template
      const systemMessage: Message = {
        role: 'system',
        content: PROMPT_TEMPLATES[activePromptTemplate].content
      };

      // Add user message
      const userMessage: Message = { role: 'user', content };
      
      // Create a temporary assistant message for streaming
      const tempAssistantMessage: Message = { role: 'assistant', content: '' };
      
      // Update messages state with system, user, and empty assistant message
      setMessages(prev => [...prev, userMessage, tempAssistantMessage]);

      // Prepare messages for API call
      const apiMessages = [
        systemMessage,
        ...messages.slice(-6), // Include recent context (last 6 messages)
        userMessage
      ];

      let responseContent = '';

      // Send the request to the API
      await sendMessage(
        apiMessages,
        selectedModel,
        temperature,
        maxTokens,
        (chunk) => {
          // Update the assistant message content as chunks arrive
          responseContent += chunk;
          setMessages(prev => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              content: responseContent
            };
            return updated;
          });
        },
        (newMetrics) => {
          // Update metrics when complete
          setMetrics(newMetrics);
        }
      );

    } catch (err) {
      console.error('Error sending message:', err);
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
      
      // Update the assistant message with the error
      setMessages(prev => {
        const updated = [...prev];
        if (updated.length > 0 && updated[updated.length - 1].role === 'assistant') {
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            content: 'Sorry, an error occurred while processing your request. Please try again.'
          };
        }
        return updated;
      });
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setMetrics(null);
    setError(null);
  };

  const value = {
    messages,
    isLoading,
    error,
    metrics,
    models,
    selectedModel,
    temperature,
    maxTokens,
    activePromptTemplate,
    sendUserMessage,
    clearChat,
    setSelectedModel,
    setTemperature,
    setMaxTokens,
    setActivePromptTemplate
  };

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
};

export const useChatContext = () => {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChatContext must be used within a ChatProvider');
  }
  return context;
}; 