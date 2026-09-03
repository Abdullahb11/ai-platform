import { useEffect, useRef, useState } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';
import './App.css';

const API_BASE = 'http://localhost:8000';
const ACTIVE_CONVERSATION_STORAGE_KEY = 'ai-platform.active-conversation-id';

// ── API types ────────────────────────────────────────────────────────────────

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

// ── Context window types ──────────────────────────────────────────────────────

/** Per-phase context view (request or current). */
interface ContextWindowDetail {
  token_count: number;
  percent_used: number;
  start_message_id: string | null;
  end_message_id: string | null;
  message_count: number;
}

/** Full context metadata from POST /chat. */
interface ContextInfo {
  limit_tokens: number;
  request: ContextWindowDetail;
  current: ContextWindowDetail;
  snapshot_id?: string | null;
}

/** Single snapshot entry from GET /conversations/{id}/context. */
interface ContextSnapshot {
  id: string;
  conversation_id: string;
  // Request context
  request_message_id: string | null;
  assistant_message_id: string | null;
  request_start_message_id: string | null;
  request_end_message_id: string | null;
  request_token_count: number;
  // Post-response / current context
  current_start_message_id: string | null;
  current_end_message_id: string | null;
  current_token_count: number;
  // Shared
  context_limit_tokens: number;
  created_at: string;
}

interface ContextHistoryResponse {
  latest: ContextSnapshot | null;
  snapshots: ContextSnapshot[];
}

// ── Gemini generation usage ───────────────────────────────────────────────────

interface UsageMetadata {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}

interface ChatResponse {
  response: string;
  conversation_id: string;
  usage?: UsageMetadata;
  context?: ContextInfo;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function conversationLabel(conversation: Conversation): string {
  return conversation.title || 'Untitled conversation';
}

function getUsageColor(percent: number): string {
  if (percent < 60) return 'var(--accent-green)';
  if (percent < 85) return 'var(--accent-yellow)';
  return 'var(--accent-red)';
}

function shortMessagePreview(content: string, maxLen = 60): string {
  const trimmed = content.trim();
  return trimmed.length > maxLen ? trimmed.slice(0, maxLen) + '…' : trimmed;
}

function pct(count: number, limit: number): number {
  return Math.min(Math.round((count / limit) * 1000) / 10, 100);
}

/** Derive ContextInfo from a ContextSnapshot for display on conversation load. */
function contextInfoFromSnapshot(snap: ContextSnapshot): ContextInfo {
  const limit = snap.context_limit_tokens;
  return {
    limit_tokens: limit,
    request: {
      token_count: snap.request_token_count,
      percent_used: pct(snap.request_token_count, limit),
      start_message_id: snap.request_start_message_id,
      end_message_id: snap.request_end_message_id,
      message_count: 0, // not stored; computed from messages in panel
    },
    current: {
      token_count: snap.current_token_count,
      percent_used: pct(snap.current_token_count, limit),
      start_message_id: snap.current_start_message_id,
      end_message_id: snap.current_end_message_id,
      message_count: 0, // not stored; computed from messages in panel
    },
    snapshot_id: snap.id,
  };
}

/** Slice messages between start_id and end_id (inclusive). */
function messagesInRange(
  messages: Message[],
  start_id: string | null,
  end_id: string | null,
): Message[] {
  if (!end_id) return [];
  const endIdx = messages.findIndex((m) => m.id === end_id);
  if (endIdx === -1) return [];
  if (!start_id) return messages.slice(0, endIdx + 1);
  const startIdx = messages.findIndex((m) => m.id === start_id);
  if (startIdx === -1) return messages.slice(0, endIdx + 1);
  return messages.slice(startIdx, endIdx + 1);
}

// ── App ───────────────────────────────────────────────────────────────────────

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

  // ── Context state ───────────────────────────────────────────────────────────
  /** Latest context info — derived from chat response or on conversation load. */
  const [activeContextInfo, setActiveContextInfo] = useState<ContextInfo | null>(null);
  /** Full snapshot history for the active conversation. */
  const [contextSnapshots, setContextSnapshots] = useState<ContextSnapshot[]>([]);
  const [contextPanelOpen, setContextPanelOpen] = useState(false);

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

  const loadContextHistory = async (conversationId: string, viewVersion: number) => {
    try {
      const response = await fetch(`${API_BASE}/conversations/${conversationId}/context`);
      if (!response.ok) return;
      const data: ContextHistoryResponse = await response.json();
      if (
        viewVersionRef.current === viewVersion &&
        activeConversationIdRef.current === conversationId
      ) {
        setContextSnapshots(data.snapshots);
        setActiveContextInfo(data.latest ? contextInfoFromSnapshot(data.latest) : null);
      }
    } catch {
      // Non-critical — new conversations legitimately have no snapshots yet
    }
  };

  const selectConversation = async (conversationId: string) => {
    const viewVersion = ++viewVersionRef.current;
    setActiveConversation(conversationId);
    setMessages([]);
    setMessagesLoading(true);
    setError(null);
    setRenameConversationId(null);
    setActiveContextInfo(null);
    setContextSnapshots([]);
    setContextPanelOpen(false);

    try {
      const [msgResponse] = await Promise.all([
        fetch(`${API_BASE}/conversations/${conversationId}/messages`),
        loadContextHistory(conversationId, viewVersion),
      ]);

      if (!msgResponse.ok) {
        if (msgResponse.status === 404 && viewVersionRef.current === viewVersion) {
          setActiveConversation(null);
          setMessages([]);
          setError('This conversation is no longer available.');
          void loadConversations(false);
          return;
        }
        throw new Error('Unable to load messages.');
      }

      const data: MessageListResponse = await msgResponse.json();
      if (
        viewVersionRef.current === viewVersion &&
        activeConversationIdRef.current === conversationId
      ) {
        setMessages(data.items);
      }
    } catch {
      if (
        viewVersionRef.current === viewVersion &&
        activeConversationIdRef.current === conversationId
      ) {
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
      const savedId = localStorage.getItem(ACTIVE_CONVERSATION_STORAGE_KEY);
      if (savedId && items.some((c) => c.id === savedId)) {
        await selectConversation(savedId);
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
    setActiveContextInfo(null);
    setContextSnapshots([]);
    setContextPanelOpen(false);
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
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);

    try {
      const body: { message: string; conversation_id?: string } = { message: userMessage };
      if (requestedConversationId) body.conversation_id = requestedConversationId;

      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        const detail = (errData as { detail?: string }).detail;
        if ((response.status === 422 || response.status === 503) && detail) {
          throw new Error(detail);
        }
        throw new Error('Unable to send message.');
      }

      const data: ChatResponse = await response.json();
      const viewIsCurrent = viewVersionRef.current === viewVersion;
      if (viewIsCurrent) {
        setActiveConversation(data.conversation_id);

        // Patch optimistic messages with their real persisted UUIDs.
        // handleSubmit added the user message without an id (optimistic), and
        // the assistant response below also starts without an id. messagesInRange
        // uses m.id === end_message_id for context reconstruction, so both IDs
        // must be present in state before ContextInfo is applied.
        const userMsgId = data.context?.request.end_message_id ?? undefined;
        const assistantMsgId = data.context?.current.end_message_id ?? undefined;

        setMessages((prev) => {
          // The last entry is the optimistic user message (no id yet).
          const patched = prev.map((m, i) =>
            i === prev.length - 1 && m.role === 'user' && !m.id
              ? { ...m, id: userMsgId }
              : m
          );
          // Append the assistant message with its real id.
          return [...patched, { role: 'assistant', content: data.response, id: assistantMsgId }];
        });

        if (data.context) {
          setActiveContextInfo(data.context);
          // Reload snapshot history to keep panel up to date
          void loadContextHistory(data.conversation_id, viewVersionRef.current);
        }
      }
      await loadConversations(viewIsCurrent);
    } catch (err) {
      if (viewVersionRef.current === viewVersion) {
        setMessages((prev) => prev.slice(0, -1));
        setError(
          err instanceof Error ? err.message : 'Unable to send your message. Please try again.',
        );
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
      const updated: Conversation = await response.json();
      setConversations((prev) => prev.map((c) => (c.id === conversationId ? updated : c)));
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
      if (!response.ok && response.status !== 404) throw new Error('Unable to delete.');
      setConversations((prev) => prev.filter((c) => c.id !== conversationId));
      if (activeConversationIdRef.current === conversationId) handleNewChat();
      setRenameConversationId((id) => (id === conversationId ? null : id));
      setError(null);
    } catch {
      setError('Unable to delete this conversation. Please try again.');
    } finally {
      setOperationConversationId(null);
    }
  };

  // ── Context-window derived data ────────────────────────────────────────────

  const activeChatIsLoading = chatLoading && pendingChatViewVersion === viewVersionRef.current;

  // Current context is the active state that matters to the user
  const currentCtx = activeContextInfo?.current ?? null;
  const requestCtx = activeContextInfo?.request ?? null;
  const limitTokens = activeContextInfo?.limit_tokens ?? 0;

  // Messages within current active context window.
  // messagesInRange works by finding persisted message IDs in the messages array.
  // After handleSubmit, optimistic messages are patched with real IDs before
  // ContextInfo is applied, so this lookup is always reliable.
  const currentContextMessages = currentCtx
    ? messagesInRange(messages, currentCtx.start_message_id, currentCtx.end_message_id)
    : [];

  // Messages within request context window (for panel detail).
  const requestContextMessages = requestCtx
    ? messagesInRange(messages, requestCtx.start_message_id, requestCtx.end_message_id)
    : [];

  // Reliable message counts: use the dynamic array length when IDs resolved
  // correctly; fall back to the API-provided message_count otherwise (e.g. a
  // brief render cycle before the state update settles).
  const currentMessageCount =
    currentContextMessages.length > 0
      ? currentContextMessages.length
      : (currentCtx?.message_count ?? 0);
  const requestMessageCount =
    requestContextMessages.length > 0
      ? requestContextMessages.length
      : (requestCtx?.message_count ?? 0);

  const currentStartMessage =
    currentCtx?.start_message_id
      ? messages.find((m) => m.id === currentCtx.start_message_id) ?? null
      : null;

  // A message is outside the current context window only when:
  //   - we have context info (currentCtx exists)
  //   - the message has a persisted id (not a pre-ID-patch optimistic message)
  //   - currentContextMessages is non-empty (IDs resolved successfully)
  //   - this specific message id is not in that set
  const currentContextIdSet = new Set(currentContextMessages.map((m) => m.id));
  const contextResolved = currentContextMessages.length > 0;

  // Messages in full history that are outside current context window
  const outsideContextCount =
    contextResolved ? messages.length - currentContextMessages.length : 0;

  return (
    <div className="app-layout">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <h2 className="sidebar-title">Conversations</h2>
        </div>
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
                  <form className="rename-form" onSubmit={(e) => void saveRename(e, conversation.id)}>
                    <input
                      aria-label="Conversation title"
                      className="rename-input"
                      value={renameTitle}
                      onChange={(e) => setRenameTitle(e.target.value)}
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
                      <button className="icon-action" onClick={() => startRename(conversation)} aria-label={`Rename ${conversationLabel(conversation)}`} title="Rename" disabled={isOperating}>Rename</button>
                      <button className="icon-action delete-action" onClick={() => void deleteConversation(conversation.id)} aria-label={`Delete ${conversationLabel(conversation)}`} title="Delete" disabled={isOperating}>Delete</button>
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </aside>

      {/* ── Chat area ── */}
      <div className="chat-area">
        <header>
          <h1 className="title">AI Platform</h1>
          <p className="subtitle">End-to-End Gemini Integration Test</p>
        </header>

        <main>
          {/* Messages — ALWAYS show full DB history, even for messages outside context */}
          <div className="messages-container" aria-busy={messagesLoading}>
            {messagesLoading && <div className="empty-state"><p>Loading conversation...</p></div>}
            {!messagesLoading && messages.length === 0 && !activeChatIsLoading && (
              <div className="empty-state"><p>Send a message to start a conversation.</p></div>
            )}
            {!messagesLoading && messages.map((item, index) => {
              // A message is out-of-context only when IDs have resolved (contextResolved)
              // and this message's id is not in the current context window set.
              // Messages without an id (brief pre-patch window) are never labelled.
              const isOutOfCtx =
                contextResolved && !!item.id && !currentContextIdSet.has(item.id);
              return (
                <div
                  key={item.id || `${item.role}-${index}`}
                  className={`message ${item.role}${isOutOfCtx ? ' out-of-context' : ''}`}
                  title={isOutOfCtx ? 'This message is in the full conversation history but outside the current model context window' : undefined}
                >
                  <div className="message-role">
                    {item.role === 'user' ? 'You' : 'Gemini'}
                    {isOutOfCtx && <span className="out-of-ctx-badge" title="Outside model context">↑ history</span>}
                  </div>
                  <div className="message-content">{item.content}</div>
                </div>
              );
            })}
            {activeChatIsLoading && (
              <div className="message assistant">
                <div className="message-role">Gemini</div>
                <div className="loading-indicator"><div className="spinner"></div><span>Thinking...</span></div>
              </div>
            )}
          </div>

          {error && <div className="response-content error" role="alert">{error}</div>}

          {/* ── Context Indicator — shows CURRENT (post-response) context ── */}
          {currentCtx && (
            <button
              id="context-indicator"
              className="context-indicator"
              onClick={() => setContextPanelOpen((o) => !o)}
              title="Click to inspect context window"
              aria-expanded={contextPanelOpen}
            >
              <div className="context-indicator-top">
                <span className="context-label">Active context</span>
                <span
                  className="context-percent"
                  style={{ color: getUsageColor(currentCtx.percent_used) }}
                >
                  {currentCtx.percent_used}%
                </span>
              </div>
              <div className="context-bar-track">
                <div
                  className="context-bar-fill"
                  style={{
                    width: `${currentCtx.percent_used}%`,
                    background: getUsageColor(currentCtx.percent_used),
                  }}
                />
              </div>
              <div className="context-tokens">
                {currentCtx.token_count.toLocaleString()} / {limitTokens.toLocaleString()} tokens
              </div>
            </button>
          )}

          <form onSubmit={handleSubmit} className="chat-form">
            <div className="input-wrapper">
              <textarea
                className="prompt-input"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
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

      {/* ── Context Inspection Panel ── */}
      {contextPanelOpen && activeContextInfo && (
        <div className="context-panel-overlay" onClick={() => setContextPanelOpen(false)}>
          <div
            className="context-panel"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-label="Context window inspection"
          >
            <div className="context-panel-header">
              <h2 className="context-panel-title">Context Window</h2>
              <button className="context-panel-close" onClick={() => setContextPanelOpen(false)} aria-label="Close">✕</button>
            </div>

            {/* ── Configured limit ── */}
            <div className="context-config-row">
              <span className="ctx-config-label">Configured limit</span>
              <span className="ctx-config-value">{limitTokens.toLocaleString()} tokens</span>
            </div>

            {/* ── Current (post-response) context — primary view ── */}
            <div className="context-section">
              <div className="context-section-label">Current active context</div>
              <div className="context-summary">
                <div className="context-summary-bar-track">
                  <div
                    className="context-summary-bar-fill"
                    style={{
                      width: `${currentCtx!.percent_used}%`,
                      background: getUsageColor(currentCtx!.percent_used),
                    }}
                  />
                </div>
                <div className="context-summary-stats">
                  <span style={{ color: getUsageColor(currentCtx!.percent_used) }}>
                    {currentCtx!.percent_used}%
                  </span>
                  <span className="context-summary-tokens">
                    {currentCtx!.token_count.toLocaleString()} / {limitTokens.toLocaleString()} tokens
                  </span>
                </div>
              </div>

              {/* Starts from */}
              {currentStartMessage && (
                <div className="context-start-message">
                  <span className="ctx-msg-role">{currentStartMessage.role === 'user' ? 'You' : 'Gemini'}</span>
                  <span className="ctx-msg-preview">Starts from: "{shortMessagePreview(currentStartMessage.content)}"</span>
                </div>
              )}

              {/* Messages in current context */}
              <div className="context-messages-list">
                {currentContextMessages.length === 0 && currentMessageCount === 0 && (
                  <p className="ctx-empty">Send a message to see the active context.</p>
                )}
                {currentContextMessages.length === 0 && currentMessageCount > 0 && (
                  <p className="ctx-empty">
                    {currentMessageCount} message{currentMessageCount !== 1 ? 's' : ''} in context
                    — switch conversations and back to reload message details.
                  </p>
                )}
                {currentContextMessages.map((msg, i) => (
                  <div key={msg.id || i} className="ctx-msg-item">
                    <span className="ctx-msg-role">{msg.role === 'user' ? 'You' : 'Gemini'}</span>
                    <span className="ctx-msg-preview">{shortMessagePreview(msg.content, 120)}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Truncation note */}
            {outsideContextCount > 0 && (
              <div className="context-history-note">
                ⚠ {outsideContextCount} earlier message{outsideContextCount !== 1 ? 's' : ''} exist in the full DB history but are outside the current model context window. They are shown above with a "↑ history" label and will not be sent to Gemini.
              </div>
            )}

            {/* ── Request context for last generation ── */}
            {requestCtx && (
              <div className="context-section">
                <div className="context-section-label">Last request context (sent to Gemini)</div>
                <div className="ctx-request-summary">
                  <div className="ctx-snapshot-bar-track">
                    <div
                      className="ctx-snapshot-bar-fill"
                      style={{
                        width: `${requestCtx.percent_used}%`,
                        background: getUsageColor(requestCtx.percent_used),
                      }}
                    />
                  </div>
                  <div className="ctx-snapshot-stats">
                    <span style={{ color: getUsageColor(requestCtx.percent_used) }}>
                      {requestCtx.percent_used}%
                    </span>
                    <span>
                      {requestCtx.token_count.toLocaleString()} / {limitTokens.toLocaleString()} tokens
                      &nbsp;·&nbsp; {requestMessageCount} message{requestMessageCount !== 1 ? 's' : ''}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* ── Snapshot history ── */}
            {contextSnapshots.length > 0 && (
              <div className="context-section">
                <div className="context-section-label">
                  Context history — {contextSnapshots.length} request{contextSnapshots.length !== 1 ? 's' : ''}
                </div>
                <div className="context-snapshot-list">
                  {contextSnapshots.map((snap, i) => {
                    const reqPct = pct(snap.request_token_count, snap.context_limit_tokens);
                    const curPct = pct(snap.current_token_count, snap.context_limit_tokens);
                    // Detect truncation: request start changed from the previous snapshot's current start
                    const prevCurStart = i > 0 ? contextSnapshots[i - 1].current_start_message_id : null;
                    const requestTruncated = snap.request_start_message_id !== null &&
                      (i === 0 ? false : prevCurStart !== snap.request_start_message_id);
                    const currentTruncated = snap.current_start_message_id !== snap.request_start_message_id;

                    return (
                      <div key={snap.id} className="ctx-snapshot-item">
                        <div className="ctx-snapshot-header">
                          <span className="ctx-snapshot-req">Request {i + 1}</span>
                          {requestTruncated && (
                            <span className="ctx-snapshot-badge ctx-badge-request">Req truncated</span>
                          )}
                          {currentTruncated && (
                            <span className="ctx-snapshot-badge ctx-badge-current">Cur truncated</span>
                          )}
                        </div>
                        {/* Request row */}
                        <div className="ctx-snapshot-phase-label">Request</div>
                        <div className="ctx-snapshot-bar-track">
                          <div
                            className="ctx-snapshot-bar-fill"
                            style={{ width: `${reqPct}%`, background: getUsageColor(reqPct) }}
                          />
                        </div>
                        <div className="ctx-snapshot-stats">
                          <span style={{ color: getUsageColor(reqPct) }}>{reqPct}%</span>
                          <span>{snap.request_token_count.toLocaleString()} / {snap.context_limit_tokens.toLocaleString()}</span>
                        </div>
                        {/* Current row */}
                        <div className="ctx-snapshot-phase-label">Current</div>
                        <div className="ctx-snapshot-bar-track">
                          <div
                            className="ctx-snapshot-bar-fill"
                            style={{ width: `${curPct}%`, background: getUsageColor(curPct) }}
                          />
                        </div>
                        <div className="ctx-snapshot-stats">
                          <span style={{ color: getUsageColor(curPct) }}>{curPct}%</span>
                          <span>{snap.current_token_count.toLocaleString()} / {snap.context_limit_tokens.toLocaleString()}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
