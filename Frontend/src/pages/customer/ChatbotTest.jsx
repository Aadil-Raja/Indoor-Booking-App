import React, { useState, useEffect, useRef } from 'react';
import './chatbotTest.css';

const ChatbotTest = () => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [chatId, setChatId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [userId, setUserId] = useState('');
  const [ownerId, setOwnerId] = useState('');
  const [isConfigured, setIsConfigured] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleConfigure = () => {
    if (userId && ownerId) {
      setIsConfigured(true);
      addSystemMessage(`Chat configured: User ID: ${userId.slice(0, 8)}..., Owner ID: ${ownerId.slice(0, 8)}...`);
    }
  };

  const addSystemMessage = (content) => {
    setMessages(prev => [...prev, {
      id: Date.now(),
      sender_type: 'system',
      content,
      created_at: new Date().toISOString()
    }]);
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || loading) return;

    const userMessage = {
      id: Date.now(),
      sender_type: 'user',
      content: inputMessage,
      created_at: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8002/api/chat/message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          owner_profile_id: ownerId,
          content: inputMessage
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // Store chat_id for future reference
      if (data.chat_id && !chatId) {
        setChatId(data.chat_id);
      }

      // Add bot response
      const botMessage = {
        id: data.message_id,
        sender_type: 'bot',
        content: data.content,
        message_type: data.message_type,
        metadata: data.message_metadata,
        created_at: new Date().toISOString()
      };

      setMessages(prev => [...prev, botMessage]);

    } catch (error) {
      console.error('Error sending message:', error);
      addSystemMessage(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleButtonClick = (buttonId, buttonText) => {
    setInputMessage(buttonText);
    // Auto-send after a short delay
    setTimeout(() => {
      sendMessage();
    }, 100);
  };

  const handleListItemClick = (itemId, itemTitle) => {
    setInputMessage(itemTitle);
    // Auto-send after a short delay
    setTimeout(() => {
      sendMessage();
    }, 100);
  };

  // Helper function to render text with markdown and clickable links
  const renderFormattedText = (text) => {
    if (!text) return null;

    // Split by newlines to preserve line breaks
    const lines = text.split('\n');
    
    return lines.map((line, lineIndex) => {
      // Process each line for markdown and URLs
      const parts = [];
      let currentIndex = 0;
      
      // Regex to match **bold**, URLs, and emojis
      const regex = /(\*\*[^*]+\*\*|https?:\/\/[^\s]+)/g;
      let match;
      
      while ((match = regex.exec(line)) !== null) {
        // Add text before match
        if (match.index > currentIndex) {
          parts.push(
            <span key={`text-${lineIndex}-${currentIndex}`}>
              {line.substring(currentIndex, match.index)}
            </span>
          );
        }
        
        const matchedText = match[0];
        
        // Check if it's bold text
        if (matchedText.startsWith('**') && matchedText.endsWith('**')) {
          const boldText = matchedText.slice(2, -2);
          parts.push(
            <strong key={`bold-${lineIndex}-${match.index}`}>
              {boldText}
            </strong>
          );
        }
        // Check if it's a URL
        else if (matchedText.startsWith('http')) {
          parts.push(
            <a
              key={`link-${lineIndex}-${match.index}`}
              href={matchedText}
              target="_blank"
              rel="noopener noreferrer"
              className="message-link"
            >
              {matchedText}
            </a>
          );
        }
        
        currentIndex = match.index + matchedText.length;
      }
      
      // Add remaining text
      if (currentIndex < line.length) {
        parts.push(
          <span key={`text-${lineIndex}-${currentIndex}`}>
            {line.substring(currentIndex)}
          </span>
        );
      }
      
      // Return line with <br> if not last line
      return (
        <React.Fragment key={`line-${lineIndex}`}>
          {parts.length > 0 ? parts : line}
          {lineIndex < lines.length - 1 && <br />}
        </React.Fragment>
      );
    });
  };

  const startNewChat = () => {
    setMessages([]);
    setChatId(null);
    addSystemMessage('New chat started');
  };

  const renderMessage = (message) => {
    if (message.sender_type === 'system') {
      return (
        <div key={message.id} className="message-system">
          <div className="message-content">{message.content}</div>
        </div>
      );
    }

    if (message.sender_type === 'user') {
      return (
        <div key={message.id} className="message-user">
          <div className="message-content">{message.content}</div>
          <div className="message-time">
            {new Date(message.created_at).toLocaleTimeString()}
          </div>
        </div>
      );
    }

    // Bot message
    return (
      <div key={message.id} className="message-bot">
        <div className="message-content">
          {renderFormattedText(message.content)}
          
          {/* Render buttons if present */}
          {message.message_type === 'button' && message.metadata?.buttons && (
            <div className="message-buttons">
              {message.metadata.buttons.map(button => (
                <button
                  key={button.id}
                  className="message-button"
                  onClick={() => handleButtonClick(button.id, button.text)}
                >
                  {button.text}
                </button>
              ))}
            </div>
          )}

          {/* Render list if present */}
          {message.message_type === 'list' && message.metadata?.list_items && (
            <div className="message-list">
              {message.metadata.list_items.map(item => (
                <div
                  key={item.id}
                  className="message-list-item"
                  onClick={() => handleListItemClick(item.id, item.title)}
                >
                  <div className="list-item-title">{item.title}</div>
                  {item.description && (
                    <div className="list-item-description">{item.description}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="message-time">
          {new Date(message.created_at).toLocaleTimeString()}
        </div>
      </div>
    );
  };

  if (!isConfigured) {
    return (
      <div className="chatbot-test-container">
        <div className="chatbot-config">
          <h2>Chatbot Test Configuration</h2>
          <p className="config-help">
            Enter the User ID (customer) and Owner Profile ID to start chatting.
            You can find these IDs in your database or use the signup flow.
          </p>
          
          <div className="config-form">
            <div className="form-group">
              <label>User ID (Customer):</label>
              <input
                type="text"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder="Enter customer user UUID"
                className="config-input"
              />
              <small>This is the customer who wants to book</small>
            </div>

            <div className="form-group">
              <label>Owner Profile ID:</label>
              <input
                type="text"
                value={ownerId}
                onChange={(e) => setOwnerId(e.target.value)}
                placeholder="Enter owner profile ID"
                className="config-input"
              />
              <small>This is the owner_profile_id (NOT user_id)</small>
            </div>

            <button
              onClick={handleConfigure}
              disabled={!userId || !ownerId}
              className="config-button"
            >
              Start Chat
            </button>
          </div>

          <div className="config-examples">
            <h3>Quick Test Examples:</h3>
            <ul>
              <li>Create two users via signup (one owner, one customer)</li>
              <li>Owner creates a property and courts via owner portal</li>
              <li>Use customer's user_id and owner's owner_profile_id here</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="chatbot-test-container">
      <div className="chatbot-header">
        <h2>Chatbot Test Interface</h2>
        <div className="chatbot-info">
          <span>Chat ID: {chatId ? chatId.slice(0, 8) + '...' : 'Not started'}</span>
          <button onClick={startNewChat} className="new-chat-button">
            New Chat
          </button>
          <button onClick={() => setIsConfigured(false)} className="config-button-small">
            Change IDs
          </button>
        </div>
      </div>

      <div className="chatbot-messages">
        {messages.map(renderMessage)}
        {loading && (
          <div className="message-bot">
            <div className="message-content typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chatbot-input">
        <textarea
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message..."
          disabled={loading}
          rows="2"
        />
        <button
          onClick={sendMessage}
          disabled={!inputMessage.trim() || loading}
          className="send-button"
        >
          Send
        </button>
      </div>

      <div className="chatbot-suggestions">
        <p>Try these:</p>
        <button onClick={() => setInputMessage('Hello')}>Hello</button>
        <button onClick={() => setInputMessage('I want to book a tennis court')}>Book Tennis</button>
        <button onClick={() => setInputMessage('Show me available facilities')}>Search</button>
        <button onClick={() => setInputMessage('What sports do you have?')}>FAQ</button>
      </div>
    </div>
  );
};

export default ChatbotTest;
