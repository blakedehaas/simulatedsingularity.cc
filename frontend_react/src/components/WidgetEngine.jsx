import React, { useState } from 'react';
import { apiClient } from '../api';

const WidgetEngine = ({ element, localState, setLocalState }) => {
  const [loading, setLoading] = useState(false);
  const [actionResult, setActionResult] = useState(null);

  const handleAction = async (action) => {
    if (!action) return;
    setLoading(true);
    setActionResult(null);
    try {
      let payload = {};
      // Gather payload from local state based on action.payloadFrom array
      if (action.payloadFrom && Array.isArray(action.payloadFrom)) {
        action.payloadFrom.forEach(id => {
          payload[id] = localState[id];
        });
      }

      let res;
      if (action.method.toUpperCase() === 'POST') {
        res = await apiClient.post(action.url, payload);
      } else if (action.method.toUpperCase() === 'GET') {
        res = await apiClient.get(action.url, { params: payload });
      }

      setActionResult({ success: true, data: res.data });
    } catch (err) {
      console.error("Action error:", err);
      setActionResult({ success: false, error: err.message });
    } finally {
      setLoading(false);
    }
  };

  const updateState = (id, value) => {
    if (id) {
      setLocalState(prev => ({ ...prev, [id]: value }));
    }
  };

  switch (element.type) {
    case 'text':
      const textClass = element.style === 'header' ? 'text-lg font-bold text-cyan-400' 
                      : element.style === 'warning' ? 'text-amber-500 font-bold'
                      : 'text-sm text-gray-300';
      return <div className={`mb-2 ${textClass}`}>{element.value}</div>;
      
    case 'gumball':
      const color = element.color === 'green' ? 'bg-emerald-500 shadow-[0_0_8px_#10b981]' 
                  : element.color === 'red' ? 'bg-red-500 shadow-[0_0_8px_#ef4444]'
                  : element.color === 'cyan' ? 'bg-cyan-500 shadow-[0_0_8px_#06b6d4]'
                  : 'bg-gray-500';
      return (
        <div className="flex items-center gap-2 mb-2">
          <div className={`w-3 h-3 rounded-full ${color}`}></div>
          <span className="text-xs uppercase text-gray-400">{element.label}</span>
        </div>
      );

    case 'switch':
      const isChecked = localState[element.id] || false;
      return (
        <label className="flex items-center gap-2 mb-2 cursor-pointer group">
          <span className="text-xs uppercase text-gray-400 group-hover:text-cyan-400 transition-colors">{element.label}</span>
          <div className="relative">
            <input 
              type="checkbox" 
              checked={isChecked} 
              onChange={(e) => updateState(element.id, e.target.checked)} 
              className="sr-only" 
            />
            <div className={`block w-8 h-4 rounded-full transition-colors ${isChecked ? 'bg-cyan-600' : 'bg-gray-800 border border-gray-700'}`}></div>
            <div className={`dot absolute left-0.5 top-0.5 bg-cyan-400 w-3 h-3 rounded-full transition-transform ${isChecked ? 'transform translate-x-4 bg-white' : ''}`}></div>
          </div>
        </label>
      );

    case 'textbox':
      return (
        <div className="flex flex-col gap-1 mb-2">
          {element.label && <label className="text-xs uppercase text-gray-500">{element.label}</label>}
          {element.multiline ? (
            <textarea 
              value={localState[element.id] || ''}
              onChange={(e) => updateState(element.id, e.target.value)}
              placeholder={element.placeholder}
              className="bg-black/50 border border-gray-700 rounded p-2 text-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 transition-colors h-20 resize-none w-full"
            />
          ) : (
            <input 
              type="text"
              value={localState[element.id] || ''}
              onChange={(e) => updateState(element.id, e.target.value)}
              placeholder={element.placeholder}
              className="bg-black/50 border border-gray-700 rounded p-2 text-sm focus:border-cyan-500 focus:outline-none w-full"
            />
          )}
        </div>
      );

    case 'button':
      return (
        <div className="flex flex-col gap-1 mb-2">
          <button 
            onClick={() => handleAction(element.action)}
            disabled={loading}
            className={`py-2 px-4 text-xs font-bold uppercase tracking-wider border transition-colors w-full text-center
              ${loading ? 'bg-gray-800 border-gray-700 text-gray-500 cursor-not-allowed' 
                : 'bg-cyan-900/30 border-cyan-500 text-cyan-400 hover:bg-cyan-900/50 hover:text-glow-cyan'}`}
          >
            {loading ? 'Processing...' : element.label}
          </button>
          {actionResult && actionResult.success && <span className="text-[10px] text-emerald-500 text-center">Action successful</span>}
          {actionResult && !actionResult.success && <span className="text-[10px] text-red-500 text-center">Error: {actionResult.error}</span>}
        </div>
      );

    case 'image':
      return (
        <div className="mb-2">
          <img src={element.src} alt={element.label || 'Image'} className="w-full rounded border border-gray-700" />
        </div>
      );

    case 'video':
      return (
        <div className="mb-2">
          <video src={element.src} controls className="w-full rounded border border-gray-700" />
        </div>
      );

    case 'audio':
      return (
        <div className="mb-2 w-full">
          {element.label && <span className="text-xs text-gray-400 block mb-1">{element.label}</span>}
          <audio src={element.src} controls className="w-full h-8 outline-none" />
        </div>
      );

    case 'table':
      return (
        <div className="mb-2 overflow-x-auto border border-gray-800 rounded">
          <table className="w-full text-xs text-left text-gray-300">
            <thead className="bg-gray-900 text-gray-400 uppercase">
              <tr>
                {element.columns.map((col, i) => (
                  <th key={i} className="px-3 py-2 border-b border-gray-800">{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {element.rows.map((row, i) => (
                <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                  {row.map((cell, j) => (
                    <td key={j} className="px-3 py-2">{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );

    case 'bar_graph':
      return (
        <div className="mb-2 flex flex-col gap-2 p-2 border border-gray-800 rounded bg-black/30">
          {element.label && <div className="text-xs uppercase text-gray-400 font-bold mb-1">{element.label}</div>}
          {element.data.map((item, i) => {
            const percent = Math.min(100, Math.max(0, (item.value / element.max) * 100));
            return (
              <div key={i} className="flex items-center gap-2">
                <span className="text-xs text-gray-500 w-16 truncate">{item.label}</span>
                <div className="flex-1 h-3 bg-gray-900 rounded overflow-hidden">
                  <div 
                    className="h-full bg-cyan-500 shadow-[0_0_8px_#06b6d4]" 
                    style={{ width: `${percent}%` }}
                  ></div>
                </div>
                <span className="text-xs text-cyan-400 w-8 text-right">{item.value}</span>
              </div>
            );
          })}
        </div>
      );

    default:
      return <div className="p-2 text-red-500 text-xs border border-red-900 mb-2">Unsupported type: {element.type}</div>;
  }
};

export default WidgetEngine;
