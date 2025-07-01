import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Message } from '../services/api';

interface ChatMessageProps {
  message: Message;
  isLoading?: boolean;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message, isLoading = false }) => {
  const isUser = message.role === 'user';
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`message p-3 border rounded-lg ${
          isUser ? 'user-message' : 'assistant-message'
        } max-w-3xl`}
      >
        {isLoading && !isUser && message.content === '' ? (
          <div className="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        ) : (
          <ReactMarkdown>
            {message.content}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
};

export default ChatMessage; 