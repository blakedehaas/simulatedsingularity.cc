import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import Monetization from './components/Monetization';
import DynamicDashboard from './components/DynamicDashboard';
import TemporalFork from './components/TemporalFork';
import DocumentationRAG from './components/DocumentationRAG';

function App() {
  const [data, setData] = useState(0);
  const [epochs, setEpochs] = useState(0);

  useEffect(() => {
    const dataPerSecond = 1 * (1 + epochs * 0.5);
    const interval = setInterval(() => {
      setData(prev => prev + dataPerSecond);
    }, 1000);
    return () => clearInterval(interval);
  }, [epochs]);

  const handleExtract = () => {
    const dataPerClick = 1 * (1 + epochs * 0.5);
    setData(prev => prev + dataPerClick);
  };

  const handleAscend = () => {
    setData(0);
    setEpochs(prev => prev + 1);
  };

  const navItemClass = ({ isActive }) => 
    `px-4 py-2 text-sm uppercase tracking-wider transition-colors ${isActive ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-gray-500 hover:text-gray-300'}`;

  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col relative z-10">
        {/* Navigation Bar */}
        <nav className="glass-panel sticky top-0 z-50 flex items-center justify-between px-6 py-2 border-b border-gray-800">
          <div className="flex space-x-2">
            <NavLink to="/" className={navItemClass}>[SWARM COMMAND]</NavLink>
            <NavLink to="/temporal" className={navItemClass}>[TEMPORAL RAG]</NavLink>
            <NavLink to="/docs" className={navItemClass}>[DOCS RAG]</NavLink>
            <NavLink to="/store" className={navItemClass}>[STORE]</NavLink>
          </div>
          
          <div className="flex items-center space-x-6 text-sm">
            <div className="flex flex-col items-end">
              <span className="text-gray-500">DATA</span>
              <span className="text-cyan-400 font-bold text-glow-cyan">{Math.floor(data)}</span>
            </div>
            <div className="flex flex-col items-end">
              <span className="text-gray-500">EPOCH</span>
              <span className="text-purple-400 font-bold text-glow-purple">{epochs}</span>
            </div>
            <button 
              onClick={handleExtract}
              className="px-3 py-1 bg-gray-900 border border-gray-700 hover:border-cyan-500 text-cyan-500 hover:bg-gray-800 transition-colors"
            >
              EXTRACT
            </button>
            {data > 100 && (
              <button 
                onClick={handleAscend}
                className="px-3 py-1 bg-purple-900/30 border border-purple-500 text-purple-400 hover:bg-purple-900/50 transition-colors text-glow-purple"
              >
                ASCEND
              </button>
            )}
          </div>
        </nav>

        {/* Main Content Area */}
        <main className="flex-1 p-6 overflow-hidden flex flex-col">
          <Routes>
            <Route path="/" element={<DynamicDashboard />} />
            <Route path="/temporal" element={<TemporalFork />} />
            <Route path="/docs" element={<DocumentationRAG />} />
            <Route path="/store" element={<Monetization />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
