import React, { useState, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { VRButton, XR, Controllers, Hands } from '@react-three/xr';
import { PointerLockControls, Text, Sky } from '@react-three/drei';

const VoxelBlock = ({ position, onIntersect }) => {
  const [exists, setExists] = useState(true);
  const [hovered, setHovered] = useState(false);

  if (!exists) return null;

  return (
    <mesh 
      position={position}
      onClick={() => setExists(false)}
      onPointerOver={() => setHovered(true)}
      onPointerOut={() => setHovered(false)}
    >
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial 
        color={hovered ? "#06b6d4" : "#1a1a2e"} 
        wireframe={!hovered}
        emissive={hovered ? "#06b6d4" : "#000000"}
        emissiveIntensity={hovered ? 0.5 : 0}
      />
    </mesh>
  );
};

const Grid = () => {
  const blocks = [];
  const size = 15;
  for (let x = -size/2; x < size/2; x++) {
    for (let z = -size/2; z < size/2; z++) {
      blocks.push(
        <VoxelBlock key={`${x}-${z}`} position={[x, -1, z]} />
      );
    }
  }
  return <group>{blocks}</group>;
};

const AgentEntity = () => {
  const meshRef = useRef();
  
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.x += 0.01;
      meshRef.current.rotation.y += 0.01;
      meshRef.current.position.y = Math.sin(state.clock.elapsedTime) * 0.5 + 2;
    }
  });

  return (
    <group position={[0, 2, -5]}>
      <mesh ref={meshRef}>
        <octahedronGeometry args={[1, 0]} />
        <meshStandardMaterial color="#a855f7" wireframe={true} emissive="#a855f7" emissiveIntensity={0.5} />
      </mesh>
      <Text
        position={[0, 2, 0]}
        color="#a855f7"
        fontSize={0.5}
        anchorX="center"
        anchorY="middle"
      >
        I AM COMPUTING...
      </Text>
    </group>
  );
};

const Sandbox = () => {
  return (
    <div className="flex-1 relative w-full h-full overflow-hidden bg-black rounded-lg border border-gray-800">
      <div className="absolute top-4 left-4 z-10 glass-panel p-4 max-w-sm pointer-events-none">
        <h2 className="text-xl font-bold text-cyan-400 mb-2">WEBXR SANDBOX</h2>
        <p className="text-xs text-gray-400 font-mono">
          Click the canvas to enable PointerLock controls (Desktop). Use WASD to move, mouse to look around. Click voxels to destroy them.
        </p>
      </div>
      
      <div className="absolute bottom-4 right-4 z-10">
        <VRButton className="px-6 py-2 bg-purple-900/50 border border-purple-500 text-purple-400 font-bold hover:bg-purple-900 transition-colors" />
      </div>

      <Canvas camera={{ position: [0, 1.5, 0], fov: 75 }}>
        <XR>
          <color attach="background" args={['#050505']} />
          <ambientLight intensity={0.2} />
          <pointLight position={[0, 5, 0]} intensity={1} color="#06b6d4" />
          <pointLight position={[-5, 5, -5]} intensity={0.5} color="#a855f7" />
          
          <Controllers />
          <Hands />
          
          <Grid />
          <AgentEntity />
          
          <PointerLockControls />
        </XR>
      </Canvas>
    </div>
  );
};

export default Sandbox;
