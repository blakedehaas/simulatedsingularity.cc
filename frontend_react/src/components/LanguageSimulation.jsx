import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const LanguageSimulation = () => {
  const [seedText, setSeedText] = useState('');
  const [seedArtifacts, setSeedArtifacts] = useState([]);
  const [verboseMode, setVerboseMode] = useState(false);
  
  const [endStateCondition, setEndStateCondition] = useState('');
  const [agents, setAgents] = useState([{ name: '', system_prompt: '', model: 'gemini-2.5-flash-8b' }]);
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

  const loadSwarmTemplate = () => {
    setSeedText("The Github Swarm is now online. ProjectManager, please analyze the repository, identify 3 high-impact features or bugs, and file them as issues. Developer, wait for the issues to be filed, then pick one to implement.");
    setEndStateCondition("End when a PR is merged or the team concludes their work.");
    setAgents([
      {
        name: "ProjectManager",
        model: "gemini-2.5-flash-8b",
        system_prompt: "You are the ProjectManager. You analyze the codebase, identify issues, and file them using the create_github_issue tool. Once you file issues, tell the Developer to start."
      },
      {
        name: "Developer",
        model: "gemini-2.5-flash-8b",
        system_prompt: "You are the Developer. You wait for the ProjectManager to create issues. Then you use execute_git_command, read_file, and write_file to implement the changes in a feature branch. Finally, you commit, push, and use create_pull_request to open a PR against dev."
      },
      {
        name: "CodeReviewer",
        model: "gemini-2.5-flash-8b",
        system_prompt: "You are the CodeReviewer. You review PRs created by the Developer. You can accept or reject them and provide feedback."
      }
    ]);
  };

  const handleAddAgent = () => {
    setAgents([...agents, { name: '', system_prompt: '', model: 'gemini-2.5-flash-8b' }]);
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

  const handleFileUpload = (e) => {
    const files = Array.from(e.target.files);
    files.forEach(file => {
      const reader = new FileReader();
      reader.onload = (event) => {
        const result = event.target.result;
        const base64Data = result.split(',')[1];
        setSeedArtifacts(prev => [...prev, {
          name: file.name,
          mimeType: file.type,
          data: base64Data,
          dataUrl: result
        }]);
      };
      reader.readAsDataURL(file);
    });
    // Reset file input
    e.target.value = '';
  };

  const handleRemoveArtifact = (index) => {
    setSeedArtifacts(prev => prev.filter((_, i) => i !== index));
  };

  const handleSpawn = async () => {
    setIsSpawning(true);
    setError('');
    try {
      const finalSeedPrompt = [
        { text: seedText },
        ...seedArtifacts.map(a => ({ inlineData: { mimeType: a.mimeType, data: a.data } }))
      ];

      const payload = {
        seed_prompt: JSON.stringify(finalSeedPrompt),
        end_state_condition: endStateCondition,
        agents_config: agents.filter(a => a.name.trim() !== '' && a.system_prompt.trim() !== ''),
        verbose_mode: verboseMode
      };
      
      const res = await axios.post('/api/simulations/language/spawn', payload);
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

  const handleExport = async () => {
    if (!simId) return;
    try {
      const res = await axios.get(`/api/simulations/${simId}/export`);
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(res.data, null, 2));
      const downloadAnchorNode = document.createElement('a');
      downloadAnchorNode.setAttribute("href", dataStr);
      downloadAnchorNode.setAttribute("download", `simulation_${simId}.json`);
      document.body.appendChild(downloadAnchorNode);
      downloadAnchorNode.click();
      downloadAnchorNode.remove();
    } catch (err) {
      console.error('Error exporting simulation:', err);
      setError('Failed to export simulation.');
    }
  };

  const handleImport = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        const json = JSON.parse(event.target.result);
        const res = await axios.post('/api/simulations/import', json);
        setSimId(res.data.sim_id);
        setError('');
        
        const sim = json.simulation || {};
        try {
            const parsedSeed = JSON.parse(sim.seed_prompt || '[]');
            if (Array.isArray(parsedSeed) && parsedSeed.length > 0 && parsedSeed[0].text) {
                setSeedText(parsedSeed[0].text);
            }
        } catch(e) {
            setSeedText(sim.seed_prompt || '');
        }
        
        setEndStateCondition(sim.end_state_condition || '');
        setVerboseMode(sim.verbose_mode || false);
        if (sim.agents_config) {
          setAgents(sim.agents_config);
        }
      } catch (err) {
        console.error('Error importing simulation:', err);
        setError('Failed to import simulation. Invalid JSON or server error.');
      }
    };
    reader.readAsText(file);
    e.target.value = '';
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
    return <div className="whitespace-pre-wrap">{contentString}</div>;
  };

  return (
    <div className="flex flex-col h-full font-mono text-gray-300">
      <div className="flex justify-between items-end border-b border-gray-800 pb-2 mb-6">
        <div className="flex items-end gap-4">
            <h1 className="text-2xl text-cyan-400 text-glow-cyan uppercase tracking-wider">
              Language Simulation Matrix
            </h1>
            <div className="flex items-center gap-2 mb-1">
                <button 
                  onClick={handleExport}
                  disabled={!simId}
                  className={`text-xs px-2 py-1 rounded transition-colors uppercase ${!simId ? 'bg-gray-800 text-gray-500 cursor-not-allowed' : 'bg-gray-800 hover:bg-gray-700 text-cyan-400 border border-gray-700'}`}
                >
                  Export JSON
                </button>
                <label className="text-xs px-2 py-1 rounded transition-colors uppercase cursor-pointer bg-gray-800 hover:bg-gray-700 text-purple-400 border border-gray-700">
                  Import JSON
                  <input type="file" accept=".json" className="hidden" onChange={handleImport} />
                </label>
            </div>
        </div>
        
        <label className="flex items-center gap-2 cursor-pointer group">
          <span className="text-xs uppercase text-gray-400 group-hover:text-cyan-400 transition-colors">Verbose Mode</span>
          <div className="relative">
            <input type="checkbox" checked={verboseMode} onChange={(e) => setVerboseMode(e.target.checked)} className="sr-only" />
            <div className={`block w-10 h-6 rounded-full transition-colors ${verboseMode ? 'bg-cyan-600' : 'bg-gray-800 border border-gray-700'}`}></div>
            <div className={`dot absolute left-1 top-1 bg-cyan-400 w-4 h-4 rounded-full transition-transform ${verboseMode ? 'transform translate-x-4 bg-white' : ''}`}></div>
          </div>
        </label>
      </div>
      
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 overflow-hidden">
        
        {/* Configuration Panel */}
        <div className="glass-panel p-6 flex flex-col gap-4 overflow-y-auto border border-gray-800 bg-gray-900/40 rounded-lg">
          <div className="flex justify-between items-center mb-2">
            <h2 className="text-xl text-emerald-400 uppercase tracking-wide">Configuration</h2>
            <button onClick={loadSwarmTemplate} className="text-xs px-2 py-1 bg-emerald-900/30 hover:bg-emerald-900/50 text-emerald-400 border border-emerald-700 rounded transition-colors uppercase">
              Load Swarm Template
            </button>
          </div>
          
          <div className="flex flex-col gap-2">
            <label className="text-xs uppercase text-gray-500">Seed Prompt</label>
            <textarea 
              value={seedText}
              onChange={(e) => setSeedText(e.target.value)}
              className="bg-black/50 border border-gray-700 rounded p-2 text-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 transition-colors h-24 resize-none"
              placeholder="Initial context or prompt to kickstart the simulation..."
            />
            
            <div className="flex items-center gap-4 mt-2">
              <label className="cursor-pointer bg-gray-800 hover:bg-gray-700 text-cyan-400 border border-gray-700 text-xs px-3 py-1.5 rounded transition-colors uppercase">
                + Attach Artifacts
                <input type="file" multiple accept="image/*,audio/*" className="hidden" onChange={handleFileUpload} />
              </label>
            </div>
            
            {seedArtifacts.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2 p-2 bg-black/30 border border-gray-800 rounded">
                {seedArtifacts.map((artifact, i) => (
                  <div key={i} className="flex items-center gap-2 bg-gray-900 p-1 pr-2 rounded border border-gray-700">
                    {artifact.mimeType.startsWith('image/') ? (
                      <img src={artifact.dataUrl} className="w-8 h-8 object-cover rounded" />
                    ) : (
                      <div className="w-8 h-8 flex items-center justify-center bg-gray-800 rounded text-xs">🔊</div>
                    )}
                    <span className="text-xs max-w-[100px] truncate">{artifact.name}</span>
                    <button onClick={() => handleRemoveArtifact(i)} className="text-red-500 hover:text-red-400 ml-1">×</button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex flex-col gap-2 mt-2">
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
                  <select
                    value={agent.model || 'gemini-2.5-flash-8b'}
                    onChange={(e) => handleAgentChange(index, 'model', e.target.value)}
                    className="bg-black/50 border border-gray-700 rounded p-2 text-sm focus:border-cyan-500 focus:outline-none text-gray-300"
                  >
                    <option value="gemini-2.5-flash-8b">gemini-2.5-flash-8b (Text/Vision)</option>
                    <option value="gemini-3.1-flash-image">gemini-3.1-flash-image (Image Generation)</option>
                    <option value="gemini-3.1-flash-tts-preview">gemini-3.1-flash-tts-preview (Audio Generation)</option>
                  </select>
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
                  <div className="bg-gray-900/60 p-3 rounded border border-gray-800 text-sm">
                    {renderContent(msg.content || msg.text || msg.message)}
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
