import React, { useState } from 'react';

const MediaEngine = () => {
  const [activeTab, setActiveTab] = useState('text-to-video');
  const [prompt, setPrompt] = useState('');
  const [isSynthesizing, setIsSynthesizing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [timelineTracks, setTimelineTracks] = useState([
    { id: 1, type: 'video', clips: [{ id: 'v1', start: 10, width: 40, color: 'bg-cyan-600' }] },
    { id: 2, type: 'audio', clips: [{ id: 'a1', start: 15, width: 30, color: 'bg-emerald-600' }] }
  ]);

  const handleSynthesize = () => {
    if (!prompt) return;
    setIsSynthesizing(true);
    setProgress(0);
    
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsSynthesizing(false);
          // Add new clip to video track
          setTimelineTracks(tracks => {
            const newTracks = [...tracks];
            newTracks[0].clips.push({
              id: Date.now().toString(),
              start: 60,
              width: 25,
              color: 'bg-purple-600'
            });
            return newTracks;
          });
          setPrompt('');
          return 0;
        }
        return prev + 5;
      });
    }, 100);
  };

  return (
    <div className="flex-1 flex flex-col h-full space-y-6">
      
      {/* Top Half: Preview and Controls */}
      <div className="grid grid-cols-3 gap-6 flex-[2]">
        
        {/* Preview Panel */}
        <div className="col-span-2 glass-panel flex flex-col overflow-hidden relative">
          <div className="bg-black flex-1 flex items-center justify-center border-b border-gray-800">
            {isSynthesizing ? (
              <div className="flex flex-col items-center">
                <div className="w-16 h-16 border-4 border-cyan-900 border-t-cyan-400 rounded-full animate-spin mb-4"></div>
                <div className="text-cyan-400 font-mono text-sm">SYNTHESIZING {progress}%</div>
              </div>
            ) : (
              <span className="text-gray-700 font-mono">NO SIGNAL / WAITING FOR RENDER</span>
            )}
          </div>
          <div className="p-4 bg-gray-900/50 flex items-center justify-center space-x-4">
            <button className="text-gray-400 hover:text-white">◁</button>
            <button className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center hover:bg-gray-600">
              <div className="w-0 h-0 border-t-[6px] border-t-transparent border-l-[10px] border-l-white border-b-[6px] border-b-transparent ml-1"></div>
            </button>
            <button className="text-gray-400 hover:text-white">▷</button>
            <div className="flex-1 h-2 bg-gray-800 rounded mx-4 relative overflow-hidden">
               <div className="absolute top-0 left-0 h-full bg-cyan-500 w-1/3"></div>
            </div>
            <span className="text-xs font-mono text-gray-500">00:01:23 / 00:05:00</span>
          </div>
        </div>

        {/* AI Generation Panel */}
        <div className="glass-panel p-6 flex flex-col">
          <h2 className="text-xl font-bold text-cyan-400 mb-4">GENERATIVE PIPELINE</h2>
          
          <div className="flex space-x-1 mb-6 bg-gray-900/50 p-1 rounded">
            {['text-to-video', 'enhance', 'animate'].map(tab => (
              <button 
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 text-xs py-2 uppercase ${activeTab === tab ? 'bg-gray-800 text-white' : 'text-gray-500 hover:text-gray-300'}`}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="flex-1 flex flex-col space-y-4">
            <textarea 
              className="flex-1 bg-black/50 border border-gray-700 p-3 text-sm font-mono text-gray-300 resize-none focus:outline-none focus:border-cyan-500"
              placeholder="Enter neural prompt..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={isSynthesizing}
            ></textarea>
            
            <button 
              onClick={handleSynthesize}
              disabled={!prompt || isSynthesizing}
              className={`py-3 font-bold transition-all ${
                prompt && !isSynthesizing 
                  ? 'bg-cyan-900/30 border border-cyan-500 text-cyan-400 hover:bg-cyan-900/50 text-glow-cyan' 
                  : 'bg-gray-900 border border-gray-700 text-gray-600 cursor-not-allowed'
              }`}
            >
              {isSynthesizing ? 'PROCESSING...' : 'SYNTHESIZE MEDIA'}
            </button>
          </div>
        </div>
      </div>

      {/* Bottom Half: Timeline */}
      <div className="flex-1 glass-panel p-4 flex flex-col">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-sm font-bold text-gray-400">NON-LINEAR TIMELINE</h3>
          <button className="text-xs px-3 py-1 bg-gray-800 hover:bg-gray-700 border border-gray-600 text-white">EXPORT SEQUENCE</button>
        </div>
        
        <div className="flex-1 border border-gray-800 bg-black/30 relative flex flex-col overflow-x-auto">
          {/* Time ruler */}
          <div className="h-6 border-b border-gray-800 flex" style={{ width: '200%' }}>
            {[...Array(20)].map((_, i) => (
              <div key={i} className="flex-1 border-l border-gray-800 text-[10px] text-gray-600 pl-1">00:0{i}</div>
            ))}
          </div>
          
          {/* Tracks */}
          <div className="flex-1 relative overflow-y-auto" style={{ width: '200%' }}>
            {timelineTracks.map(track => (
              <div key={track.id} className="h-16 border-b border-gray-800/50 flex relative items-center bg-gray-900/20">
                <div className="absolute left-0 w-24 h-full bg-gray-900 border-r border-gray-700 flex items-center justify-center text-xs text-gray-500 uppercase z-10 sticky">
                  {track.type}
                </div>
                <div className="ml-24 relative w-full h-full">
                  {track.clips.map(clip => (
                    <div 
                      key={clip.id}
                      className={`absolute top-2 bottom-2 rounded-sm border border-black/50 ${clip.color} opacity-80 cursor-pointer hover:opacity-100 transition-opacity`}
                      style={{ left: `${clip.start}%`, width: `${clip.width}%` }}
                    ></div>
                  ))}
                </div>
              </div>
            ))}
            
            {/* Playhead */}
            <div className="absolute top-0 bottom-0 w-px bg-red-500 left-[33%] z-20 pointer-events-none">
              <div className="w-3 h-3 bg-red-500 absolute -top-1 -left-1 transform rotate-45"></div>
            </div>
          </div>
        </div>
      </div>
      
    </div>
  );
};

export default MediaEngine;
