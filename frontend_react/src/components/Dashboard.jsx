import React, { useState } from 'react';
import SimulationConfig from './SimulationConfig';
import C2Terminal from './C2Terminal';

const Dashboard = () => {
  const [simId, setSimId] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [agentsState, setAgentsState] = useState([]);

  return (
    <div className="h-full flex flex-col md:flex-row gap-6 p-2">
      {/* Left Pane: Configuration (40% width on large screens) */}
      <div className="w-full md:w-[40%] flex flex-col min-w-[300px]">
        <SimulationConfig 
          simId={simId} 
          setSimId={setSimId} 
          isRunning={isRunning} 
          setIsRunning={setIsRunning}
          setAgentsState={setAgentsState}
        />
      </div>

      {/* Right Pane: Terminal Log (60% width on large screens) */}
      <div className="w-full md:w-[60%] flex flex-col min-w-[400px]">
        <C2Terminal simId={simId} agentsState={agentsState} />
      </div>
    </div>
  );
};

export default Dashboard;
