// This file is just a placeholder for the Flask app
// The actual chat functionality will be implemented in the React app
console.log('Flask app loaded');
console.log('React app should be running on port 3000');
console.log('Navigate to http://localhost:3000 to use the chat application');

// DOM Elements
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const messagesContainer = document.getElementById('messages-container');
const modelSelector = document.getElementById('model-selector');
const promptTemplates = document.querySelectorAll('.prompt-template');
const toggleDrawerBtn = document.getElementById('toggle-drawer');
const closeDrawerBtn = document.getElementById('close-drawer');
const promptDrawer = document.getElementById('prompt-drawer');
const fullPromptDisplay = document.getElementById('full-prompt');
const tokenCountDisplay = document.getElementById('token-count');
const latencyDisplay = document.getElementById('latency');
const costDisplay = document.getElementById('cost');
const sessionTokensDisplay = document.getElementById('session-tokens');
const sessionCostDisplay = document.getElementById('session-cost');
const exportChatBtn = document.getElementById('export-chat');

// State management
let conversation = [];
let activeTemplate = 'general';
let sessionTokens = 0;
let sessionCost = 0;
let currentlyStreaming = false;

// Load conversation from localStorage if available
function loadConversation() {
    const savedConversation = localStorage.getItem('chat-conversation');
    if (savedConversation) {
        try {
            conversation = JSON.parse(savedConversation);
            // Display the last 8 messages (sliding window)
            if (conversation.length > 0) {
                messagesContainer.innerHTML = ''; // Clear the welcome message
                const messagesToShow = conversation.slice(-8);
                messagesToShow.forEach(msg => {
                    appendMessage(msg.role, msg.content);
                });
            }
        } catch (e) {
            console.error('Failed to load conversation:', e);
            conversation = [];
        }
    }
}

// Save conversation to localStorage
function saveConversation() {
    // Keep only the last 8 messages (sliding window)
    const conversationToSave = conversation.slice(-8);
    localStorage.setItem('chat-conversation', JSON.stringify(conversationToSave));
}

// Prompt templates
const templates = {
    general: {
        prefix: '',
        system: 'You are a helpful AI assistant. Provide accurate and concise answers.'
    },
    explain: {
        prefix: 'Explain this in simple terms as if I\'m 5 years old: ',
        system: 'You are a helpful AI assistant that explains complex concepts in simple terms that a 5-year-old could understand. Use simple words, short sentences, and relatable examples.'
    },
    summarize: {
        prefix: 'Summarize the following text concisely: ',
        system: 'You are a helpful AI assistant that summarizes text. Create concise summaries that capture the main points while being significantly shorter than the original text.'
    }
};

// Initialize the app
function init() {
    loadConversation();
    updateSessionMetrics();
    setupEventListeners();
    
    // Auto-resize textarea
    userInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });

    // Disable GPT-4 option
    const gpt4Option = Array.from(modelSelector.options).find(option => option.value === 'gpt-4');
    if (gpt4Option) {
        gpt4Option.disabled = true;
        gpt4Option.text += ' (not available)';
    }
    modelSelector.value = 'gpt-3.5-turbo';
}

// Set up event listeners
function setupEventListeners() {
    // Form submission
    chatForm.addEventListener('submit', handleSubmit);
    
    // Model selection
    modelSelector.addEventListener('change', () => {
        if (modelSelector.value === 'gpt-4') {
            alert('GPT-4 is not available with your current API key. Using GPT-3.5-Turbo instead.');
            modelSelector.value = 'gpt-3.5-turbo';
        }
    });
    
    // Prompt templates
    promptTemplates.forEach(btn => {
        btn.addEventListener('click', () => {
            promptTemplates.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            activeTemplate = btn.dataset.template;
            userInput.placeholder = `Type your message here${templates[activeTemplate].prefix ? ' (will apply template)' : ''}...`;
        });
    });
    
    // Prompt drawer toggle
    toggleDrawerBtn.addEventListener('click', () => {
        promptDrawer.classList.toggle('hidden');
    });
    
    closeDrawerBtn.addEventListener('click', () => {
        promptDrawer.classList.add('hidden');
    });
    
    // Export chat
    exportChatBtn.addEventListener('click', exportChat);
}

// Handle form submission
async function handleSubmit(e) {
    e.preventDefault();
    
    const message = userInput.value.trim();
    if (!message || currentlyStreaming) return;
    
    // Apply template prefix if needed
    const prefix = templates[activeTemplate].prefix;
    const finalMessage = prefix ? `${prefix}${message}` : message;
    
    // Add user message to UI
    appendMessage('user', message);
    
    // Add to conversation history
    conversation.push({
        role: 'user',
        content: finalMessage
    });
    
    // Clear input
    userInput.value = '';
    userInput.style.height = 'auto';
    
    // Add typing indicator
    const typingIndicator = document.createElement('div');
    typingIndicator.className = 'flex justify-start mb-4';
    typingIndicator.innerHTML = `
        <div class="message assistant-message p-3 rounded-lg border">
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    messagesContainer.appendChild(typingIndicator);
    
    // Scroll to bottom
    scrollToBottom();
    
    // Prepare messages for API
    const messages = [
        {
            role: 'system',
            content: templates[activeTemplate].system
        },
        ...conversation
    ];
    
    // Update prompt drawer
    fullPromptDisplay.textContent = JSON.stringify(messages, null, 2);
    
    try {
        currentlyStreaming = true;
        await streamResponse(messages);
    } catch (error) {
        console.error('Error:', error);
        // Remove typing indicator
        messagesContainer.removeChild(typingIndicator);
        // Show error message
        appendMessage('assistant', `Sorry, there was an error processing your request: ${error.message}`);
    } finally {
        currentlyStreaming = false;
        // Save conversation
        saveConversation();
    }
}

// Stream response from API
async function streamResponse(messages) {
    const model = 'gpt-3.5-turbo'; // Force using GPT-3.5-turbo
    
    // Start streaming
    const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            messages,
            model,
            stream: true
        })
    });
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    // Remove typing indicator
    const typingIndicator = messagesContainer.lastChild;
    messagesContainer.removeChild(typingIndicator);
    
    // Create message container for streaming
    const messageDiv = document.createElement('div');
    messageDiv.className = 'flex justify-start mb-4';
    messageDiv.innerHTML = `
        <div class="message assistant-message p-3 rounded-lg border">
            <div class="message-content"></div>
        </div>
    `;
    messagesContainer.appendChild(messageDiv);
    
    const messageContent = messageDiv.querySelector('.message-content');
    let fullResponse = '';
    
    // Process the stream
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n\n');
        
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                try {
                    const data = JSON.parse(line.substring(6));
                    
                    if (data.error) {
                        fullResponse = data.content || "An error occurred while generating a response.";
                        messageContent.innerHTML = markdownToHtml(fullResponse);
                        scrollToBottom();
                        break;
                    } else if (data.done) {
                        // Update metrics
                        if (data.metrics) {
                            updateMetrics(data.metrics);
                        }
                    } else if (data.content) {
                        fullResponse += data.content;
                        messageContent.innerHTML = markdownToHtml(fullResponse);
                        scrollToBottom();
                    }
                } catch (e) {
                    console.error('Error parsing SSE data:', e);
                }
            }
        }
    }
    
    // Add to conversation history
    conversation.push({
        role: 'assistant',
        content: fullResponse
    });
    
    // Scroll to bottom one final time
    scrollToBottom();
}

// Append a message to the UI
function appendMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = role === 'user' ? 'flex justify-end mb-4' : 'flex justify-start mb-4';
    
    const messageClass = role === 'user' ? 'user-message' : 'assistant-message';
    
    messageDiv.innerHTML = `
        <div class="message ${messageClass} p-3 rounded-lg border">
            ${markdownToHtml(content)}
        </div>
    `;
    
    // If this is the first message, clear the container
    if (messagesContainer.querySelector('p')?.textContent === 'Start a conversation with the AI assistant') {
        messagesContainer.innerHTML = '';
    }
    
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

// Simple markdown to HTML converter
function markdownToHtml(text) {
    // Convert code blocks
    text = text.replace(/```([\s\S]*?)```/g, '<pre>$1</pre>');
    
    // Convert inline code
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // Convert bold text
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Convert italic text
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Convert line breaks
    text = text.replace(/\n/g, '<br>');
    
    return text;
}

// Scroll chat to bottom
function scrollToBottom() {
    const chatWindow = document.getElementById('chat-window');
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

// Update metrics displays
function updateMetrics(metrics) {
    // Update current message metrics
    tokenCountDisplay.textContent = metrics.total_tokens || 0;
    latencyDisplay.textContent = `${metrics.latency || 0} s`;
    costDisplay.textContent = `$${(metrics.cost || 0).toFixed(6)}`;
    
    // Update session metrics
    sessionTokens += metrics.total_tokens || 0;
    sessionCost += metrics.cost || 0;
    updateSessionMetrics();
}

// Update session metrics display
function updateSessionMetrics() {
    sessionTokensDisplay.textContent = sessionTokens;
    sessionCostDisplay.textContent = `$${sessionCost.toFixed(6)}`;
}

// Export chat to file
function exportChat() {
    if (conversation.length === 0) {
        alert('No conversation to export');
        return;
    }
    
    // Create JSON file
    const dataStr = JSON.stringify(conversation, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    
    // Create download link
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `chat-export-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Initialize the app when the DOM is loaded
document.addEventListener('DOMContentLoaded', init); 