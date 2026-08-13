import React, { useState } from 'react';
import { apiClient } from '../api';

const Monetization = () => {
  const [loadingId, setLoadingId] = useState(null);

  const tiers = [
    {
      id: 'tier-1',
      title: 'INITIATE SPARK',
      description: 'One-time injection of cognitive tokens for basic synthesis operations.',
      price: '$4.99',
      features: ['50,000 Tokens', 'Standard Priority', 'Basic Synthesis Models'],
      color: 'cyan'
    },
    {
      id: 'tier-2',
      title: 'SINGULARITY SYNC',
      description: 'Unrestricted monthly access to the neural network substrate.',
      price: '$29.99/mo',
      features: ['Unlimited Tokens', 'High Priority Queue', 'Advanced Video/Audio Models'],
      color: 'purple',
      popular: true
    },
    {
      id: 'tier-3',
      title: 'ARCHITECT PROTOCOL',
      description: 'Direct API access and full administrative override capabilities.',
      price: '$99.99/mo',
      features: ['Full Substrate Access', 'Dedicated VRAM', 'Commercial License'],
      color: 'emerald'
    }
  ];

  const handlePurchase = async (tierId) => {
    setLoadingId(tierId);
    try {
      // Mock API call to create checkout session
      await new Promise(r => setTimeout(r, 1500)); 
      // In real implementation: window.location.href = res.data.url;
      console.log(`Redirecting to checkout for ${tierId}`);
    } catch (err) {
      console.error('Purchase failed', err);
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8">
      <div className="text-center mb-12">
        <h1 className="text-3xl font-bold tracking-widest text-white mb-4">NEURAL COMMERCE GATEWAY</h1>
        <p className="text-gray-400 font-mono max-w-2xl mx-auto">Upgrade your substrate connection to allocate more computational resources to the simulation.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 w-full max-w-6xl">
        {tiers.map((tier) => {
          const isColorCyan = tier.color === 'cyan';
          const isColorPurple = tier.color === 'purple';
          
          const borderColor = isColorCyan ? 'border-cyan-500' : isColorPurple ? 'border-purple-500' : 'border-emerald-500';
          const bgColor = isColorCyan ? 'bg-cyan-900/10' : isColorPurple ? 'bg-purple-900/10' : 'bg-emerald-900/10';
          const textColor = isColorCyan ? 'text-cyan-400' : isColorPurple ? 'text-purple-400' : 'text-emerald-400';
          const buttonBg = isColorCyan ? 'bg-cyan-900/30' : isColorPurple ? 'bg-purple-900/30' : 'bg-emerald-900/30';
          const hoverBg = isColorCyan ? 'hover:bg-cyan-900/50' : isColorPurple ? 'hover:bg-purple-900/50' : 'hover:bg-emerald-900/50';
          
          return (
            <div 
              key={tier.id} 
              className={`glass-panel p-8 flex flex-col relative transition-transform hover:-translate-y-2 border-t-4 ${borderColor} ${bgColor} ${tier.popular ? 'glow-purple' : ''}`}
            >
              {tier.popular && (
                <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-purple-500 text-white text-xs font-bold px-3 py-1 tracking-widest">
                  RECOMMENDED
                </div>
              )}
              
              <h2 className={`text-xl font-bold mb-2 ${textColor}`}>{tier.title}</h2>
              <div className="text-3xl font-bold text-white mb-4">{tier.price}</div>
              <p className="text-gray-400 text-sm h-16 mb-6">{tier.description}</p>
              
              <div className="flex-1 space-y-3 mb-8 border-t border-gray-800 pt-6">
                {tier.features.map((feature, i) => (
                  <div key={i} className="flex items-center text-sm text-gray-300">
                    <span className={`mr-2 ${textColor}`}>›</span> {feature}
                  </div>
                ))}
              </div>
              
              <button
                onClick={() => handlePurchase(tier.id)}
                disabled={loadingId !== null}
                className={`w-full py-3 font-bold border transition-colors ${buttonBg} ${borderColor} ${textColor} ${hoverBg} ${loadingId === tier.id ? 'animate-pulse' : ''}`}
              >
                {loadingId === tier.id ? 'INITIALIZING...' : tier.id.includes('1') ? 'ACQUIRE' : 'SUBSCRIBE'}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Monetization;
