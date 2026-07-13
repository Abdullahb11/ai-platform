import React, { useState } from 'react';
import './App.css';

function App() {
  const [message, setMessage] = useState('');
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;

    setLoading(true);
    setError(null);
    setResponse('');

    try {
      const res = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message }),
      });

      if (!res.ok) {
        throw new Error(`Server responded with code: ${res.status}`);
      }

      const data = await res.json();
      setResponse(data.response);
    } catch (err: any) {
      setError(err.message || 'Failed to connect to the backend server. Make sure the FastAPI app is running on port 8000.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <header>
        <h1 className="title">AI Platform</h1>
        <p className="subtitle">End-to-End Gemini Integration Test</p>
      </header>

      <main>
        <form onSubmit={handleSubmit}>
          <div className="input-wrapper">
            <textarea
              className="prompt-input"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
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

        {(loading || response || error) && (
          <div className="response-container">
            <div className="response-label">
              {loading ? 'Processing' : error ? 'Error' : 'Gemini Response'}
            </div>
            
            {loading && (
              <div className="loading-indicator">
                <div className="spinner"></div>
                <span>Waiting for response...</span>
              </div>
            )}

            {error && (
              <div className="response-content error">
                {error}
              </div>
            )}

            {response && !loading && !error && (
              <div className="response-content">
                {response}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
