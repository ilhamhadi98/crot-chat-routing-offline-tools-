'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Sidebar from '@/components/Sidebar';
import Main from '@/components/Main';
import SettingsModal from '@/components/SettingsModal';
import StatsPanel from '@/components/StatsPanel';

const API_URL = 'http://localhost:5000';

export default function Home() {
  // UI State
  const [isSidebarOpen, setSidebarOpen] = useState(false);
  const [isStatsPanelOpen, setStatsPanelOpen] = useState(false);
  const [isSettingsModalOpen, setSettingsModalOpen] = useState(false);

  // Data State
  const [providers, setProviders] = useState([]);
  const [models, setModels] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [chatHistory, setChatHistory] = useState([]);
  const [stats, setStats] = useState({});
  const [isLoading, setIsLoading] = useState(false);

  // Selection State
  const [selectedProvider, setSelectedProvider] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [currentSessionName, setCurrentSessionName] = useState('New Session');

  // --- DATA FETCHING & STATE MANAGEMENT ---
  
  // Set initial session name on client-side only to prevent hydration error
  useEffect(() => {
    setCurrentSessionName('Session_' + Date.now());
  }, []);

  const fetchProviders = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/providers`);
      const data = await res.json();
      setProviders(data);
      if (data.length > 0 && !selectedProvider) {
        setSelectedProvider(data[0].name);
      }
    } catch (e) { console.error("Failed to fetch providers:", e); }
  }, [selectedProvider]);

  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/sessions`);
      const data = await res.json();
      setSessions(data);
    } catch (e) { console.error("Failed to fetch sessions:", e); }
  }, []);

  const fetchModels = useCallback(async () => {
    if (!selectedProvider) return;
    try {
      const res = await fetch(`${API_URL}/models/${selectedProvider}`);
      const data = await res.json();
      setModels(data);
      if (data.length > 0) {
        setSelectedModel(data[0] || '');
      } else {
        setSelectedModel('');
      }
    } catch (e) {
      console.error("Failed to fetch models:", e);
      setModels([]);
      setSelectedModel('');
    }
  }, [selectedProvider]);
  
  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/system_stats`);
      const data = await res.json();
      setStats(data);
    } catch (e) { console.error("Failed to fetch stats:", e); }
  }, []);

  useEffect(() => {
    fetchProviders();
    fetchSessions();
    fetchStats();
    
    const statsInterval = setInterval(fetchStats, 2000);
    return () => clearInterval(statsInterval);
  }, []);

  useEffect(() => {
    fetchModels();
  }, [selectedProvider]);

  // --- HANDLERS ---
  const handleProviderChange = (providerName) => setSelectedProvider(providerName);
  const handleModelChange = (modelName) => setSelectedModel(modelName);

  const handleNewSession = () => {
    setChatHistory([]);
    setCurrentSessionName('Session_' + Date.now());
  };

  const handleSessionClick = async (sessionName) => {
    try {
      const res = await fetch(`${API_URL}/load_session/${sessionName}`);
      const data = await res.json();
      setChatHistory(data);
      setCurrentSessionName(sessionName);
    } catch (e) { console.error("Failed to load session:", e); }
  };

  const handleSendMessage = async (message, images) => {
    if (isLoading) return;
    setIsLoading(true);
    const userMessage = { role: 'user', content: message, images: images };
    setChatHistory(prev => [...prev, userMessage]);

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ provider: selectedProvider, model: selectedModel, message, images, history: chatHistory, session_name: currentSessionName })
      });
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let fullReply = "";
      setChatHistory(prev => [...prev, { role: 'assistant', content: "" }]);
      while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = JSON.parse(line.substring(6));
          if(data.text) { 
            fullReply += data.text;
            setChatHistory(prev => [...prev.slice(0, -1), { role: 'assistant', content: fullReply }]);
          }
          if(data.error) throw new Error(data.error);
          if(data.done) {
            setChatHistory(prev => [...prev.slice(0, -1), { role: 'assistant', content: fullReply, meta: data }]);
            fetchSessions();
            fetchStats();
            return;
          }
        }
      }
    } catch (e) {
      setChatHistory(prev => [...prev.slice(0, -1), { role: 'assistant', content: `Error: ${e.message}` }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddProvider = async (name, key) => {
    try {
      await fetch(`${API_URL}/providers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, api_key: key })
      });
      fetchProviders();
    } catch (e) { console.error("Failed to add provider:", e); }
  };
  
  const handleDeleteProvider = async (name) => {
    try {
      await fetch(`${API_URL}/providers?name=${name}`, { method: 'DELETE' });
      fetchProviders();
    } catch (e) { console.error("Failed to delete provider:", e); }
  };
  
  const handleCheckConnection = async (name) => {
    try {
      await fetch(`${API_URL}/check_connection/${name}`);
      fetchProviders();
    } catch (e) { console.error("Failed to check connection:", e); }
  };

  return (
    <>
      <div id="overlay" style={{display: (isSidebarOpen || isStatsPanelOpen || isSettingsModalOpen) ? 'block' : 'none', position: 'fixed', width: '100%', height: '100%', background: 'rgba(0,0,0,0.5)', zIndex: 500}} onClick={() => { setSidebarOpen(false); setStatsPanelOpen(false); setSettingsModalOpen(false); }}></div>

      <Sidebar
        providers={providers} models={models} sessions={sessions}
        currentSessionName={currentSessionName} selectedProvider={selectedProvider} selectedModel={selectedModel}
        onProviderChange={handleProviderChange} onModelChange={handleModelChange} onSessionClick={handleSessionClick}
        onOpenSettings={() => setSettingsModalOpen(true)}
      />

      <Main
        chatHistory={chatHistory} currentSessionName={currentSessionName} isLoading={isLoading}
        onSendMessage={handleSendMessage} onToggleSidebar={() => setSidebarOpen(!isSidebarOpen)}
        onNewSession={handleNewSession} onToggleStats={() => setStatsPanelOpen(!isStatsPanelOpen)}
      />
      
      <SettingsModal
        isOpen={isSettingsModalOpen}
        onClose={() => setSettingsModalOpen(false)}
        providers={providers}
        onAddProvider={handleAddProvider}
        onDeleteProvider={handleDeleteProvider}
        onCheckConnection={handleCheckConnection}
      />

      <StatsPanel
        isOpen={isStatsPanelOpen}
        onClose={() => setStatsPanelOpen(false)}
        stats={stats}
      />
    </>
  );
}
