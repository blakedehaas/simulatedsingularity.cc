import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Line, PerspectiveCamera, OrthographicCamera } from '@react-three/drei';
import { apiClient } from '../api';
import * as THREE from 'three';

const ForceGraph = ({ swarmData, mode }) => {
  const [positions, setPositions] = useState([]);
  const velocities = useRef([]);
  
  // Initialize positions and velocities when data changes or initially
  useEffect(() => {
    if (!swarmData.agents.length) return;
    
    setPositions(swarmData.agents.map((a, i) => {
      // Start in a random spherical/circular distribution
      const theta = Math.random() * 2 * Math.PI;
      const phi = mode === '2d' ? Math.PI / 2 : Math.random() * Math.PI;
      const r = Math.random() * 5;
      return new THREE.Vector3(
        r * Math.sin(phi) * Math.cos(theta),
        r * Math.sin(phi) * Math.sin(theta),
        mode === '2d' ? 0 : r * Math.cos(phi)
      );
    }));
    
    velocities.current = swarmData.agents.map(() => new THREE.Vector3(0, 0, 0));
  }, [swarmData.agents.length, mode]);

  // Physics loop
  useFrame(() => {
    if (!positions.length || positions.length !== swarmData.agents.length) return;
    
    const newPositions = [...positions];
    const newVelocities = [...velocities.current];
    
    const kRepel = 0.5;
    const kAttract = 0.05;
    const damping = 0.85; // high damping for stability
    const centerAttract = 0.01;
    
    for (let i = 0; i < newPositions.length; i++) {
      const force = new THREE.Vector3(0, 0, 0);
      const posI = newPositions[i];
      
      // Pull to center slightly to avoid flying off
      force.add(posI.clone().multiplyScalar(-centerAttract));
      
      for (let j = 0; j < newPositions.length; j++) {
        if (i === j) continue;
        const posJ = newPositions[j];
        
        const dir = new THREE.Vector3().subVectors(posI, posJ);
        let dist = dir.length();
        if (dist < 0.1) dist = 0.1; // avoid division by zero
        
        // Repulsion
        const repelForce = dir.normalize().multiplyScalar(kRepel / (dist * dist));
        force.add(repelForce);
        
        // Attraction (if connected)
        if (i < j) {
          const weight = swarmData.adjMatrix[i]?.[j] || 0;
          if (weight > 0) {
            const attractForce = new THREE.Vector3().subVectors(posJ, posI).multiplyScalar(weight * kAttract * dist);
            force.add(attractForce);
            
            // Apply equal and opposite force to j
            newVelocities[j].sub(attractForce);
          }
        }
      }
      
      newVelocities[i].add(force);
    }
    
    // Apply velocities and damping
    for (let i = 0; i < newPositions.length; i++) {
      newVelocities[i].multiplyScalar(damping);
      if (mode === '2d') {
        newVelocities[i].z = 0;
      }
      newPositions[i].add(newVelocities[i]);
      if (mode === '2d') {
        newPositions[i].z = 0;
      }
    }
    
    setPositions(newPositions);
    velocities.current = newVelocities;
  });

  const colors = ['#06b6d4', '#a855f7', '#10b981', '#f59e0b', '#ef4444'];

  const lines = useMemo(() => {
    const result = [];
    if (!positions.length || !swarmData.adjMatrix.length) return result;

    for (let i = 0; i < positions.length; i++) {
      for (let j = i + 1; j < positions.length; j++) {
        const weight = swarmData.adjMatrix[i]?.[j] || 0;
        if (weight > 0) {
          result.push({
            start: positions[i],
            end: positions[j],
            weight
          });
        }
      }
    }
    return result;
  }, [positions, swarmData.adjMatrix]);

  return (
    <group>
      {positions.map((pos, i) => {
        const agent = swarmData.agents[i];
        if (!agent) return null;
        
        const isLeader = swarmData.leaders?.includes(agent.id);
        const cluster = swarmData.clusters?.[i] || 0;
        const color = colors[cluster % colors.length];
        
        return (
          <mesh key={`agent-${agent.id}`} position={pos}>
            <sphereGeometry args={[isLeader ? 0.6 : 0.3, 16, 16]} />
            <meshStandardMaterial 
              color={color} 
              emissive={color}
              emissiveIntensity={isLeader ? 2 : 0.8}
            />
          </mesh>
        );
      })}
      
      {lines.map((line, i) => (
        <Line 
          key={`line-${i}`}
          points={[line.start.toArray(), line.end.toArray()]}
          color="#4b5563"
          lineWidth={line.weight * 2}
          opacity={line.weight}
          transparent
        />
      ))}
    </group>
  );
};

const SwarmVisualizer = () => {
  const [swarmData, setSwarmData] = useState({ agents: [], adjMatrix: [], clusters: [], leaders: [] });
  const [mode, setMode] = useState('3d'); // '2d' or '3d'

  useEffect(() => {
    const fetchSwarm = async () => {
      try {
        const res = await apiClient.get('/vr/swarm');
        if (res.data) setSwarmData(res.data);
      } catch (err) {
        // Fallback mock data if API fails
        const mockAgents = Array.from({ length: 20 }).map((_, i) => ({ id: i }));
        const mockMatrix = Array(20).fill(0).map(() => Array(20).fill(0).map(() => Math.random() > 0.85 ? Math.random() : 0));
        const mockClusters = mockAgents.map(a => a.id % 4);
        const mockLeaders = [0, 5, 10, 15];
        
        setSwarmData({ agents: mockAgents, adjMatrix: mockMatrix, clusters: mockClusters, leaders: mockLeaders });
      }
    };
    
    fetchSwarm();
    const interval = setInterval(fetchSwarm, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full h-full relative glass-panel overflow-hidden border border-gray-800">
      <div className="absolute top-4 left-4 z-10 pointer-events-auto flex flex-col items-start space-y-2">
        <div>
          <h3 className="text-cyan-400 font-bold mb-1 text-shadow">SWARM TOPOLOGY</h3>
          <p className="text-xs text-gray-500 font-mono">Multi-Dimensional Projection Visualizer</p>
        </div>
        
        <div className="flex space-x-2">
          <button 
            onClick={() => setMode('2d')}
            className={`px-3 py-1 text-xs font-bold border transition-colors ${
              mode === '2d' 
                ? 'bg-cyan-900/50 border-cyan-500 text-cyan-400' 
                : 'bg-gray-900/50 border-gray-700 text-gray-500 hover:text-gray-300'
            }`}
          >
            [2D SLICE]
          </button>
          <button 
            onClick={() => setMode('3d')}
            className={`px-3 py-1 text-xs font-bold border transition-colors ${
              mode === '3d' 
                ? 'bg-purple-900/50 border-purple-500 text-purple-400' 
                : 'bg-gray-900/50 border-gray-700 text-gray-500 hover:text-gray-300'
            }`}
          >
            [3D SLICE]
          </button>
        </div>
      </div>
      
      <Canvas>
        {mode === '2d' ? (
          <OrthographicCamera makeDefault position={[0, 0, 50]} zoom={30} />
        ) : (
          <PerspectiveCamera makeDefault position={[0, 0, 20]} />
        )}
        <color attach="background" args={['#000000']} />
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} intensity={1} />
        
        <ForceGraph swarmData={swarmData} mode={mode} />
        
        <OrbitControls 
          enablePan={true} 
          enableZoom={true} 
          enableRotate={mode === '3d'} // Disable rotation in 2D mode
        />
      </Canvas>
    </div>
  );
};

export default SwarmVisualizer;
