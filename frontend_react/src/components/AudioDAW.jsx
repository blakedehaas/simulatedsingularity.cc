import React, { useState, useEffect, useRef } from 'react';

const AudioDAW = () => {
  const [engineReady, setEngineReady] = useState(false);
  const audioCtxRef = useRef(null);
  const activeOscillatorsRef = useRef({});
  const analyserRef = useRef(null);
  const canvasRef = useRef(null);
  const animationFrameRef = useRef(null);

  // Synth Parameters
  const [waveform, setWaveform] = useState('sine');
  const [attack, setAttack] = useState(0.1);
  const [decay, setDecay] = useState(0.2);
  const [sustain, setSustain] = useState(0.5);
  const [release, setRelease] = useState(0.5);

  const initAudio = () => {
    if (!audioCtxRef.current) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      audioCtxRef.current = new AudioContext();
      analyserRef.current = audioCtxRef.current.createAnalyser();
      analyserRef.current.fftSize = 2048;
      analyserRef.current.connect(audioCtxRef.current.destination);
      setEngineReady(true);
      drawWaveform();
    }
  };

  const noteToFreq = (note) => {
    const notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
    const octave = parseInt(note.slice(-1), 10);
    const keyNumber = notes.indexOf(note.slice(0, -1));
    
    if (keyNumber < 0) return 440;
    
    const noteIndex = keyNumber + ((octave - 4) * 12);
    return 261.63 * Math.pow(2, noteIndex / 12);
  };

  const noteOn = (note) => {
    if (!audioCtxRef.current) return;
    
    const ctx = audioCtxRef.current;
    const osc = ctx.createOscillator();
    const gainNode = ctx.createGain();
    
    osc.type = waveform;
    osc.frequency.setValueAtTime(noteToFreq(note), ctx.currentTime);
    
    // ADSR Envelope
    gainNode.gain.setValueAtTime(0, ctx.currentTime);
    gainNode.gain.linearRampToValueAtTime(1, ctx.currentTime + parseFloat(attack));
    gainNode.gain.linearRampToValueAtTime(parseFloat(sustain), ctx.currentTime + parseFloat(attack) + parseFloat(decay));
    
    osc.connect(gainNode);
    gainNode.connect(analyserRef.current);
    
    osc.start();
    
    activeOscillatorsRef.current[note] = { osc, gainNode };
  };

  const noteOff = (note) => {
    if (!audioCtxRef.current || !activeOscillatorsRef.current[note]) return;
    
    const { osc, gainNode } = activeOscillatorsRef.current[note];
    const ctx = audioCtxRef.current;
    
    // Release
    gainNode.gain.cancelScheduledValues(ctx.currentTime);
    gainNode.gain.setValueAtTime(gainNode.gain.value, ctx.currentTime);
    gainNode.gain.linearRampToValueAtTime(0, ctx.currentTime + parseFloat(release));
    
    osc.stop(ctx.currentTime + parseFloat(release));
    delete activeOscillatorsRef.current[note];
  };

  const drawWaveform = () => {
    if (!analyserRef.current || !canvasRef.current) return;
    
    const canvas = canvasRef.current;
    const canvasCtx = canvas.getContext('2d');
    const bufferLength = analyserRef.current.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    const draw = () => {
      animationFrameRef.current = requestAnimationFrame(draw);
      analyserRef.current.getByteTimeDomainData(dataArray);
      
      canvasCtx.fillStyle = '#050505';
      canvasCtx.fillRect(0, 0, canvas.width, canvas.height);
      
      canvasCtx.lineWidth = 2;
      canvasCtx.strokeStyle = '#06b6d4';
      canvasCtx.beginPath();
      
      const sliceWidth = canvas.width * 1.0 / bufferLength;
      let x = 0;
      
      for(let i = 0; i < bufferLength; i++) {
        const v = dataArray[i] / 128.0;
        const y = v * canvas.height/2;
        
        if(i === 0) {
          canvasCtx.moveTo(x, y);
        } else {
          canvasCtx.lineTo(x, y);
        }
        x += sliceWidth;
      }
      
      canvasCtx.lineTo(canvas.width, canvas.height/2);
      canvasCtx.stroke();
    };
    
    draw();
  };

  useEffect(() => {
    return () => {
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
      if (audioCtxRef.current) audioCtxRef.current.close();
    };
  }, []);

  const simulateTTS = (pitch, rate, text) => {
    if (!window.speechSynthesis) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.pitch = pitch;
    utterance.rate = rate;
    window.speechSynthesis.speak(utterance);
  };

  const keys = [
    { note: 'C4', type: 'white' },
    { note: 'C#4', type: 'black' },
    { note: 'D4', type: 'white' },
    { note: 'D#4', type: 'black' },
    { note: 'E4', type: 'white' },
    { note: 'F4', type: 'white' },
    { note: 'F#4', type: 'black' },
    { note: 'G4', type: 'white' },
    { note: 'G#4', type: 'black' },
    { note: 'A4', type: 'white' },
    { note: 'A#4', type: 'black' },
    { note: 'B4', type: 'white' },
    { note: 'C5', type: 'white' }
  ];

  return (
    <div className="flex-1 flex flex-col space-y-6">
      <div className="glass-panel p-6 flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-emerald-400">AUDIO DAW & SYNTHESIS</h2>
          <p className="text-sm text-gray-500">Real-time Web Audio API Engine</p>
        </div>
        {!engineReady ? (
          <button 
            onClick={initAudio}
            className="px-6 py-2 bg-emerald-900/30 border border-emerald-500 text-emerald-400 hover:bg-emerald-900/50 animate-pulse"
          >
            WAKE AUDIO ENGINE
          </button>
        ) : (
          <div className="text-emerald-500 text-sm font-bold flex items-center">
            <div className="w-2 h-2 bg-emerald-500 rounded-full mr-2 animate-ping"></div>
            ENGINE ONLINE
          </div>
        )}
      </div>

      <div className="grid grid-cols-3 gap-6 flex-1">
        {/* Synth Controls */}
        <div className="glass-panel p-6 flex flex-col space-y-6">
          <h3 className="text-lg font-bold text-gray-300">SYNTH PARAMETERS</h3>
          
          <div className="space-y-2">
            <label className="text-xs text-gray-500">WAVEFORM</label>
            <div className="flex space-x-2">
              {['sine', 'square', 'sawtooth', 'triangle'].map(w => (
                <button
                  key={w}
                  onClick={() => setWaveform(w)}
                  className={`flex-1 py-1 text-xs uppercase border ${waveform === w ? 'border-cyan-500 bg-cyan-900/30 text-cyan-400' : 'border-gray-700 text-gray-500 hover:border-gray-500'}`}
                >
                  {w}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex flex-col">
              <label className="text-xs text-gray-500 flex justify-between"><span>ATTACK</span><span>{attack}s</span></label>
              <input type="range" min="0.01" max="2" step="0.01" value={attack} onChange={e => setAttack(e.target.value)} className="accent-cyan-500"/>
            </div>
            <div className="flex flex-col">
              <label className="text-xs text-gray-500 flex justify-between"><span>DECAY</span><span>{decay}s</span></label>
              <input type="range" min="0.01" max="2" step="0.01" value={decay} onChange={e => setDecay(e.target.value)} className="accent-cyan-500"/>
            </div>
            <div className="flex flex-col">
              <label className="text-xs text-gray-500 flex justify-between"><span>SUSTAIN</span><span>{sustain}</span></label>
              <input type="range" min="0" max="1" step="0.01" value={sustain} onChange={e => setSustain(e.target.value)} className="accent-cyan-500"/>
            </div>
            <div className="flex flex-col">
              <label className="text-xs text-gray-500 flex justify-between"><span>RELEASE</span><span>{release}s</span></label>
              <input type="range" min="0.01" max="5" step="0.01" value={release} onChange={e => setRelease(e.target.value)} className="accent-cyan-500"/>
            </div>
          </div>
        </div>

        {/* Visualizer and Keyboard */}
        <div className="col-span-2 flex flex-col space-y-6">
          <div className="glass-panel p-4 flex-1 flex flex-col items-center justify-center relative overflow-hidden">
             <canvas ref={canvasRef} width="600" height="200" className="w-full h-full object-cover opacity-80"></canvas>
             {!engineReady && <div className="absolute inset-0 bg-black/50 flex items-center justify-center text-gray-600">Engine Offline</div>}
          </div>

          <div className="glass-panel p-6 flex justify-center overflow-x-auto">
            <div className="flex relative" style={{ height: '140px' }}>
              {keys.map((k, i) => (
                <div
                  key={i}
                  onMouseDown={() => noteOn(k.note)}
                  onMouseUp={() => noteOff(k.note)}
                  onMouseLeave={() => noteOff(k.note)}
                  className={`${k.type === 'white' ? 'white-key' : 'black-key'} ${!engineReady ? 'opacity-50 pointer-events-none' : ''}`}
                ></div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* TTS Agent Voices */}
      <div className="grid grid-cols-3 gap-6">
        <div className="glass-panel p-4 flex flex-col items-center text-center space-y-2 border-t-2 border-t-purple-500">
          <h4 className="font-bold text-purple-400">Orchestrator</h4>
          <button 
            onClick={() => simulateTTS(0.8, 1.1, "All subsystems nominal. Awaiting next sequence.")}
            className="text-xs px-3 py-1 bg-purple-900/30 border border-purple-500 hover:bg-purple-900/50 transition"
          >
            SIMULATE VOICE
          </button>
        </div>
        <div className="glass-panel p-4 flex flex-col items-center text-center space-y-2 border-t-2 border-t-emerald-500">
          <h4 className="font-bold text-emerald-400">Safeguard</h4>
          <button 
            onClick={() => simulateTTS(1.2, 0.9, "Warning. Variance detected in cognitive substrate.")}
            className="text-xs px-3 py-1 bg-emerald-900/30 border border-emerald-500 hover:bg-emerald-900/50 transition"
          >
            SIMULATE VOICE
          </button>
        </div>
        <div className="glass-panel p-4 flex flex-col items-center text-center space-y-2 border-t-2 border-t-cyan-500">
          <h4 className="font-bold text-cyan-400">Execution</h4>
          <button 
            onClick={() => simulateTTS(0.5, 1.3, "Task completed in zero point zero four seconds.")}
            className="text-xs px-3 py-1 bg-cyan-900/30 border border-cyan-500 hover:bg-cyan-900/50 transition"
          >
            SIMULATE VOICE
          </button>
        </div>
      </div>
    </div>
  );
};

export default AudioDAW;
