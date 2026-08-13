import React, { useState, useEffect } from 'react';
import { Responsive, WidthProvider } from 'react-grid-layout';
import SimulationConfig from './SimulationConfig';
import C2Terminal from './C2Terminal';
import ProductionSwarmVisualizer from './ProductionSwarmVisualizer';

const ResponsiveGridLayout = WidthProvider(Responsive);

const getFromLS = (key) => {
  let ls = {};
  if (global.localStorage) {
    try {
      ls = JSON.parse(global.localStorage.getItem("rgl-8")) || {};
    } catch (e) {
      /*Ignore*/
    }
  }
  return ls[key];
};

const saveToLS = (key, value) => {
  if (global.localStorage) {
    global.localStorage.setItem(
      "rgl-8",
      JSON.stringify({
        [key]: value
      })
    );
  }
};

const GridDashboard = () => {
  const [simId, setSimId] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [agentsState, setAgentsState] = useState([]);
  const [messages, setMessages] = useState([]);

  // Fullscreen state
  const [fullscreenWidget, setFullscreenWidget] = useState(null);

  const initialLayouts = {
    lg: [
      { i: 'config', x: 0, y: 0, w: 4, h: 25 },
      { i: 'visualizer', x: 4, y: 0, w: 8, h: 12 },
      { i: 'terminal', x: 4, y: 12, w: 8, h: 13 }
    ]
  };

  const [layouts, setLayouts] = useState(
    getFromLS("layouts") || initialLayouts
  );

  const onLayoutChange = (layout, layouts) => {
    saveToLS("layouts", layouts);
    setLayouts(layouts);
  };

  const PanelWrapper = ({ id, title, children, colorClass }) => {
    const isFullscreen = fullscreenWidget === id;
    
    if (isFullscreen) {
      return (
        <div className="fixed inset-0 z-[9999] bg-[#050505] p-4 flex flex-col glass-panel">
          <div className={`flex justify-between items-center p-2 mb-2 bg-gray-900 border-b border-gray-700`}>
            <h3 className={`font-bold uppercase tracking-widest ${colorClass}`}>{title}</h3>
            <button 
              onClick={() => setFullscreenWidget(null)}
              className="text-gray-400 hover:text-white px-2 py-1"
            >
              [RESTORE]
            </button>
          </div>
          <div className="flex-1 overflow-hidden relative">
            {children}
          </div>
        </div>
      );
    }

    return (
      <div className="h-full flex flex-col glass-panel rounded overflow-hidden">
        <div className={`panel-drag-handle cursor-move flex justify-between items-center p-2 bg-gray-900/80 border-b border-gray-800`}>
          <h3 className={`font-bold text-xs uppercase tracking-widest ${colorClass} drop-shadow-[0_0_8px_currentColor]`}>{title}</h3>
          <button 
            onMouseDown={(e) => e.stopPropagation()} // Prevent drag when clicking maximize
            onClick={() => setFullscreenWidget(id)}
            className="text-gray-500 hover:text-cyan-400 text-xs px-1"
          >
            [MAXIMIZE]
          </button>
        </div>
        <div className="flex-1 overflow-hidden relative p-1 bg-black/40">
          {children}
        </div>
      </div>
    );
  };

  return (
    <div className="flex-1 w-full h-full p-2 relative overflow-y-auto">
      <ResponsiveGridLayout
        className="layout"
        layouts={layouts}
        breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
        cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
        rowHeight={30}
        onLayoutChange={onLayoutChange}
        draggableHandle=".panel-drag-handle"
        margin={[16, 16]}
      >
        <div key="config">
          <PanelWrapper id="config" title="Simulation Configuration" colorClass="text-emerald-400">
            <div className="h-full overflow-y-auto pb-4">
                <SimulationConfig 
                simId={simId} 
                setSimId={setSimId} 
                isRunning={isRunning} 
                setIsRunning={setIsRunning}
                setAgentsState={setAgentsState}
                />
            </div>
          </PanelWrapper>
        </div>
        
        <div key="visualizer">
          <PanelWrapper id="visualizer" title="Swarm Topology Visualizer" colorClass="text-purple-400">
            <ProductionSwarmVisualizer simId={simId} agentsState={agentsState} messages={messages} />
          </PanelWrapper>
        </div>

        <div key="terminal">
          <PanelWrapper id="terminal" title="Global Observation Deck" colorClass="text-cyan-400">
             <C2Terminal simId={simId} messages={messages} setMessages={setMessages} />
          </PanelWrapper>
        </div>
      </ResponsiveGridLayout>
    </div>
  );
};

export default GridDashboard;
