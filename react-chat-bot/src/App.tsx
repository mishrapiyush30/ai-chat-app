import React from 'react';
import { ChatProvider } from './context/ChatContext';
import Header from './components/Header';
import ChatWindow from './components/ChatWindow';
import ChatInput from './components/ChatInput';
import MetricsBar from './components/MetricsBar';
import Footer from './components/Footer';
import PromptDrawer from './components/PromptDrawer';

const App: React.FC = () => {
  return (
    <ChatProvider>
      <div className="flex flex-col h-screen">
        <Header />
        <main className="flex-1 flex flex-col overflow-hidden">
          <ChatWindow />
          <MetricsBar />
          <ChatInput />
        </main>
        <Footer />
        <PromptDrawer />
      </div>
    </ChatProvider>
  );
};

export default App; 