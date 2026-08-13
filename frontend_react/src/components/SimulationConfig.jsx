import React, { useState } from 'react';
import axios from 'axios';

const SimulationConfig = ({ simId, setSimId, isRunning, setIsRunning, setAgentsState }) => {
  const [seedText, setSeedText] = useState('');
  const [seedArtifacts, setSeedArtifacts] = useState([]);
  const [verboseMode, setVerboseMode] = useState(false);
  
  const [endStateCondition, setEndStateCondition] = useState('');
  const [maxTokens, setMaxTokens] = useState('');
  const [agents, setAgents] = useState([{ name: '', system_prompt: '', model: 'gemini-2.5-flash-8b' }]);
  const [isSpawning, setIsSpawning] = useState(false);
  const [error, setError] = useState('');

  const loadSwarmTemplate = () => {
    setSeedText("The Github Swarm is now online. ProjectManager, please analyze the repository, identify 3 high-impact features or bugs, and file them as issues. Developer, wait for the issues to be filed, then pick one to implement.");
    setEndStateCondition("End when a PR is merged or the team concludes their work.");
    
    const newAgents = [
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
    ];
    setAgents(newAgents);
    if (setAgentsState) setAgentsState(newAgents);
  };

  const handleAddAgent = () => {
    const newAgents = [...agents, { name: '', system_prompt: '', model: 'gemini-2.5-flash-8b' }];
    setAgents(newAgents);
    if (setAgentsState) setAgentsState(newAgents);
  };

  const handleRemoveAgent = (index) => {
    const newAgents = agents.filter((_, i) => i !== index);
    setAgents(newAgents);
    if (setAgentsState) setAgentsState(newAgents);
  };

  const handleAgentChange = (index, field, value) => {
    const newAgents = [...agents];
    newAgents[index][field] = value;
    setAgents(newAgents);
    if (setAgentsState) setAgentsState(newAgents);
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
        name: `Sim-${new Date().toISOString()}`,
        seed: Math.floor(Math.random() * 1000000),
        seed_prompt: JSON.stringify(finalSeedPrompt),
        end_state_condition: endStateCondition,
        agents_config: agents.filter(a => a.name.trim() !== '' && a.system_prompt.trim() !== ''),
        verbose_mode: verboseMode,
        max_tokens: maxTokens ? parseInt(maxTokens) : null
      };
      
      const res = await axios.post('/api/simulations/language/spawn', payload);
      const newSimId = res.data?.id || res.data?.sim_id || res.data;
      if (typeof newSimId === 'string' || typeof newSimId === 'number') {
        setSimId(newSimId);
        if (setAgentsState) setAgentsState(payload.agents_config);
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
        setMaxTokens(sim.max_tokens || '');
        setVerboseMode(sim.verbose_mode || false);
        if (sim.agents_config) {
          setAgents(sim.agents_config);
          if (setAgentsState) setAgentsState(sim.agents_config);
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

  const handleKill = async () => {
    if (!simId) return;
    try {
      await axios.post(`/api/simulations/${simId}/kill`);
      setIsRunning(false);
    } catch (err) {
      console.error('Error stopping simulation:', err);
      setError('Failed to send kill signal.');
    }
  };

  return (
    <div className="h-full flex flex-col font-mono text-gray-300">
      <div className="flex justify-between items-end border-b border-gray-800 pb-2 mb-6">
        <div className="flex items-end gap-4">
            <h1 className="text-2xl text-cyan-400 text-glow-cyan uppercase tracking-wider">
              Swarm Config
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
          <span className="text-xs uppercase text-gray-400 group-hover:text-cyan-400 transition-colors">Verbose</span>
          <div className="relative">
            <input type="checkbox" checked={verboseMode} onChange={(e) => setVerboseMode(e.target.checked)} className="sr-only" />
            <div className={`block w-10 h-6 rounded-full transition-colors ${verboseMode ? 'bg-cyan-600' : 'bg-gray-800 border border-gray-700'}`}></div>
            <div className={`dot absolute left-1 top-1 bg-cyan-400 w-4 h-4 rounded-full transition-transform ${verboseMode ? 'transform translate-x-4 bg-white' : ''}`}></div>
          </div>
        </label>
      </div>
      
      <div className="flex-1 glass-panel p-6 flex flex-col gap-4 overflow-y-auto border border-gray-800 bg-gray-900/40 rounded-lg">
        <div className="flex justify-between items-center mb-2">
          <h2 className="text-xl text-emerald-400 uppercase tracking-wide">Initialization</h2>
          <button onClick={loadSwarmTemplate} className="text-xs px-2 py-1 bg-emerald-900/30 hover:bg-emerald-900/50 text-emerald-400 border border-emerald-700 rounded transition-colors uppercase">
            Load Default Simulation
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
            <label className="text-xs uppercase text-gray-500">Agents Matrix</label>
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
                  <span className="text-xs text-purple-400">Agent Node {index + 1}</span>
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
          {!isRunning ? (
            <button
              onClick={handleRun}
              disabled={!simId}
              className={`flex-1 py-2 font-bold uppercase tracking-wider border transition-colors ${!simId ? 'bg-gray-800 border-gray-700 text-gray-500 cursor-not-allowed' : 'bg-purple-900/30 border-purple-500 text-purple-400 hover:bg-purple-900/50 hover:text-glow-purple'}`}
            >
              Run Simulation
            </button>
          ) : (
            <button
              onClick={handleKill}
              className="flex-1 py-2 font-bold uppercase tracking-wider border transition-colors bg-red-900/30 border-red-500 text-red-400 hover:bg-red-900/50 hover:text-glow-red"
            >
              KILL SWITCH
            </button>
          )}
        </div>
        
        {simId && (
          <div className="text-xs text-emerald-500 mt-2 text-center font-bold">
            MATRIX ACTIVE: {simId}
          </div>
        )}
      </div>
    </div>
  );
};

export default SimulationConfig;
