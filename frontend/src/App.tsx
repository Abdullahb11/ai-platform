import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE = 'http://localhost:8000';

interface Message {
  role: string;
  content: string;
}

function App() {
  const [conversations, setConversations] = useState<string[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load existing conversations on startup
  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      const res = await fetch(`${API_BASE}/conversations`);
      if (!res.ok) throw new Error('Failed to load conversations');
      const data = await res.json();
      setConversations(data.conversations);
    } catch {
      // Silently fail — backend may not be running yet
    }
  };

  const loadConversationMessages = async (conversationId: string) => {
    try {
      const res = await fetch(`${API_BASE}/conversations/${conversationId}`);
      if (!res.ok) throw new Error('Failed to load conversation');
      const data = await res.json();
      setMessages(data.messages);
    } catch {
      setMessages([]);
    }
  };

  const handleNewChat = async () => {
    try {
      const res = await fetch(`${API_BASE}/conversations`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to create conversation');
      const data = await res.json();
      const newId = data.conversation_id;

      setConversations(prev => [...prev, newId]);
      setActiveConversationId(newId);
      setMessages([]);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to create new conversation');
    }
  };

  const handleSelectConversation = async (conversationId: string) => {
    setActiveConversationId(conversationId);
    setError(null);
    await loadConversationMessages(conversationId);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || !activeConversationId) return;

    const userMessage = message.trim();
    setMessage('');
    setLoading(true);
    setError(null);

    // Optimistically show the user message
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation_id: activeConversationId, message: userMessage }),
      });

      if (!res.ok) {
        throw new Error(`Server responded with code: ${res.status}`);
      }

      const data = await res.json();
      setMessages(prev => [...prev, { role: 'model', content: data.response }]);
    } catch (err: any) {
      setError(err.message || 'Failed to connect to the backend server.');
      // Remove the optimistic user message on error
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (message.trim() && activeConversationId && !loading) {
        handleSubmit(e as unknown as React.FormEvent);
      }
    }
  };

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <h2 className="sidebar-title">Conversations</h2>
        </div>
        <button className="new-chat-btn" onClick={handleNewChat}>
          + New Chat
        </button>
        <div className="conversation-list">
          {conversations.map((id, index) => (
            <button
              key={id}
              className={`conversation-item ${id === activeConversationId ? 'active' : ''}`}
              onClick={() => handleSelectConversation(id)}
            >
              Conversation {index + 1}
            </button>
          ))}
          {conversations.length === 0 && (
            <p className="no-conversations">No conversations yet</p>
          )}
        </div>
      </aside>

      {/* Main Chat Area */}
      <div className="chat-area">
        <header>
          <h1 className="title">AI Platform</h1>
          <p className="subtitle">End-to-End Gemini Integration Test</p>
        </header>

        <main>
          {!activeConversationId ? (
            <div className="empty-state">
              <p>Create a new conversation to get started.</p>
            </div>
          ) : (
            <>
              {/* Message History */}
              <div className="messages-container">
                {messages.map((msg, index) => (
                  <div key={index} className={`message ${msg.role}`}>
                    <div className="message-role">{msg.role === 'user' ? 'You' : 'Gemini'}</div>
                    <div className="message-content">{msg.content}</div>
                  </div>
                ))}

                {loading && (
                  <div className="message model">
                    <div className="message-role">Gemini</div>
                    <div className="loading-indicator">
                      <div className="spinner"></div>
                      <span>Thinking...</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Error Display */}
              {error && (
                <div className="response-content error">{error}</div>
              )}

              {/* Input Form */}
              <form onSubmit={handleSubmit} className="chat-form">
                <div className="input-wrapper">
                  <textarea
                    className="prompt-input"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask Gemini anything..."
                    disabled={loading}
                  />
                </div>
                <button
                  type="submit"
                  className="send-btn"
                  disabled={loading || !message.trim()}
                >
                  {loading ? 'Sending...' : 'Send Message'}
                </button>
              </form>
            </>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
