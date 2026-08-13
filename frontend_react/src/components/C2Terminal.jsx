import React, { useState, useEffect, useRef } from 'react';
import { apiClient } from '../api';
import SwarmVisualizer from './SwarmVisualizer';

const C2Terminal = () => {
  const [telemetry, setTelemetry] = useState([]);
  const logEndRef = useRef(null);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await apiClient.get('/telemetry');
        if (res.data) {
          setTelemetry(res.data);
        }
      } catch (err) {
        console.error("Telemetry error", err);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, []);



  const getAgentColor = (agent) => {
    switch(agent) {
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

    </div>
  );
};

export default C2Terminal;
