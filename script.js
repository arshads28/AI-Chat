// DOM elements
const chatWindow = document.getElementById('chat-window');
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');
const modelSelect = document.getElementById('model-select');
const sendButton = document.getElementById('send-button');
const newChatBtn = document.getElementById('new-chat-btn');
const chatHistory = document.getElementById('chat-history');
const chatTitle = document.getElementById('chat-title');
const sidebar = document.getElementById('sidebar');
const toggleSidebar = document.getElementById('toggle-sidebar');
const themeToggle = document.getElementById('theme-toggle');
const themeIcon = document.getElementById('theme-icon');
const themeText = document.getElementById('theme-text');

const overlay = document.getElementById('sidebar-overlay');
const body = document.body;

// --- NEW: Input container ---
const inputContainer = document.getElementById('input-container');

// Chat management
let currentThreadId = null;
let chats = {};

// Theme management
let isDarkMode = true;

// Toggle theme
themeToggle.addEventListener('click', () => {
    isDarkMode = !isDarkMode;
    document.body.classList.toggle('light-mode');
    
    if (isDarkMode) {
        themeText.textContent = 'Light Mode';
        themeIcon.innerHTML = `
            <circle cx="12" cy="12" r="5"></circle>
            <line x1="12" y1="1" x2="12" y2="3"></line>
            <line x1="12" y1="21" x2="12" y2="23"></line>
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
            <line x1="1" y1="12" x2="3" y2="12"></line>
            <line x1="21" y1="12" x2="23" y2="12"></line>
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
        `;
    } else {
        themeText.textContent = 'Dark Mode';
        themeIcon.innerHTML = `
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
        `;
    }
});

function closeMobileSidebar() {
    if (window.innerWidth <= 768) {
        sidebar.classList.add('is-closed');
        body.classList.remove('sidebar-open');
        overlay.classList.add('hidden');
    }
}

toggleSidebar.addEventListener('click', () => {
    sidebar.classList.toggle('is-closed');
    
    if (window.innerWidth <= 768) {
        body.classList.toggle('sidebar-open');
        overlay.classList.toggle('hidden');
    }
});

overlay.addEventListener('click', () => {
    closeMobileSidebar();
});

// --- UPDATED: Auto-resize textarea and container ---
messageInput.addEventListener('input', function() {
    this.style.height = 'auto'; // Reset height
    this.style.height = Math.min(this.scrollHeight, 192) + 'px'; // Set to scrollHeight or max
    
    // Check if scrollHeight (full content height) is greater than one line
    // 52px is a rough estimate for one line in this setup
    if (this.scrollHeight > 52) { 
        inputContainer.classList.remove('rounded-full');
        inputContainer.classList.add('rounded-3xl');
    } else {
        inputContainer.classList.add('rounded-full');
        inputContainer.classList.remove('rounded-3xl');
    }
});

// Handle Enter key
messageInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event('submit'));
    }
});

// Create new chat
function createNewChat() {
    const chatId = 'chat_' + Date.now();
    currentThreadId = null;
    
    chats[chatId] = {
        id: chatId,
        threadId: null,
        title: 'New Chat',
        messages: [],
        timestamp: Date.now()
    };
    
    loadChat(chatId);
    updateChatHistory();
    return chatId;
}

// Load a chat
function loadChat(chatId) {
    const chat = chats[chatId];
    if (!chat) return;
    
    currentThreadId = chat.threadId;
    chatTitle.textContent = chat.title;
    
    const container = chatWindow.querySelector('.max-w-3xl');
    container.innerHTML = `
        <div class="message-animation flex gap-4 mb-6">
            <div class="avatar assistant-avatar">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                </svg>
            </div>
            <div class="flex-1 space-y-2">
                <div class="prose prose-invert text-gray-100">
                    <p>Hello! I'm your AI assistant. How can I help you today?</p>
                </div>
            </div>
        </div>
    `;
    
    chat.messages.forEach(msg => {
        addMessage(msg.sender, msg.content, false);
    });
    
    updateChatHistory();
    closeMobileSidebar();
}

// Update chat history sidebar
function updateChatHistory() {
    chatHistory.innerHTML = '';
    const sortedChats = Object.values(chats).sort((a, b) => b.timestamp - a.timestamp);
    
    sortedChats.forEach(chat => {
        const chatItem = document.createElement('div');
        chatItem.className = `chat-item px-3 py-2 rounded-lg mb-1 flex items-center justify-between group ${chat.id === getCurrentChatId() ? 'active' : ''}`;
        chatItem.innerHTML = `
            <div class="flex items-center gap-2 flex-1 min-w-0">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                <span class="text-sm truncate">${chat.title}</span>
            </div>
            <button class="delete-chat opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-700 rounded" data-chat-id="${chat.id}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
            </button>
        `;
        
        chatItem.addEventListener('click', (e) => {
            if (!e.target.closest('.delete-chat')) {
                loadChat(chat.id);
            }
        });
        
        const deleteBtn = chatItem.querySelector('.delete-chat');
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteChat(chat.id);
        });
        
        chatHistory.appendChild(chatItem);
    });
}

// Delete chat
function deleteChat(chatId) {
    delete chats[chatId];
    if (getCurrentChatId() === chatId) {
        const remainingChats = Object.keys(chats);
        if (remainingChats.length > 0) {
            loadChat(remainingChats[0]);
        } else {
            createNewChat();
        }
    }
    updateChatHistory();
}

// Get current chat ID
function getCurrentChatId() {
    return Object.values(chats).find(chat => chat.threadId === currentThreadId)?.id || 
           Object.keys(chats)[Object.keys(chats).length - 1];
}

// Update chat title based on first message
function updateChatTitle(chatId, firstMessage) {
    if (chats[chatId]) {
        chats[chatId].title = firstMessage.substring(0, 30) + (firstMessage.length > 30 ? '...' : '');
        if (getCurrentChatId() === chatId) {
            chatTitle.textContent = chats[chatId].title;
        }
        updateChatHistory();
    }
}

// New chat button
newChatBtn.addEventListener('click', () => {
    createNewChat();
    messageInput.focus();
    closeMobileSidebar();
});

function addMessage(sender, message, isStreaming = false) {
    const container = chatWindow.querySelector('.max-w-3xl');
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message-animation', 'flex', 'gap-4', 'mb-6');
    
    const avatar = document.createElement('div');
    avatar.classList.add('avatar');
    
    if (sender === 'user') {
        avatar.classList.add('user-avatar');
        avatar.textContent = 'U';
    } else {
        avatar.classList.add('assistant-avatar');
        avatar.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
        `;
    }
    
    const content = document.createElement('div');
    content.classList.add('flex-1', 'space-y-2');
    
    const messageContent = document.createElement('div');
    messageContent.classList.add('prose', 'prose-invert', 'text-gray-100');
    
    if (sender === 'user') {
        messageContent.textContent = message;
    } else {
        if (isStreaming) {
                    messageContent.innerHTML = `
                        <span class="loading-cursor">
                            <svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                                <path d="M12 2L9.19 8.63L2 9.24L7.45 14L5.82 21L12 17.27L18.18 21L16.55 14L22 9.24L14.81 8.63L12 2Z"/>
                            </svg>
                        </span>`;
                } else {
            messageContent.innerHTML = marked.parse(message);
        }
    }
    
    content.appendChild(messageContent);
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    container.appendChild(messageDiv);
    
    chatWindow.scrollTop = chatWindow.scrollHeight;
    return messageContent;
}

async function handleSubmit(e) {
    e.preventDefault();
    
    const message = messageInput.value.trim();
    const modelName = modelSelect.value;
    if (!message) return;

    let chatId = getCurrentChatId();
    if (!chatId || !chats[chatId]) {
        chatId = createNewChat();
    }

    const chat = chats[chatId];
    
    chat.messages.push({ sender: 'user', content: message });
    
    if (chat.messages.length === 1) {
        updateChatTitle(chatId, message);
    }

    addMessage('user', message);
    
    messageInput.value = '';
    messageInput.style.height = 'auto';
    // --- UPDATED: Reset container shape ---
    inputContainer.classList.add('rounded-full');
    inputContainer.classList.remove('rounded-3xl');
    
    sendButton.disabled = true;
    messageInput.disabled = true;

    const assistantMessageDiv = addMessage('assistant', '', true);
    let fullResponse = "";

    try {
        const response = await fetch('/chat/', { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                input: message,
                model_name: modelName,
                thread_id: currentThreadId 
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.final_message) { 
            fullResponse = data.final_message;
        } else if (data.error) {
            fullResponse = `**Error:** ${data.error}`;
        } else {
            fullResponse = data.response || "Sorry, I received an empty response.";
        }

        if (data.thread_id) {
            currentThreadId = data.thread_id;
            chat.threadId = data.thread_id;
        }
        
        chat.messages.push({ sender: 'assistant', content: fullResponse });
        chat.timestamp = Date.now();
        
    } catch (err) {
        console.error('Fetch error:', err);
        fullResponse = `**Sorry, an error occurred:** ${err.message}`;
    } finally {
        assistantMessageDiv.innerHTML = marked.parse(fullResponse);
        chatWindow.scrollTop = chatWindow.scrollHeight;
        
        sendButton.disabled = false;
        messageInput.disabled = false;
        messageInput.focus();
    }
}

chatForm.addEventListener('submit', handleSubmit);

// --- SET DEFAULT STATE ---
sidebar.classList.add('is-closed'); // Start collapsed by default

createNewChat();
messageInput.focus();