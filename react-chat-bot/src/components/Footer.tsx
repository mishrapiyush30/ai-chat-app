import React from 'react';
import { useChatContext } from '../context/ChatContext';

const Footer: React.FC = () => {
  const { clearChat } = useChatContext();

  return (
    <footer className="bg-gray-100 border-t border-gray-200 py-3 px-4 text-center text-xs text-gray-500">
      <div className="flex justify-between items-center">
        <div>
          <button
            onClick={clearChat}
            className="px-3 py-1 bg-white text-red-600 border border-red-200 rounded-md hover:bg-red-50"
          >
            Clear Conversation
          </button>
        </div>
        <div>
          Powered by OpenAI API • {new Date().getFullYear()}
        </div>
        <div>
          <a
            href="https://github.com/yourusername/chat-bot"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-500 hover:text-blue-700"
          >
            GitHub
          </a>
        </div>
      </div>
    </footer>
  );
};

export default Footer; 