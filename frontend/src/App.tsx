import { useEffect, useRef, useState } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';
import './App.css';

const API_BASE = 'http://localhost:8000';
const ACTIVE_CONVERSATION_STORAGE_KEY = 'ai-platform.active-conversation-id';

interface Conversation {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

interface Message {
  id?: string;
  role: string;
  content: string;
  created_at?: string;
}

interface ConversationListResponse {
  items: Conversation[];
  next_cursor: string | null;
}

interface MessageListResponse {
  items: Message[];
  next_cursor: string | null;
}

interface ChatResponse {
  response: string;
  conversation_id: string;
}

function conversationLabel(conversation: Conversation): string {
  return conversation.title || 'Untitled conversation';
}

function App() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [message, setMessage] = useState('');
  const [conversationsLoading, setConversationsLoading] = useState(true);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [pendingChatViewVersion, setPendingChatViewVersion] = useState<number | null>(null);
  const [operationConversationId, setOperationConversationId] = useState<string | null>(null);
  const [renameConversationId, setRenameConversationId] = useState<string | null>(null);
  const [renameTitle, setRenameTitle] = useState('');
  const [error, setError] = useState<string | null>(null);

  const activeConversationIdRef = useRef<string | null>(null);
  const viewVersionRef = useRef(0);

  const setActiveConversation = (conversationId: string | null) => {
    activeConversationIdRef.current = conversationId;
    setActiveConversationId(conversationId);

    if (conversationId) {
      localStorage.setItem(ACTIVE_CONVERSATION_STORAGE_KEY, conversationId);
    } else {
      localStorage.removeItem(ACTIVE_CONVERSATION_STORAGE_KEY);
    }
  };

  const loadConversations = async (showError = true): Promise<Conversation[]> => {
    setConversationsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/conversations`);
      if (!response.ok) throw new Error('Unable to load conversations.');

      const data: ConversationListResponse = await response.json();
      setConversations(data.items);
      return data.items;
    } catch {
      if (showError) setError('Unable to load conversations. Please try again.');
      return [];
    } finally {
      setConversationsLoading(false);
    }
  };

  const selectConversation = async (conversationId: string) => {
    const viewVersion = ++viewVersionRef.current;
    setActiveConversation(conversationId);
    setMessages([]);
    setMessagesLoading(true);
    setError(null);
    setRenameConversationId(null);

    try {
      const response = await fetch(`${API_BASE}/conversations/${conversationId}/messages`);
      if (!response.ok) {
        if (response.status === 404 && viewVersionRef.current === viewVersion) {
          setActiveConversation(null);
          setMessages([]);
          setError('This conversation is no longer available.');
          void loadConversations(false);
          return;
        }
        throw new Error('Unable to load messages.');
      }

      const data: MessageListResponse = await response.json();
      if (viewVersionRef.current === viewVersion && activeConversationIdRef.current === conversationId) {
        setMessages(data.items);
      }
    } catch {
      if (viewVersionRef.current === viewVersion && activeConversationIdRef.current === conversationId) {
        setMessages([]);
        setError('Unable to load this conversation. Please try again.');
      }
    } finally {
      if (viewVersionRef.current === viewVersion) setMessagesLoading(false);
    }
  };

  useEffect(() => {
    const initialize = async () => {
      const items = await loadConversations();
      const savedConversationId = localStorage.getItem(ACTIVE_CONVERSATION_STORAGE_KEY);
      if (savedConversationId && items.some((conversation) => conversation.id === savedConversationId)) {
        await selectConversation(savedConversationId);
      }
    };
    void initialize();
  }, []);

  const handleNewChat = () => {
    ++viewVersionRef.current;
    setActiveConversation(null);
    setMessages([]);
    setMessage('');
    setMessagesLoading(false);
    setRenameConversationId(null);
    setError(null);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!message.trim() || chatLoading) return;

    const userMessage = message.trim();
    const requestedConversationId = activeConversationIdRef.current;
    const viewVersion = viewVersionRef.current;
    setMessage('');
    setChatLoading(true);
    setPendingChatViewVersion(viewVersion);
    setError(null);
    setMessages((currentMessages) => [...currentMessages, { role: 'user', content: userMessage }]);

    try {
      const body: { message: string; conversation_id?: string } = { message: userMessage };
      if (requestedConversationId) body.conversation_id = requestedConversationId;

      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!response.ok) throw new Error('Unable to send message.');

      const data: ChatResponse = await response.json();
      const viewIsCurrent = viewVersionRef.current === viewVersion;
      if (viewIsCurrent) {
        setActiveConversation(data.conversation_id);
        setMessages((currentMessages) => [
          ...currentMessages,
          { role: 'assistant', content: data.response },
        ]);
      }
      await loadConversations(viewIsCurrent);
    } catch {
      if (viewVersionRef.current === viewVersion) {
        setMessages((currentMessages) => currentMessages.slice(0, -1));
        setError('Unable to send your message. Please try again.');
      }
    } finally {
      setChatLoading(false);
      setPendingChatViewVersion(null);
    }
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      if (message.trim() && !chatLoading) void handleSubmit(event as unknown as FormEvent);
    }
  };

  const startRename = (conversation: Conversation) => {
    setRenameConversationId(conversation.id);
    setRenameTitle(conversation.title || '');
    setError(null);
  };

  const saveRename = async (event: FormEvent, conversationId: string) => {
    event.preventDefault();
    const title = renameTitle.trim();
    if (!title) {
      setError('A conversation title cannot be blank.');
      return;
    }

    setOperationConversationId(conversationId);
    try {
      const response = await fetch(`${API_BASE}/conversations/${conversationId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      });
      if (!response.ok) throw new Error('Unable to rename conversation.');

      const updatedConversation: Conversation = await response.json();
      setConversations((currentConversations) =>
        currentConversations.map((conversation) =>
          conversation.id === conversationId ? updatedConversation : conversation,
        ),
      );
      setRenameConversationId(null);
      setError(null);
    } catch {
      setError('Unable to rename this conversation. Please try again.');
    } finally {
      setOperationConversationId(null);
    }
  };

  const deleteConversation = async (conversationId: string) => {
    setOperationConversationId(conversationId);
    try {
      const response = await fetch(`${API_BASE}/conversations/${conversationId}`, {
        method: 'DELETE',
      });
      if (!response.ok && response.status !== 404) throw new Error('Unable to delete conversation.');

      setConversations((currentConversations) =>
        currentConversations.filter((conversation) => conversation.id !== conversationId),
      );
      if (activeConversationIdRef.current === conversationId) handleNewChat();
      setRenameConversationId((currentId) => (currentId === conversationId ? null : currentId));
      setError(null);
    } catch {
      setError('Unable to delete this conversation. Please try again.');
    } finally {
      setOperationConversationId(null);
    }
  };

  const activeChatIsLoading = chatLoading && pendingChatViewVersion === viewVersionRef.current;

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header"><h2 className="sidebar-title">Conversations</h2></div>
        <button className="new-chat-btn" onClick={handleNewChat}>+ New Chat</button>
        <div className="conversation-list" aria-busy={conversationsLoading}>
          {conversationsLoading && <p className="no-conversations">Loading conversations...</p>}
          {!conversationsLoading && conversations.length === 0 && (
            <p className="no-conversations">No conversations yet</p>
          )}
          {conversations.map((conversation) => {
            const isActive = conversation.id === activeConversationId;
            const isRenaming = conversation.id === renameConversationId;
            const isOperating = conversation.id === operationConversationId;
            return (
              <div key={conversation.id} className={`conversation-row ${isActive ? 'active' : ''}`}>
                {isRenaming ? (
                  <form className="rename-form" onSubmit={(event) => void saveRename(event, conversation.id)}>
                    <input
                      aria-label="Conversation title"
                      className="rename-input"
                      value={renameTitle}
                      onChange={(event) => setRenameTitle(event.target.value)}
                      maxLength={255}
                      autoFocus
                      disabled={isOperating}
                    />
                    <div className="rename-actions">
                      <button className="sidebar-action" type="submit" disabled={isOperating}>Save</button>
                      <button className="sidebar-action" type="button" onClick={() => setRenameConversationId(null)} disabled={isOperating}>Cancel</button>
                    </div>
                  </form>
                ) : (
                  <>
                    <button
                      className="conversation-item"
                      onClick={() => void selectConversation(conversation.id)}
                      disabled={isOperating}
                      title={conversationLabel(conversation)}
                    >
                      {conversationLabel(conversation)}
                    </button>
                    <div className="conversation-actions">
                      <button
                        className="icon-action"
                        onClick={() => startRename(conversation)}
                        aria-label={`Rename ${conversationLabel(conversation)}`}
                        title="Rename conversation"
                        disabled={isOperating}
                      >Rename</button>
                      <button
                        className="icon-action delete-action"
                        onClick={() => void deleteConversation(conversation.id)}
                        aria-label={`Delete ${conversationLabel(conversation)}`}
                        title="Delete conversation"
                        disabled={isOperating}
                      >Delete</button>
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </aside>

      <div className="chat-area">
        <header>
          <h1 className="title">AI Platform</h1>
          <p className="subtitle">End-to-End Gemini Integration Test</p>
        </header>

        <main>
          <div className="messages-container" aria-busy={messagesLoading}>
            {messagesLoading && <div className="empty-state"><p>Loading conversation...</p></div>}
            {!messagesLoading && messages.length === 0 && !activeChatIsLoading && (
              <div className="empty-state"><p>Send a message to start a conversation.</p></div>
            )}
            {!messagesLoading && messages.map((item, index) => (
              <div key={item.id || `${item.role}-${index}`} className={`message ${item.role}`}>
                <div className="message-role">{item.role === 'user' ? 'You' : 'Gemini'}</div>
                <div className="message-content">{item.content}</div>
              </div>
            ))}
            {activeChatIsLoading && (
              <div className="message assistant">
                <div className="message-role">Gemini</div>
                <div className="loading-indicator"><div className="spinner"></div><span>Thinking...</span></div>
              </div>
            )}
          </div>

          {error && <div className="response-content error" role="alert">{error}</div>}

          <form onSubmit={handleSubmit} className="chat-form">
            <div className="input-wrapper">
              <textarea
                className="prompt-input"
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask Gemini anything..."
                disabled={chatLoading}
              />
            </div>
            <button type="submit" className="send-btn" disabled={chatLoading || !message.trim()}>
              {chatLoading ? 'Sending...' : 'Send Message'}
            </button>
          </form>
        </main>
      </div>
    </div>
  );
}

export default App;
