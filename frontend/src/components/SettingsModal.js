'use client';

import React, { useState } from 'react';

function ProviderRow({ provider, onDelete, onCheck }) {
  const getStatusClass = (status) => {
    if (status === 'online') return 'online';
    if (status === 'offline') return 'offline';
    return '';
  };

  return (
    <div className="provider-row">
      <div>
        <span className={`status-dot ${getStatusClass(provider.status)}`}></span>
        <span style={{ fontWeight: 'bold' }}>{provider.name}</span>
      </div>
      <div>
        <button onClick={() => onCheck(provider.name)} style={{marginRight: '10px', background: 'none', border: '1px solid var(--border)', color: 'var(--text-sub)', borderRadius: '8px', padding: '5px 10px', cursor: 'pointer'}}>Check</button>
        {provider.name !== 'ollama' && (
          <button onClick={() => onDelete(provider.name)} style={{background: '#f44336', color: 'white', border: 'none', borderRadius: '8px', padding: '5px 10px', cursor: 'pointer'}}>Delete</button>
        )}
      </div>
    </div>
  );
}


export default function SettingsModal({
  isOpen,
  onClose,
  providers,
  onAddProvider,
  onDeleteProvider,
  onCheckConnection
}) {
  const [newProvName, setNewProvName] = useState('');
  const [newProvKey, setNewProvKey] = useState('');

  const handleAdd = () => {
    if (!newProvName.trim()) return;
    onAddProvider(newProvName, newProvKey);
    setNewProvName('');
    setNewProvKey('');
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="modal" style={{ display: isOpen ? 'flex' : 'none' }}>
      <div className="modal-content">
        <h3 style={{marginTop:0, background:'var(--accent-gradient)', WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent'}}>⚙️ PROVIDER MANAGEMENT</h3>
        
        <div id="providerList" style={{marginBottom:'20px', maxHeight:'200px', overflowY:'auto'}}>
          {providers.map(p => (
            <ProviderRow 
              key={p.name} 
              provider={p} 
              onDelete={onDeleteProvider}
              onCheck={onCheckConnection}
            />
          ))}
        </div>

        <div className="sidebar-section">
          <label>Add New Provider</label>
          <div style={{display:'flex', gap:'10px'}}>
            <input 
              value={newProvName}
              onChange={(e) => setNewProvName(e.target.value)}
              placeholder="e.g. gemini" 
              style={{flex:1}} 
            />
            <input 
              value={newProvKey}
              onChange={(e) => setNewProvKey(e.target.value)}
              type="password" 
              placeholder="API Key" 
              style={{flex:2}} 
            />
            <button 
              onClick={handleAdd}
              style={{background:'var(--accent-gradient)', border:'none', padding:'10px 15px', borderRadius:'12px', color:'white', cursor:'pointer', fontWeight:'bold'}}
            >
              ADD
            </button>
          </div>
        </div>
        
        <button 
          onClick={onClose}
          style={{marginTop:'20px', width:'100%', padding:'12px', borderRadius:'12px', border:'none', background:'var(--border)', color:'white', cursor:'pointer', fontWeight:'bold'}}
        >
          CLOSE
        </button>
      </div>
    </div>
  );
}
