import React, { useRef, useEffect, useState } from 'react';

const SimulationCanvas = () => {
  const canvasRef = useRef(null);
  const latestWorldState = useRef(null);
  const animationFrameId = useRef(null);
  const [status, setStatus] = useState('Connecting...');

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    
    // Resize canvas to fit container
    const resizeCanvas = () => {
      canvas.width = canvas.parentElement.clientWidth || 800;
      canvas.height = canvas.parentElement.clientHeight || 600;
      // Draw initial dark background
      ctx.fillStyle = '#1e1e1e';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    };
    
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();

    // Setup WebSocket
    const ws = new WebSocket('ws://localhost:8001/ws');

    ws.onopen = () => {
      setStatus('Connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        latestWorldState.current = data;
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

    const renderLoop = () => {
      const data = latestWorldState.current;
      
      if (data) {
        // Clear canvas
        ctx.fillStyle = '#1e1e1e';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        const worldWidth = data.width || 2000;
        const worldHeight = data.height || 2000;
        const scale = Math.min(canvas.width / worldWidth, canvas.height / worldHeight);
        
        if (Number.isFinite(scale) && scale > 0) {
          ctx.save();
          
          const offsetX = (canvas.width - worldWidth * scale) / 2;
          const offsetY = (canvas.height - worldHeight * scale) / 2;
          
          ctx.translate(offsetX, offsetY);
          ctx.scale(scale, scale);

          // Render state (placeholder logic based on possible generic simulation state)
          if (data.creatures) {
            data.creatures.forEach(creature => {
              ctx.fillStyle = creature.color || '#4CAF50';
              ctx.beginPath();
              ctx.arc(creature.x, creature.y, creature.radius || 5, 0, Math.PI * 2);
              ctx.fill();
              
              // Draw direction indicator
              if (creature.rotation !== undefined) {
                const lineLength = (creature.radius || 5) * 2;
                ctx.strokeStyle = '#ffffff';
                ctx.lineWidth = Math.max(1, 2 / scale); // visible line regardless of scale
                ctx.beginPath();
                ctx.moveTo(creature.x, creature.y);
                ctx.lineTo(
                  creature.x + Math.cos(creature.rotation) * lineLength,
                  creature.y + Math.sin(creature.rotation) * lineLength
                );
                ctx.stroke();
              }
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
          
          ctx.restore();
        }
      }
      
      animationFrameId.current = requestAnimationFrame(renderLoop);
    };

    animationFrameId.current = requestAnimationFrame(renderLoop);

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      ws.close();
      if (animationFrameId.current) {
        cancelAnimationFrame(animationFrameId.current);
      }
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
