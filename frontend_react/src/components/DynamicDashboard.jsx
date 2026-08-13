import React, { useState, useEffect } from 'react';
import { Responsive, WidthProvider } from 'react-grid-layout';
import { apiClient } from '../api';
import SimulationConfig from './SimulationConfig';
import C2Terminal from './C2Terminal';
import ProductionSwarmVisualizer from './ProductionSwarmVisualizer';
import WidgetEngine from './WidgetEngine';

const ResponsiveGridLayout = WidthProvider(Responsive);

const getFromLS = (key) => {
  let ls = {};
  if (global.localStorage) {
    try {
      ls = JSON.parse(global.localStorage.getItem("rgl-dynamic")) || {};
    } catch (e) {
      /*Ignore*/
    }
  }
  return ls[key];
};

const saveToLS = (key, value) => {
  if (global.localStorage) {
    global.localStorage.setItem(
      "rgl-dynamic",
      JSON.stringify({
        [key]: value
      })
    );
  }
};

const DynamicDashboard = () => {
  const [schema, setSchema] = useState(null);
  const [layouts, setLayouts] = useState(getFromLS("layouts") || { lg: [] });
  const [fullscreenWidget, setFullscreenWidget] = useState(null);

  // Global state to share between custom widgets
  const [simId, setSimId] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [agentsState, setAgentsState] = useState([]);
  const [messages, setMessages] = useState([]);
  const [localState, setLocalState] = useState({});

  useEffect(() => {
    const fetchSchema = async () => {
      try {
        const res = await apiClient.get('/ui/schema');
        if (res.data && res.data.panels) {
          setSchema(res.data);
          
          // If no layouts in local storage, initialize from schema
          const saved = getFromLS("layouts");
          if (!saved || !saved.lg || saved.lg.length === 0) {
            const initialLg = res.data.panels.map(p => ({
              i: p.id,
              x: p.grid.x,
              y: p.grid.y,
              w: p.grid.w,
              h: p.grid.h
            }));
            setLayouts({ lg: initialLg });
          }
        }
      } catch (err) {
        console.error("Failed to load UI schema", err);
      }
    };
    fetchSchema();
  }, []);

  const onLayoutChange = (layout, newLayouts) => {
    saveToLS("layouts", newLayouts);
    setLayouts(newLayouts);
  };

  const renderComponent = (element) => {
    if (element.type === 'custom') {
      switch (element.component) {
        case 'SimulationConfigWidget':
          return (
            <div className="h-full overflow-y-auto pb-4">
              <SimulationConfig 
                simId={simId} 
                setSimId={setSimId} 
                isRunning={isRunning} 
                setIsRunning={setIsRunning}
                setAgentsState={setAgentsState}
              />
            </div>
          );
        case 'ProductionSwarmVisualizer':
          return <ProductionSwarmVisualizer simId={simId} agentsState={agentsState} messages={messages} />;
        case 'C2Terminal':
          return <C2Terminal simId={simId} messages={messages} setMessages={setMessages} />;
        default:
          return <div className="p-4 text-red-500">Unknown custom component: {element.component}</div>;
      }
    }
    
    // Generic UI Primitive rendering
    return <WidgetEngine element={element} localState={localState} setLocalState={setLocalState} />;
  };

  const PanelWrapper = ({ panel }) => {
    const isFullscreen = fullscreenWidget === panel.id;
    
    if (isFullscreen) {
      return (
        <div className="fixed inset-0 z-[9999] bg-[#050505] p-4 flex flex-col glass-panel">
          <div className={`flex justify-between items-center p-2 mb-2 bg-gray-900 border-b border-gray-700`}>
            <h3 className={`font-bold uppercase tracking-widest ${panel.colorClass}`}>{panel.title}</h3>
            <button 
              onClick={() => setFullscreenWidget(null)}
              className="text-gray-400 hover:text-white px-2 py-1"
            >
              [RESTORE]
            </button>
          </div>
          <div className="flex-1 overflow-hidden relative">
            {panel.elements.map((el, i) => <React.Fragment key={i}>{renderComponent(el)}</React.Fragment>)}
          </div>
        </div>
      );
    }

    return (
      <div className="h-full flex flex-col glass-panel rounded overflow-hidden">
        <div className={`panel-drag-handle cursor-move flex justify-between items-center p-2 bg-gray-900/80 border-b border-gray-800`}>
          <h3 className={`font-bold text-xs uppercase tracking-widest ${panel.colorClass} drop-shadow-[0_0_8px_currentColor]`}>{panel.title}</h3>
          <button 
            onMouseDown={(e) => e.stopPropagation()} 
            onClick={() => setFullscreenWidget(panel.id)}
            className="text-gray-500 hover:text-cyan-400 text-xs px-1"
          >
            [MAXIMIZE]
          </button>
        </div>
        <div className="flex-1 overflow-hidden relative p-1 bg-black/40">
           {panel.elements.map((el, i) => <React.Fragment key={i}>{renderComponent(el)}</React.Fragment>)}
        </div>
      </div>
    );
  };

  if (!schema) {
    return <div className="p-10 text-cyan-500 animate-pulse">Initializing UI Matrix from Server Schema...</div>;
  }

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
        {schema.panels.map(panel => (
          <div key={panel.id}>
            <PanelWrapper panel={panel} />
          </div>
        ))}
      </ResponsiveGridLayout>
    </div>
  );
};

export default DynamicDashboard;
