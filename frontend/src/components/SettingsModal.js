'use client';

import React, { useState } from 'react';

function ProviderRow({ provider, onDelete, onCheck }) {
  const getStatusClass = (status) => {
    if (status === 'online') return 'online';
    if (status === 'offline') return 'offline';
    return '';
  };

  return (
    <div className="provider-row" style={{ 
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', 
        padding: '12px 15px', borderBottom: '1px solid var(--border)',
        background: 'rgba(255,255,255,0.03)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <span className={`status-dot ${getStatusClass(provider.status)}`} style={{ width: '10px', height: '10px', borderRadius: '50%' }}></span>
        <span style={{ fontWeight: 'bold', fontSize: '14px', color: 'var(--text-main)' }}>{provider.name.toUpperCase()}</span>
      </div>
      <div style={{ display: 'flex', gap: '8px' }}>
        <button 
            onClick={() => onCheck(provider.name)} 
            style={{ 
                background: 'var(--bg-main)', border: '1px solid var(--border)', 
                color: 'var(--accent)', borderRadius: '6px', padding: '5px 12px', 
                fontSize: '12px', cursor: 'pointer', transition: 'all 0.2s'
            }}
        >
            Check
        </button>
        {provider.name !== 'ollama' && (
          <button 
            onClick={() => onDelete(provider.name)} 
            style={{ 
                background: 'rgba(244, 67, 54, 0.1)', border: '1px solid #f44336', 
                color: '#f44336', borderRadius: '6px', padding: '5px 12px', 
                fontSize: '12px', cursor: 'pointer' 
            }}
          >
            Delete
          </button>
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

  if (!isOpen) return null;

  return (
    <div className="modal" style={{ 
        display: 'flex', position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', 
        background: 'rgba(0,0,0,0.85)', zIndex: 2000, backdropFilter: 'blur(10px)',
        alignItems: 'center', justifyContent: 'center'
    }}>
      <div className="modal-content" style={{ 
          background: 'var(--bg-sidebar)', padding: '30px', borderRadius: '24px', 
          width: '550px', maxWidth: '95%', border: '1px solid var(--border)', 
          boxShadow: '0 20px 50px rgba(0,0,0,0.5)', overflow: 'hidden'
      }}>
        <h3 style={{ 
            marginTop: 0, marginBottom: '25px', color: 'var(--accent)', 
            fontFamily: "'Press Start 2P', cursive", fontSize: '14px', textAlign: 'center'
        }}>
            ⚙️ PROVIDER SETTINGS
        </h3>
        
        <div id="providerList" style={{ 
            marginBottom: '30px', maxHeight: '250px', overflowY: 'auto', 
            borderRadius: '12px', border: '1px solid var(--border)', background: 'rgba(0,0,0,0.2)'
        }}>
          {providers.map(p => (
            <ProviderRow 
              key={p.name} 
              provider={p} 
              onDelete={onDeleteProvider}
              onCheck={onCheckConnection}
            />
          ))}
        </div>

        <div className="sidebar-section" style={{ background: 'rgba(255,255,255,0.02)', padding: '20px', borderRadius: '15px', border: '1px dashed var(--border)' }}>
          <label style={{ display: 'block', marginBottom: '15px', color: 'var(--text-sub)', fontSize: '10px', fontWeight: 'bold' }}>ADD NEW PROVIDER</label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <input 
                    value={newProvName}
                    onChange={(e) => setNewProvName(e.target.value)}
                    placeholder="e.g. openai" 
                    style={{ 
                        flex: '1 1 200px', minWidth: 0, padding: '12px 15px', borderRadius: '10px', 
                        background: 'var(--bg-main)', border: '1px solid var(--border)', 
                        color: 'white', outline: 'none' 
                    }} 
                />
                <button 
                    onClick={handleAdd}
                    style={{ 
                        background: 'var(--accent-gradient)', border: 'none', 
                        padding: '12px 25px', borderRadius: '10px', color: 'white', 
                        cursor: 'pointer', fontWeight: 'bold', fontSize: '14px',
                        flex: '0 0 auto'
                    }}
                >
                    ADD
                </button>
            </div>
            <input 
                value={newProvKey}
                onChange={(e) => setNewProvKey(e.target.value)}
                type="password" 
                placeholder="Enter API Key" 
                style={{ 
                    width: '100%', padding: '12px 15px', borderRadius: '10px', 
                    background: 'var(--bg-main)', border: '1px solid var(--border)', 
                    color: 'white', outline: 'none' 
                }} 
            />
          </div>
        </div>
        
        <button 
          onClick={onClose}
          style={{ 
              marginTop: '25px', width: '100%', padding: '14px', borderRadius: '12px', 
              border: 'none', background: 'var(--border)', color: 'white', 
              cursor: 'pointer', fontWeight: 'bold', fontSize: '14px'
          }}
        >
          CLOSE
        </button>
      </div>
    </div>
  );
}
