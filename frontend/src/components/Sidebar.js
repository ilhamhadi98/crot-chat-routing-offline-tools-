'use client';

export default function Sidebar({
  isOpen,
  onClose,
  providers,
  models,
  sessions,
  currentSessionName,
  onProviderChange,
  onModelChange,
  onSessionClick,
  onOpenSettings,
  onDeleteSession,
  selectedProvider,
  selectedModel
}) {
  return (
    <div className={`sidebar ${isOpen ? 'active' : ''}`} id="sidebar">
      <button className="btn-close-sidebar" onClick={onClose}>✕</button>
      <div className="logo-minecraft-3d">
        <span className="char-c">C</span>
        <span className="char-r">R</span>
        <span className="char-o">O</span>
        <span className="char-t">T</span>
      </div>
      <div className="sidebar-section">
        <label>Provider</label>
        <select id="provider" value={selectedProvider} onChange={e => onProviderChange(e.target.value)}>
          {providers.map(p => (
            <option key={p.name} value={p.name}>{p.name}</option>
          ))}
        </select>
      </div>
      <div className="sidebar-section">
        <label>Model</label>
        <select id="model" value={selectedModel} onChange={e => onModelChange(e.target.value)}>
          {models.map(m => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </div>
      <label style={{marginTop: '10px'}}>Sessions (SQLite)</label>
      <div className="session-list" id="sessionList">
        {sessions.map(s => (
          <div 
            key={s.name} 
            className={`session-item ${s.name === currentSessionName ? 'active' : ''}`}
            title={s.name}
          >
            <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis' }} onClick={() => onSessionClick(s.name)}>
              {s.name}
            </span>
            <button 
              className="btn-delete-session"
              onClick={(e) => {
                e.stopPropagation(); // prevent session click
                onDeleteSession(s.name);
              }}
            >
              ✕
            </button>
          </div>
        ))}
      </div>
      <div style={{flex: 1}}></div>
      <button 
        className="sidebar-section" 
        style={{background: 'var(--border)', border: 'none', padding: '12px', borderRadius: '12px', color: 'white', cursor: 'pointer', fontWeight: 'bold'}}
        onClick={onOpenSettings}
      >
        ⚙️ PROVIDER SETTINGS
      </button>
    </div>
  );
}
