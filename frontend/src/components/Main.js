'use client';

import React, { useState, useRef, useEffect } from 'react';

// A sub-component for the loading animation
function LoadingCube() {
  const phrases = ["MINING DATA...", "SMELTING TOKENS...", "CRAFTING RESPONSE...", "THINKING..."];
  const [phrase, setPhrase] = useState(phrases[0]);

  useEffect(() => {
    let i = 0;
    const interval = setInterval(() => {
      i = (i + 1) % phrases.length;
      setPhrase(phrases[i]);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="loading" style={{ display: 'flex' }}>
      <div className="cube-wrapper"><div className="cube"><div className="face top"></div><div className="face bottom"></div><div className="face front"></div><div className="face back"></div><div className="face left"></div><div className="face right"></div></div></div>
      <div id="thinkingText" style={{fontSize: '9px', fontWeight: 'bold', color: 'var(--accent)', letterSpacing: '1px'}}>{phrase}</div>
    </div>
  );
}

// A sub-component for a single message
function Message({ msg }) {
  const isBot = msg.role === 'assistant';

  const ImageGrid = ({ images }) => (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginTop: '10px' }}>
      {images.map((img, i) => (
        <img key={i} src={img} alt={`uploaded content ${i + 1}`} style={{ maxWidth: '150px', maxHeight: '150px', borderRadius: '12px' }} />
      ))}
    </div>
  );

  return (
    <div className={`msg ${isBot ? 'bot' : 'user'}`}>
      {msg.images && msg.images.length > 0 && <ImageGrid images={msg.images} />}
      {msg.content && <span>{msg.content}</span>}
      
      {isBot && msg.meta && (
        <div className="msg-meta">
          <span>
            🤖 <b>{msg.meta.provider}/{msg.meta.model}</b>
          </span>
          <span>
            ⏱ <b>{msg.meta.process_time}s</b>
          </span>
          <span>
            🪙 <b>{msg.meta.tokens}</b>
          </span>
          <span>
            💰 <b>${(msg.meta.cost || 0).toFixed(6)}</b>
          </span>
        </div>
      )}
    </div>
  );
}

export default function Main({ 
  chatHistory, 
  currentSessionName, 
  isLoading,
  onSendMessage,
  onToggleSidebar,
  onNewSession,
  onToggleStats
}) {
  const [message, setMessage] = useState('');
  const [selectedImages, setSelectedImages] = useState([]);
  const chatBoxRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [chatHistory, isLoading]);

  const handleTextareaInput = (e) => {
    setMessage(e.target.value);
    e.target.style.height = "44px";
    e.target.style.height = (e.target.scrollHeight) + "px";
  };

  const handleSend = () => {
    if (!message.trim() && selectedImages.length === 0) return;
    onSendMessage(message, selectedImages);
    setMessage('');
    setSelectedImages([]);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleImageChange = (e) => {
    const files = Array.from(e.target.files);
    const newImages = [];
    files.forEach(file => {
      const reader = new FileReader();
      reader.onload = (loadEvent) => {
        newImages.push(loadEvent.target.result);
        if (newImages.length === files.length) {
          setSelectedImages(prev => [...prev, ...newImages]);
        }
      };
      reader.readAsDataURL(file);
    });
    e.target.value = '';
  };

  const removeImage = (index) => {
    setSelectedImages(prev => prev.filter((_, i) => i !== index));
  };
  
  return (
    <div className="main">
      <div className="top-bar">
        <button className="btn-icon-top" onClick={onToggleSidebar}>☰</button>
        <button className="btn-icon-top" onClick={onNewSession}>+</button>
        <div style={{flex:1, textAlign:'center', fontWeight:'bold', fontSize:'14px', opacity:0.8}}>{currentSessionName}</div>
        <button className="btn-icon-top" onClick={() => document.body.setAttribute("data-theme", document.body.getAttribute("data-theme")==="dark"?"light":"dark")}>☀️</button>
        <button className="btn-icon-top" onClick={onToggleStats}>📊</button>
      </div>

      <div className="chat-container" ref={chatBoxRef}>
        {chatHistory.map((msg, index) => (
          <Message key={index} msg={msg} />
        ))}
        {isLoading && <LoadingCube />}
      </div>

      <div className="input-wrapper">
        <div className="unified-box">
          <div id="imagePreview" style={{display: selectedImages.length > 0 ? 'flex' : 'none', padding: '10px', gap: '10px', flexWrap: 'wrap'}}>
            {selectedImages.map((img, index) => (
              <div key={index} className="preview-item" style={{position: 'relative'}}>
                <img src={img} alt="preview" style={{width: '50px', height: '50px', borderRadius: '8px', objectFit: 'cover'}} />
                <div className="preview-remove" onClick={() => removeImage(index)} style={{position: 'absolute', top: '-5px', right: '-5px', background: 'black', color: 'white', borderRadius: '50%', width: '16px', height: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', cursor: 'pointer'}}>✕</div>
              </div>
            ))}
          </div>
          <div className="input-row">
            <input type="file" ref={fileInputRef} hidden accept="image/*" multiple onChange={handleImageChange} />
            <button style={{background: 'transparent', border: 'none', color: 'var(--text-sub)', fontSize: '20px', cursor: 'pointer'}} onClick={() => fileInputRef.current.click()}>📎</button>
            <textarea 
              id="message" 
              placeholder="Ask me anything..."
              value={message}
              onChange={handleTextareaInput}
              onKeyDown={handleKeyDown}
            ></textarea>
            <button className="btn-send" onClick={handleSend}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ imageRendering: 'pixelated' }}>
                <path d="M10 20H14V22H10V20Z" fill="#6A462F"/>
                <path d="M11 19H13V20H11V19Z" fill="#A07B58"/>
                <path d="M8 18H16V19H8V18Z" fill="#3E3E3E"/>
                <path d="M9 17H15V18H9V17Z" fill="#6A462F"/>
                <path fill-rule="evenodd" clip-rule="evenodd" d="M11 4H13V17H11V4Z" fill="#8BE5FF"/>
                <path d="M12 4H13V17H12V4Z" fill="#42A2C1"/>
                <path d="M11 3H13V4H11V3Z" fill="#3E3E3E"/>
                <path d="M10 4H11V5H10V4Z" fill="#3E3E3E"/>
                <path d="M13 4H14V5H13V4Z" fill="#3E3E3E"/>
                <path d="M11 17H13V18H11V17Z" fill="#3E3E3E"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
