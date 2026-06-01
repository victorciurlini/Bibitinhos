import React, { useRef, useEffect, useState } from 'react';

const SimulationCanvas = () => {
  const canvasRef = useRef(null);
  const [status, setStatus] = useState('Connecting...');

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    
    // Resize canvas to fit container
    const resizeCanvas = () => {
      canvas.width = canvas.parentElement.clientWidth;
      canvas.height = canvas.parentElement.clientHeight;
      // Draw initial dark background
      ctx.fillStyle = '#1e1e1e';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    };
    
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();

    // Setup WebSocket
    const ws = new WebSocket('ws://localhost:8000/ws');

    ws.onopen = () => {
      setStatus('Connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Clear canvas
        ctx.fillStyle = '#1e1e1e';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        // Render state (placeholder logic based on possible generic simulation state)
        if (data.creatures) {
          data.creatures.forEach(creature => {
            ctx.fillStyle = creature.color || '#4CAF50';
            ctx.beginPath();
            ctx.arc(creature.x, creature.y, creature.radius || 5, 0, Math.PI * 2);
            ctx.fill();
          });
        }
        if (data.foods) {
          data.foods.forEach(food => {
            ctx.fillStyle = food.color || '#ffcc00';
            ctx.beginPath();
            ctx.arc(food.x, food.y, food.radius || 3, 0, Math.PI * 2);
            ctx.fill();
          });
        }
      } catch (e) {
        console.error('Error parsing WebSocket message:', e);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setStatus('Error connecting to simulation');
    };

    ws.onclose = () => {
      setStatus('Disconnected');
    };

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      ws.close();
    };
  }, []);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', flex: 1 }}>
      <div style={{
        position: 'absolute',
        top: 10,
        left: 10,
        padding: '5px 10px',
        backgroundColor: 'rgba(0,0,0,0.6)',
        borderRadius: '5px',
        color: '#fff',
        zIndex: 10,
        fontFamily: 'monospace'
      }}>
        Status: {status}
      </div>
      <canvas 
        ref={canvasRef} 
        style={{ display: 'block', width: '100%', height: '100%', backgroundColor: '#1e1e1e' }}
      />
    </div>
  );
};

export default SimulationCanvas;
