import React, { useState, useEffect, useRef } from 'react';
import { apiClient } from '../api';

const C2Terminal = ({ simId }) => {
  const [telemetry, setTelemetry] = useState([]);
  const [messages, setMessages] = useState([]);
  const logEndRef = useRef(null);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        // Fetch global telemetry
        const telRes = await apiClient.get('/telemetry');
        if (telRes.data) {
          setTelemetry(telRes.data);
        }

        // Fetch simulation specific messages if active
        if (simId) {
          const msgRes = await apiClient.get(`/simulations/${simId}/messages`);
          if (msgRes.data) {
            setMessages(Array.isArray(msgRes.data) ? msgRes.data : (msgRes.data.messages || []));
          }
        } else {
          setMessages([]);
        }
      } catch (err) {
        console.error("Terminal fetch error", err);
      }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 2000);
    return () => clearInterval(interval);
  }, [simId]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [telemetry, messages]);

  const getAgentColor = (agent) => {
    switch(agent) {
      case 'SYSTEM_AUDIT': return 'text-red-400';
      case 'ProjectManager': return 'text-purple-400';
      case 'Developer': return 'text-cyan-400';
      case 'CodeReviewer': return 'text-emerald-400';
      default: return 'text-gray-400';
    }
  };

  const renderContent = (contentString) => {
    try {
      const parts = JSON.parse(contentString);
      if (Array.isArray(parts)) {
        return (
          <div className="flex flex-col gap-2">
            {parts.map((p, i) => {
              if (p.text) return <span key={i} className="whitespace-pre-wrap">{p.text}</span>;
              if (p.inlineData) {
                if (p.inlineData.mimeType.startsWith('image/')) {
                  return <img key={i} src={`data:${p.inlineData.mimeType};base64,${p.inlineData.data}`} className="max-w-xs rounded border border-gray-700" alt="Artifact" />;
                }
                if (p.inlineData.mimeType.startsWith('audio/')) {
                  return <audio key={i} controls src={`data:${p.inlineData.mimeType};base64,${p.inlineData.data}`} className="w-full max-w-xs" />;
                }
              }
              return null;
            })}
          </div>
        );
      }
    } catch (e) {
      // not JSON
    }
    return <span className="whitespace-pre-wrap">{contentString}</span>;
  };

  // Combine and sort logs by timestamp
  const combinedLogs = [...telemetry, ...messages].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

  return (
    <div className="h-full flex flex-col relative">
      <div className="glass-panel p-4 mb-2 flex justify-between items-center border-b border-gray-800 bg-gray-900/60">
        <h2 className="text-xl font-bold tracking-wider text-cyan-400 uppercase">C2 Terminal Global Log</h2>
        <div className="flex space-x-4 text-xs">
          <span className="flex items-center"><div className="w-2 h-2 bg-purple-500 rounded-full mr-2 shadow-[0_0_8px_#a855f7]"></div> Manager</span>
          <span className="flex items-center"><div className="w-2 h-2 bg-cyan-500 rounded-full mr-2 shadow-[0_0_8px_#06b6d4]"></div> Developer</span>
          <span className="flex items-center"><div className="w-2 h-2 bg-emerald-500 rounded-full mr-2 shadow-[0_0_8px_#10b981]"></div> Reviewer</span>
          <span className="flex items-center"><div className="w-2 h-2 bg-red-500 rounded-full mr-2 shadow-[0_0_8px_#ef4444]"></div> SYSTEM</span>
        </div>
      </div>
      
      <div className="glass-panel flex-1 p-6 overflow-y-auto space-y-4 relative bg-black/60 border border-gray-800 rounded-lg">
        {combinedLogs.length === 0 ? (
          <div className="text-gray-600 text-sm italic m-auto h-full flex items-center justify-center">
            Monitoring matrix for signal...
          </div>
        ) : (
          combinedLogs.map((log, idx) => {
            const isTelemetry = !log.sender; 
            const agentName = log.agent || log.sender || 'SYSTEM';
            
            return (
              <div key={log.id || idx} className="flex flex-col border-l-2 border-gray-800 pl-3 py-1 hover:border-gray-600 transition-colors">
                <div className="text-xs text-gray-500 mb-1 flex justify-between">
                  <span>[{new Date(log.timestamp).toLocaleTimeString()}]</span>
                  {isTelemetry && <span className="text-gray-700 italic">SYSTEM_TELEMETRY</span>}
                </div>
                <div className="flex flex-col font-mono text-sm break-words bg-gray-900/40 p-2 rounded">
                  <span className={`${getAgentColor(agentName)} font-bold mb-1`}>{agentName}:</span>
                  <div className="text-gray-300">
                    {renderContent(log.message || log.content || log.text)}
                  </div>
                </div>
              </div>
            );
          })
        )}
        <div ref={logEndRef} />
      </div>
    </div>
  );
};

export default C2Terminal;
