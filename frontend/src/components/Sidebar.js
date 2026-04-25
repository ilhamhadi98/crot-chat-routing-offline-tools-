'use client';

export default function Sidebar({
  providers,
  models,
  sessions,
  currentSessionName,
  onProviderChange,
  onModelChange,
  onSessionClick,
  onOpenSettings,
  selectedProvider,
  selectedModel
}) {
  return (
    <div className="sidebar" id="sidebar">
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
            onClick={() => onSessionClick(s.name)}
            title={s.name}
          >
            {s.name}
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
