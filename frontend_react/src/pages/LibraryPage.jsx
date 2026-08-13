import React, { useState, useEffect } from 'react';
import { apiClient } from '../api';

const LibraryPage = () => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [rebootingId, setRebootingId] = useState(null);

  useEffect(() => {
    const fetchLibrary = async () => {
      try {
        const res = await apiClient.get('/simulations/library');
        if (res.data) {
          setSessions(res.data);
        }
      } catch (err) {
        // Mock data
        setSessions([
          { id: 'sim-7489', name: 'Alpha Fork', status: 'ARCHIVED', timestamp: '2026-08-12T14:30:00Z', epochs: 142, dataProcessed: 154200 },
          { id: 'sim-9912', name: 'Beta Convergence', status: 'FAILED', timestamp: '2026-08-10T09:15:00Z', epochs: 34, dataProcessed: 28000 },
          { id: 'sim-1044', name: 'Gamma Protocol', status: 'ARCHIVED', timestamp: '2026-08-01T22:45:00Z', epochs: 512, dataProcessed: 994000 }
        ]);
      } finally {
        setLoading(false);
      }
    };
    fetchLibrary();
  }, []);

  const handleReboot = async (id) => {
    setRebootingId(id);
    try {
      await apiClient.post(`/simulations/${id}/reboot`);
    } catch (err) {
      console.log(`Rebooted ${id} (mock)`);
      // Update local state to show it's active
      setSessions(prev => prev.map(s => s.id === id ? { ...s, status: 'ACTIVE' } : s));
    } finally {
      setTimeout(() => setRebootingId(null), 1000);
    }
  };

  return (
    <div className="flex-1 flex flex-col p-6 space-y-6 overflow-y-auto">
      <div className="glass-panel p-6 border-b-2 border-b-cyan-500">
        <h1 className="text-2xl font-bold text-cyan-400 tracking-widest">SIMULATION LIBRARY</h1>
        <p className="text-gray-400 font-mono text-sm mt-2">Archive of previous cognitive timelines and swarm topologies.</p>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-cyan-500 animate-pulse font-mono">LOADING ARCHIVES...</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sessions.map(session => (
            <div key={session.id} className="glass-panel p-6 flex flex-col relative border-l-4 border-l-purple-500 hover:border-l-cyan-500 transition-colors">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-lg font-bold text-gray-200">{session.name}</h3>
                  <div className="text-xs text-gray-500 font-mono">{session.id}</div>
                </div>
                <div className={`px-2 py-1 text-xs font-bold ${
                  session.status === 'ARCHIVED' ? 'bg-gray-800 text-gray-400' :
                  session.status === 'FAILED' ? 'bg-red-900/50 text-red-400' :
                  'bg-emerald-900/50 text-emerald-400'
                }`}>
                  {session.status}
                </div>
              </div>

              <div className="space-y-2 mb-6 font-mono text-sm text-gray-400">
                <div className="flex justify-between">
                  <span>EPOCHS</span>
                  <span className="text-purple-400">{session.epochs}</span>
                </div>
                <div className="flex justify-between">
                  <span>DATA</span>
                  <span className="text-cyan-400">{session.dataProcessed.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>TIMESTAMP</span>
                  <span>{new Date(session.timestamp).toLocaleDateString()}</span>
                </div>
              </div>

              <div className="mt-auto">
                <button
                  onClick={() => handleReboot(session.id)}
                  disabled={rebootingId === session.id || session.status === 'ACTIVE'}
                  className={`w-full py-2 font-bold border transition-colors ${
                    session.status === 'ACTIVE' 
                      ? 'bg-emerald-900/20 border-emerald-900 text-emerald-700 cursor-not-allowed'
                      : 'bg-purple-900/30 border-purple-500 text-purple-400 hover:bg-purple-900/50'
                  }`}
                >
                  {rebootingId === session.id ? 'REBOOTING...' : session.status === 'ACTIVE' ? 'RUNNING' : 'REBOOT SEQUENCE'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default LibraryPage;
