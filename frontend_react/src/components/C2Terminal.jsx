import React, { useState, useEffect, useRef } from 'react';
import { apiClient } from '../api';
import SwarmVisualizer from './SwarmVisualizer';

const C2Terminal = () => {
  const [telemetry, setTelemetry] = useState([]);
  const [interceptActive, setInterceptActive] = useState(false);
  const logEndRef = useRef(null);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await apiClient.get('/telemetry');
        if (res.data) {
          setTelemetry(res.data);
        }
        
        const interceptRes = await apiClient.get('/console/intercepts');
        if (Object.keys(interceptRes.data).length > 0) {
          setInterceptActive(true);
        } else {
          setInterceptActive(false);
        }
      } catch (err) {
        console.error("Telemetry error", err);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleResolve = async (action) => {
    try {
      await apiClient.post('/console/resolve', { action });
    } catch (err) {
      console.error('Intercept resolve error', err);
    }
    setInterceptActive(false);
  };

  const getAgentColor = (agent) => {
      case 'SYSTEM_AUDIT': return 'text-red-400';
      case 'ProjectManager': return 'text-purple-400';
      case 'Developer': return 'text-cyan-400';
      case 'CodeReviewer': return 'text-emerald-400';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full relative space-y-4">
      {/* Visualizer at the top */}
      <div className="h-1/2 min-h-[300px]">
        <SwarmVisualizer />
      </div>
      
      {/* Terminal logs at the bottom */}
      <div className="h-1/2 flex flex-col relative">
        <div className="glass-panel p-4 mb-2 flex justify-between items-center">
          <h2 className="text-xl font-bold tracking-wider text-gray-200">C2 TERMINAL LOG</h2>
          <div className="flex space-x-4 text-xs">
            <span className="flex items-center"><div className="w-2 h-2 bg-purple-500 rounded-full mr-2"></div> Manager</span>
            <span className="flex items-center"><div className="w-2 h-2 bg-cyan-500 rounded-full mr-2"></div> Developer</span>
            <span className="flex items-center"><div className="w-2 h-2 bg-emerald-500 rounded-full mr-2"></div> Reviewer</span>
            <span className="flex items-center"><div className="w-2 h-2 bg-red-500 rounded-full mr-2"></div> SYSTEM_AUDIT</span>
          </div>
        </div>
        
        <div className="glass-panel flex-1 p-6 overflow-y-auto space-y-2 relative">
          {telemetry.map(log => (
            <div key={log.id} className="font-mono text-sm break-words border-l-2 border-gray-800 pl-3 py-1 hover:border-gray-600 transition-colors">
              <span className="text-gray-500 mr-4">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
              <span className={`${getAgentColor(log.agent)} font-bold mr-2`}>{log.agent}:</span>
              <span className="text-gray-300">{log.message}</span>
            </div>
          ))}
          <div ref={logEndRef} />
        </div>
      </div>

      {interceptActive && (
        <div className="absolute inset-0 bg-black/80 flex items-center justify-center z-50 backdrop-blur-sm">
          <div className="glass-panel p-8 border border-red-500/50 glow-red max-w-md w-full text-center">
            <h3 className="text-2xl text-red-500 font-bold mb-4 animate-pulse">!! ANOMALY DETECTED !!</h3>
            <p className="text-gray-300 mb-8">Safeguard agent has halted execution due to anomalous pattern recognition. Manual override required.</p>
            <div className="flex justify-center space-x-6">
              <button 
                onClick={() => handleResolve('approve')}
                className="px-6 py-2 bg-emerald-900/30 border border-emerald-500 text-emerald-400 hover:bg-emerald-900/50 transition-colors"
              >
                APPROVE ACTION
              </button>
              <button 
                onClick={() => handleResolve('deny')}
                className="px-6 py-2 bg-red-900/30 border border-red-500 text-red-400 hover:bg-red-900/50 transition-colors"
              >
                DENY ACTION
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default C2Terminal;
