import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Line, PerspectiveCamera } from '@react-three/drei';
import * as THREE from 'three';

const ForceGraph = ({ agentsState, messages }) => {
  const [positions, setPositions] = useState([]);
  const velocities = useRef([]);

  // Adjacency Matrix derived purely from real messages
  const adjMatrix = useMemo(() => {
    const matrix = Array(agentsState.length).fill(0).map(() => Array(agentsState.length).fill(0));
    if (!messages || messages.length === 0 || agentsState.length === 0) return matrix;

    // Build connections based on sequential messages
    // If agent A speaks right before agent B, they are interacting
    for (let i = 0; i < messages.length - 1; i++) {
        const msgA = messages[i];
        const msgB = messages[i+1];
        
        const senderA = msgA.agent || msgA.sender;
        const senderB = msgB.agent || msgB.sender;

        if (senderA && senderB && senderA !== senderB) {
            const idxA = agentsState.findIndex(a => a.name === senderA);
            const idxB = agentsState.findIndex(a => a.name === senderB);

            if (idxA !== -1 && idxB !== -1) {
                // Increase interaction weight (max out at 1.0)
                matrix[idxA][idxB] = Math.min(1.0, matrix[idxA][idxB] + 0.1);
                matrix[idxB][idxA] = Math.min(1.0, matrix[idxB][idxA] + 0.1);
            }
        }
    }
    return matrix;
  }, [messages, agentsState]);
  
  // Initialize positions and velocities when agents change
  useEffect(() => {
    if (!agentsState || !agentsState.length) return;
    
    setPositions(agentsState.map(() => {
      const theta = Math.random() * 2 * Math.PI;
      const phi = Math.random() * Math.PI;
      const r = Math.random() * 5;
      return new THREE.Vector3(
        r * Math.sin(phi) * Math.cos(theta),
        r * Math.sin(phi) * Math.sin(theta),
        r * Math.cos(phi)
      );
    }));
    
    velocities.current = agentsState.map(() => new THREE.Vector3(0, 0, 0));
  }, [agentsState.length]); // Only re-init if agent count changes

  // Physics loop
  useFrame(() => {
    if (!positions.length || positions.length !== agentsState.length) return;
    
    const newPositions = [...positions];
    const newVelocities = [...velocities.current];
    
    const kRepel = 0.5;
    const kAttract = 0.05;
    const damping = 0.85; 
    const centerAttract = 0.01;
    
    for (let i = 0; i < newPositions.length; i++) {
      const force = new THREE.Vector3(0, 0, 0);
      const posI = newPositions[i];
      
      // Pull to center
      force.add(posI.clone().multiplyScalar(-centerAttract));
      
      for (let j = 0; j < newPositions.length; j++) {
        if (i === j) continue;
        const posJ = newPositions[j];
        
        const dir = new THREE.Vector3().subVectors(posI, posJ);
        let dist = dir.length();
        if (dist < 0.1) dist = 0.1;
        
        // Repulsion
        const repelForce = dir.normalize().multiplyScalar(kRepel / (dist * dist));
        force.add(repelForce);
        
        // Attraction (if connected via messages)
        if (i < j) {
          const weight = adjMatrix[i]?.[j] || 0;
          if (weight > 0) {
            const attractForce = new THREE.Vector3().subVectors(posJ, posI).multiplyScalar(weight * kAttract * dist);
            force.add(attractForce);
            newVelocities[j].sub(attractForce);
          }
        }
      }
      
      newVelocities[i].add(force);
    }
    
    for (let i = 0; i < newPositions.length; i++) {
      newVelocities[i].multiplyScalar(damping);
      newPositions[i].add(newVelocities[i]);
    }
    
    setPositions(newPositions);
    velocities.current = newVelocities;
  });

  const colors = ['#06b6d4', '#a855f7', '#10b981', '#f59e0b', '#ef4444'];

  const lines = useMemo(() => {
    const result = [];
    if (!positions.length || !adjMatrix.length) return result;

    for (let i = 0; i < positions.length; i++) {
      for (let j = i + 1; j < positions.length; j++) {
        const weight = adjMatrix[i]?.[j] || 0;
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
  }, [positions, adjMatrix]);

  // Identify who spoke last to pulse their node
  const activeAgentName = messages.length > 0 ? (messages[messages.length-1].agent || messages[messages.length-1].sender) : null;

  return (
    <group>
      {positions.map((pos, i) => {
        const agent = agentsState[i];
        if (!agent) return null;
        
        const color = colors[i % colors.length];
        const isActive = agent.name === activeAgentName;
        
        return (
          <mesh key={`agent-${agent.name}`} position={pos}>
            <sphereGeometry args={[isActive ? 0.6 : 0.3, 16, 16]} />
            <meshStandardMaterial 
              color={color} 
              emissive={color}
              emissiveIntensity={isActive ? 2.5 : 0.8}
            />
          </mesh>
        );
      })}
      
      {lines.map((line, i) => (
        <Line 
          key={`line-${i}`}
          points={[line.start.toArray(), line.end.toArray()]}
          color="#ffffff"
          lineWidth={1 + (line.weight * 3)}
          opacity={line.weight * 0.8}
          transparent
        />
      ))}
    </group>
  );
};

const ProductionSwarmVisualizer = ({ simId, agentsState = [], messages = [] }) => {
  return (
    <div className="w-full h-full relative overflow-hidden bg-black/50">
      <div className="absolute top-4 left-4 z-10 pointer-events-none flex flex-col items-start space-y-2">
        <div>
          <h3 className="text-purple-400 font-bold mb-1 text-shadow">PRODUCTION SWARM TOPOLOGY</h3>
          {simId ? (
              <p className="text-xs text-gray-400 font-mono">Tracking {agentsState.length} active agent nodes.</p>
          ) : (
              <p className="text-xs text-gray-600 font-mono">No active simulation.</p>
          )}
        </div>
        
        {agentsState.length > 0 && (
            <div className="mt-2 text-xs flex flex-col gap-1">
                {agentsState.map((a, i) => {
                    const colors = ['text-cyan-400', 'text-purple-400', 'text-emerald-400', 'text-amber-400', 'text-red-400'];
                    return <div key={i} className={`${colors[i % colors.length]} font-bold`}>● {a.name}</div>
                })}
            </div>
        )}
      </div>
      
      <Canvas>
        <PerspectiveCamera makeDefault position={[0, 0, 15]} />
        <color attach="background" args={['#000000']} />
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} intensity={1} />
        
        {agentsState.length > 0 && (
            <ForceGraph agentsState={agentsState} messages={messages} />
        )}
        
        <OrbitControls enablePan={true} enableZoom={true} enableRotate={true} />
      </Canvas>
    </div>
  );
};

export default ProductionSwarmVisualizer;
