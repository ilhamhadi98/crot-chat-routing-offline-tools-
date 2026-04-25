'use client';

import React from 'react';

function StatCard({ label, value, progressBarId, className = '' }) {
  return (
    <div className={`stat-card ${className}`}>
      <div className="stat-label">
        <span>{label}</span>
        <span>{value}%</span>
      </div>
      {progressBarId && (
        <div className="progress-bar">
          <div id={progressBarId} className="progress-fill" style={{ width: `${value}%` }}></div>
        </div>
      )}
    </div>
  );
}

export default function StatsPanel({ isOpen, onClose, stats }) {
  if (!isOpen) {
    return null;
  }

  const formatCost = (cost) => {
    if (cost === null || cost === undefined) return '$0.00';
    return `$${cost.toFixed(6)}`;
  }

  return (
    <div className="stats-panel" style={{ right: isOpen ? '0' : '-280px' }}>
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px'}}>
        <h3 style={{margin:0}}>📊 Status</h3>
        <button className="btn-icon-top" style={{background:'transparent', border:'none'}} onClick={onClose}>✕</button>
      </div>
      
      <StatCard className="cpu-card" label="CPU" value={stats.cpu || 0} progressBarId="cpuBar" />
      <StatCard className="ram-card" label="RAM" value={stats.ram || 0} progressBarId="ramBar" />
      <StatCard className="gpu-card" label="GPU" value={stats.gpu || 0} progressBarId="gpuBar" />
      
      <label style={{fontSize:'11px', fontWeight:'bold', color:'var(--text-sub)', marginTop:'10px', display:'block'}}>PROVIDER USAGE</label>
      <div id="providerUsageList">
        {stats.provider_stats && stats.provider_stats.map(p => (
            <div key={p.name} className="stat-card provider-usage-card" style={{padding: '10px 15px', marginTop: '5px'}}>
                <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '12px'}}>
                    <span>{p.name}</span>
                    <span style={{color: '#4caf50', fontWeight: 'bold'}}>{formatCost(p.total_usage_cost)}</span>
                </div>
            </div>
        ))}
      </div>
      
      <h3 style={{marginTop: '20px'}}>📈 Global</h3>
      <div className="stat-card global-usage-card">
        <div className="stat-label">
            <span>Tokens</span>
            <b style={{color:'var(--accent)'}}>{stats.global_tokens || 0}</b>
        </div>
        <div className="stat-label" style={{marginTop: '10px'}}>
            <span>Total Cost</span>
            <b style={{color:'#4caf50'}}>{formatCost(stats.global_cost)}</b>
        </div>
      </div>
    </div>
  );
}
