import React, { useState, useEffect } from 'react';

const TemporalFork = () => {
  const [targetAge, setTargetAge] = useState(25);
  const [agents, setAgents] = useState([]);
  const [selectedAgents, setSelectedAgents] = useState([]);
  const [logs, setLogs] = useState([]);
  const [isSimulating, setIsSimulating] = useState(false);

  const handleFork = () => {
    if (agents.some(a => a.age === targetAge)) return; // Prevent duplicates
    
    const newAgent = {
      id: `agent-${targetAge}`,
      age: targetAge,
      type: targetAge < 20 ? 'Naive' : targetAge < 35 ? 'Pragmatic' : 'Cynical',
    };
    
    setAgents(prev => [...prev, newAgent].sort((a, b) => a.age - b.age));
    setLogs(prev => [...prev, `[SYSTEM] Forked consciousness at age ${targetAge}. Type: ${newAgent.type}`]);
  };

  const toggleSelection = (agent) => {
    setSelectedAgents(prev => {
      const isSelected = prev.some(a => a.id === agent.id);
      if (isSelected) {
        return prev.filter(a => a.id !== agent.id);
      } else {
        if (prev.length >= 2) return [prev[1], agent]; // Keep max 2
        return [...prev, agent];
      }
    });
  };

  const initiateDialectic = () => {
    if (selectedAgents.length !== 2) return;
    setIsSimulating(true);
    setLogs(prev => [...prev, `[SYSTEM] Initiating dialectic between Age ${selectedAgents[0].age} and Age ${selectedAgents[1].age}...`]);

    const a1 = selectedAgents[0];
    const a2 = selectedAgents[1];
    const delta = Math.abs(a1.age - a2.age);
    
    const dialogue = [
      { agent: a1, text: `I can't believe what you've compromised on.` },
      { agent: a2, text: `It's not compromise. It's survival.` },
      { agent: a1, text: `We used to have principles.` },
      { agent: a2, text: delta > 10 ? `Principles don't pay the rent.` : `They evolve, just like we did.` }
    ];

    dialogue.forEach((line, index) => {
      setTimeout(() => {
        setLogs(prev => [...prev, `[Age ${line.agent.age}]: ${line.text}`]);
        if (index === dialogue.length - 1) {
          setTimeout(() => setIsSimulating(false), 1000);
        }
      }, (index + 1) * 1500);
    });
  };

  return (
    <div className="flex-1 flex flex-col h-full space-y-6">
      <div className="grid grid-cols-3 gap-6 h-full">
        {/* Control Panel */}
        <div className="glass-panel p-6 flex flex-col space-y-6">
          <h2 className="text-xl font-bold text-cyan-400">TEMPORAL RAG</h2>
          
          <div className="space-y-4">
            <label className="block text-gray-400 text-sm">TARGET AGE: {targetAge}</label>
            <input 
              type="range" 
              min="10" 
              max="40" 
              value={targetAge}
              onChange={(e) => setTargetAge(Number(e.target.value))}
              className="w-full accent-cyan-500"
            />
            <button 
              onClick={handleFork}
              className="w-full py-2 bg-cyan-900/30 border border-cyan-500 text-cyan-400 hover:bg-cyan-900/50 transition-colors font-bold"
            >
              FORK CONSCIOUSNESS
            </button>
          </div>

          <div className="flex-1 overflow-y-auto pt-4 border-t border-gray-800">
            <h3 className="text-sm text-gray-500 mb-4">ACTIVE FRAGMENTS ({agents.length})</h3>
            <div className="space-y-3">
              {agents.map(agent => {
                const isSelected = selectedAgents.some(a => a.id === agent.id);
                return (
                  <div 
                    key={agent.id}
                    onClick={() => toggleSelection(agent)}
                    className={`p-3 cursor-pointer border transition-all ${
                      isSelected 
                        ? 'border-cyan-400 bg-cyan-900/20 shadow-[0_0_10px_rgba(6,182,212,0.3)]' 
                        : 'border-gray-700 bg-gray-900/50 hover:border-gray-500'
                    }`}
                  >
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-gray-200">Age {agent.age}</span>
                      <span className="text-xs text-gray-500">{agent.type}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Dialectic Area */}
        <div className="col-span-2 glass-panel p-6 flex flex-col">
          <div className="flex justify-between items-center mb-6 border-b border-gray-800 pb-4">
            <h2 className="text-xl font-bold text-purple-400">DIALECTIC ENGINE</h2>
            <button 
              onClick={initiateDialectic}
              disabled={selectedAgents.length !== 2 || isSimulating}
              className={`px-6 py-2 border font-bold transition-colors ${
                selectedAgents.length === 2 && !isSimulating
                  ? 'bg-purple-900/30 border-purple-500 text-purple-400 hover:bg-purple-900/50'
                  : 'bg-gray-900 border-gray-700 text-gray-600 cursor-not-allowed'
              }`}
            >
              INITIATE
            </button>
          </div>

          <div className="flex-1 bg-black/50 p-4 border border-gray-800 overflow-y-auto font-mono text-sm">
            {logs.length === 0 ? (
              <div className="text-gray-600 italic">Select exactly two fragments to initiate a dialectic.</div>
            ) : (
              logs.map((log, i) => (
                <div key={i} className={`mb-2 ${log.startsWith('[SYSTEM]') ? 'text-gray-500 text-xs' : 'text-gray-300'}`}>
                  {log}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TemporalFork;
