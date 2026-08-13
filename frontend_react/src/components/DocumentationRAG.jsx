import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

const DocumentationRAG = () => {
  const [messages, setMessages] = useState([
    { sender: 'system', text: 'Simulated Singularity Architect LLM is online. Ask questions about the codebase, API endpoints, or swarm topology.' }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const query = input.trim();
    setInput('');
    setMessages(prev => [...prev, { sender: 'user', text: query }]);
    setIsTyping(true);

    try {
      const res = await axios.post('/docs-api/chat', { query });
      setMessages(prev => [...prev, { sender: 'system', text: res.data.response }]);
    } catch (err) {
      console.error('RAG Error:', err);
      let errorMsg = 'Failed to connect to the Architect LLM. Make sure docs_server is running on port 8080.';
      if (err.response && err.response.data && err.response.data.response) {
        errorMsg = err.response.data.response;
      }
      setMessages(prev => [...prev, { sender: 'system', text: errorMsg, isError: true }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full font-mono">
      <div className="glass-panel p-6 border-b-2 border-b-cyan-500 flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-cyan-400 tracking-widest">ARCHITECT RAG</h1>
          <p className="text-gray-400 text-sm mt-1">Retrieval-Augmented Generation context query interface.</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_#10b981] animate-pulse"></div>
          <span className="text-xs text-gray-500 tracking-widest">KNOWLEDGE BASE SYNCED</span>
        </div>
      </div>

      <div className="flex-1 glass-panel flex flex-col overflow-hidden border border-gray-800">
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}>
              <div className={`text-xs mb-1 ${msg.sender === 'user' ? 'text-gray-500 mr-1' : 'text-cyan-500 ml-1'}`}>
                [{msg.sender === 'user' ? 'GUEST' : 'ARCHITECT'}]
              </div>
              <div className={`p-4 rounded max-w-3xl whitespace-pre-wrap ${
                msg.sender === 'user' 
                  ? 'bg-gray-800 text-gray-300 border border-gray-700' 
                  : msg.isError 
                    ? 'bg-red-900/30 text-red-400 border border-red-800' 
                    : 'bg-cyan-900/10 text-cyan-50 border border-cyan-900/50'
              }`}>
                {msg.text}
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="flex flex-col items-start">
              <div className="text-xs mb-1 text-cyan-500 ml-1">[ARCHITECT]</div>
              <div className="p-4 rounded max-w-3xl bg-cyan-900/10 border border-cyan-900/50 text-cyan-400 animate-pulse">
                Synthesizing response...
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        <div className="p-4 bg-black/40 border-t border-gray-800">
          <form onSubmit={handleSend} className="flex gap-4">
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Query the codebase..."
              className="flex-1 bg-gray-900 border border-gray-700 rounded px-4 py-3 text-cyan-100 focus:outline-none focus:border-cyan-500 transition-colors"
              disabled={isTyping}
            />
            <button 
              type="submit"
              disabled={isTyping || !input.trim()}
              className={`px-8 font-bold tracking-widest border transition-colors ${
                isTyping || !input.trim() 
                  ? 'bg-gray-800 border-gray-700 text-gray-500 cursor-not-allowed' 
                  : 'bg-cyan-900/30 border-cyan-500 text-cyan-400 hover:bg-cyan-900/50 hover:text-glow-cyan'
              }`}
            >
              TRANSMIT
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default DocumentationRAG;
