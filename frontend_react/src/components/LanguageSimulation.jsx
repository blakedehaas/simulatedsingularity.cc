import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const LanguageSimulation = () => {
  const [seedPrompt, setSeedPrompt] = useState('');
  const [endStateCondition, setEndStateCondition] = useState('');
  const [agents, setAgents] = useState([{ name: '', system_prompt: '' }]);
  const [simId, setSimId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [isSpawning, setIsSpawning] = useState(false);
  const [error, setError] = useState('');
  
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    let intervalId;
    if (simId && isRunning) {
      intervalId = setInterval(async () => {
        try {
          const res = await axios.get(`/api/simulations/${simId}/messages`);
          // Ensure messages is an array
          const newMessages = Array.isArray(res.data) ? res.data : (res.data.messages || []);
          setMessages(newMessages);
        } catch (err) {
          console.error('Error fetching messages:', err);
        }
      }, 2000);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [simId, isRunning]);

  const handleAddAgent = () => {
    setAgents([...agents, { name: '', system_prompt: '' }]);
  };

  const handleRemoveAgent = (index) => {
    const newAgents = agents.filter((_, i) => i !== index);
    setAgents(newAgents);
  };

  const handleAgentChange = (index, field, value) => {
    const newAgents = [...agents];
    newAgents[index][field] = value;
    setAgents(newAgents);
  };

  const handleSpawn = async () => {
    setIsSpawning(true);
    setError('');
    try {
      const payload = {
        seed_prompt: seedPrompt,
        end_state_condition: endStateCondition,
        agents: agents.filter(a => a.name.trim() !== '' && a.system_prompt.trim() !== '')
      };
      const res = await axios.post('/api/simulations/language/spawn', payload);
      // Fallback depending on backend structure
      const newSimId = res.data?.sim_id || res.data?.id || res.data;
      if (typeof newSimId === 'string' || typeof newSimId === 'number') {
        setSimId(newSimId);
      } else {
        throw new Error('Unexpected response format from spawn endpoint');
      }
    } catch (err) {
      console.error('Error spawning simulation:', err);
      setError('Failed to spawn simulation. Please check the network tab or console.');
    } finally {
      setIsSpawning(false);
    }
  };

  const handleRun = async () => {
    if (!simId) return;
    try {
      await axios.post(`/api/simulations/${simId}/start`);
      setIsRunning(true);
      setError('');
    } catch (err) {
      console.error('Error starting simulation:', err);
      setError('Failed to start simulation.');
    }
  };

  return (
    <div className="flex flex-col h-full font-mono text-gray-300">
      <h1 className="text-2xl text-cyan-400 mb-6 text-glow-cyan uppercase tracking-wider border-b border-gray-800 pb-2">
        Language Simulation Matrix
      </h1>
      
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 overflow-hidden">
        
        {/* Configuration Panel */}
        <div className="glass-panel p-6 flex flex-col gap-4 overflow-y-auto border border-gray-800 bg-gray-900/40 rounded-lg">
          <h2 className="text-xl text-emerald-400 mb-2 uppercase tracking-wide">Configuration</h2>
          
          <div className="flex flex-col gap-2">
            <label className="text-xs uppercase text-gray-500">Seed Prompt</label>
            <textarea 
              value={seedPrompt}
              onChange={(e) => setSeedPrompt(e.target.value)}
              className="bg-black/50 border border-gray-700 rounded p-2 text-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 transition-colors h-24 resize-none"
              placeholder="Initial context or prompt to kickstart the simulation..."
            />
          </div>

          <div className="flex flex-col gap-2">
            <label className="text-xs uppercase text-gray-500">End State Condition</label>
            <textarea 
              value={endStateCondition}
              onChange={(e) => setEndStateCondition(e.target.value)}
              className="bg-black/50 border border-gray-700 rounded p-2 text-sm focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 transition-colors h-24 resize-none"
              placeholder="Condition under which the simulation halts..."
            />
          </div>

          <div className="flex flex-col gap-2 mt-4">
            <div className="flex items-center justify-between border-b border-gray-800 pb-2">
              <label className="text-xs uppercase text-gray-500">Agents</label>
              <button 
                onClick={handleAddAgent}
                className="text-xs px-2 py-1 bg-gray-800 hover:bg-gray-700 text-cyan-400 border border-gray-700 rounded transition-colors"
              >
                + ADD AGENT
              </button>
            </div>
            
            <div className="flex flex-col gap-4 mt-2">
              {agents.map((agent, index) => (
                <div key={index} className="flex flex-col gap-2 p-3 bg-black/40 border border-gray-800 rounded">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-purple-400">Agent {index + 1}</span>
                    <button 
                      onClick={() => handleRemoveAgent(index)}
                      className="text-xs text-red-500 hover:text-red-400"
                    >
                      [REMOVE]
                    </button>
                  </div>
                  <input
                    type="text"
                    value={agent.name}
                    onChange={(e) => handleAgentChange(index, 'name', e.target.value)}
                    placeholder="Agent Name"
                    className="bg-black/50 border border-gray-700 rounded p-2 text-sm focus:border-cyan-500 focus:outline-none"
                  />
                  <textarea
                    value={agent.system_prompt}
                    onChange={(e) => handleAgentChange(index, 'system_prompt', e.target.value)}
                    placeholder="System Prompt"
                    className="bg-black/50 border border-gray-700 rounded p-2 text-sm focus:border-cyan-500 focus:outline-none h-20 resize-none"
                  />
                </div>
              ))}
            </div>
          </div>

          {error && (
            <div className="p-2 border border-red-500/50 bg-red-900/20 text-red-400 text-sm mt-4">
              {error}
            </div>
          )}

          <div className="flex gap-4 mt-6">
            <button
              onClick={handleSpawn}
              disabled={isSpawning || isRunning}
              className={`flex-1 py-2 font-bold uppercase tracking-wider border transition-colors ${isSpawning || isRunning ? 'bg-gray-800 border-gray-700 text-gray-500 cursor-not-allowed' : 'bg-cyan-900/30 border-cyan-500 text-cyan-400 hover:bg-cyan-900/50 hover:text-glow-cyan'}`}
            >
              {isSpawning ? 'Spawning...' : 'Spawn Simulation'}
            </button>
            <button
              onClick={handleRun}
              disabled={!simId || isRunning}
              className={`flex-1 py-2 font-bold uppercase tracking-wider border transition-colors ${!simId || isRunning ? 'bg-gray-800 border-gray-700 text-gray-500 cursor-not-allowed' : 'bg-purple-900/30 border-purple-500 text-purple-400 hover:bg-purple-900/50 hover:text-glow-purple'}`}
            >
              Run Simulation
            </button>
          </div>
          
          {simId && (
            <div className="text-xs text-emerald-500 mt-2 text-center">
              Active Sim ID: {simId}
            </div>
          )}
        </div>

        {/* Live Output Window */}
        <div className="glass-panel border border-gray-800 bg-black/60 rounded-lg flex flex-col overflow-hidden">
          <div className="p-3 border-b border-gray-800 bg-gray-900/50 flex justify-between items-center">
            <h2 className="text-sm text-cyan-400 uppercase tracking-widest">Live Output</h2>
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isRunning ? 'bg-emerald-500 shadow-[0_0_8px_#10b981] animate-pulse' : 'bg-gray-600'}`}></div>
              <span className="text-xs text-gray-500">{isRunning ? 'POLLING' : 'IDLE'}</span>
            </div>
          </div>
          
          <div className="flex-1 p-4 overflow-y-auto flex flex-col gap-4">
            {messages.length === 0 ? (
              <div className="text-gray-600 text-sm italic m-auto">
                No output data available yet.
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div key={idx} className="flex flex-col">
                  <div className="text-xs text-purple-400 mb-1">[{msg.agent || msg.sender || 'System'}]</div>
                  <div className="bg-gray-900/60 p-3 rounded border border-gray-800 text-sm whitespace-pre-wrap">
                    {msg.content || msg.text || msg.message}
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

      </div>
    </div>
  );
};

export default LanguageSimulation;
