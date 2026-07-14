import React, { useRef, useEffect, useState } from 'react';

const SimulationCanvas = () => {
  const canvasRef = useRef(null);
  const latestWorldState = useRef(null);
  const animationFrameId = useRef(null);
  const images = useRef({});
  const [status, setStatus] = useState('Connecting...');

  useEffect(() => {
    const loadImg = (src) => {
      const img = new Image();
      img.src = src;
      return img;
    };
    images.current.bibity = loadImg('/sprites/bibity.png');
    images.current.egg = loadImg('/sprites/egg.png');
    images.current.food = loadImg('/sprites/food.png');
    images.current.fundo = loadImg('/sprites/fundo.png');

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

          // Renderizar fundo original
          if (images.current.fundo && images.current.fundo.complete) {
            ctx.drawImage(images.current.fundo, 0, 0, worldWidth, worldHeight);
          }

          // Render state
          if (data.creatures) {
            const visionRadius = data.vision_radius || 80;
            const visionFovRadians = ((data.vision_fov_degrees || 120) * Math.PI) / 180;
            data.creatures.forEach(creature => {
              // Cone de visao frontal (9 setores translucidos), desenhado atras do sprite.
              // Setor do meio fica centrado exatamente na direcao "para frente" (mesma
              // geometria de compute_vision em sensors.py: nada atras da criatura acende).
              if (creature.vision && creature.vision.length > 0) {
                const sectorCount = creature.vision.length;
                const sectorWidth = visionFovRadians / sectorCount;
                const rotation = creature.rotation || 0;
                const fovStart = rotation - visionFovRadians / 2;

                ctx.save();
                ctx.translate(creature.x, creature.y);
                ctx.fillStyle = 'rgba(144, 238, 144, 0.5)'; // verde claro, 50% opacidade
                for (let i = 0; i < sectorCount; i++) {
                  const startAngle = fovStart + i * sectorWidth;
                  const endAngle = startAngle + sectorWidth;
                  ctx.beginPath();
                  ctx.moveTo(0, 0);
                  ctx.arc(0, 0, visionRadius, startAngle, endAngle);
                  ctx.closePath();
                  ctx.fill();
                }
                ctx.restore();
              }

              if (images.current.bibity && images.current.bibity.complete && images.current.egg && images.current.egg.complete) {
                const img = creature.life_stage === 'EGG' ? images.current.egg : images.current.bibity;
                ctx.save();
                ctx.translate(creature.x, creature.y);
                ctx.rotate(creature.rotation || 0);
                const s = (creature.radius || 10) * 2;
                ctx.drawImage(img, -s/2, -s/2, s, s);
                ctx.restore();
              } else {
                ctx.fillStyle = creature.color || '#4CAF50';
                ctx.beginPath();
                ctx.arc(creature.x, creature.y, creature.radius || 5, 0, Math.PI * 2);
                ctx.fill();
                
                // Draw direction indicator
                if (creature.rotation !== undefined) {
                  const lineLength = (creature.radius || 5) * 2;
                  ctx.strokeStyle = '#ffffff';
                  ctx.lineWidth = Math.max(1, 2 / scale);
                  ctx.beginPath();
                  ctx.moveTo(creature.x, creature.y);
                  ctx.lineTo(
                    creature.x + Math.cos(creature.rotation) * lineLength,
                    creature.y + Math.sin(creature.rotation) * lineLength
                  );
                  ctx.stroke();
                }
              }
            });
          }
          if (data.foods) {
            data.foods.forEach(food => {
              if (images.current.food && images.current.food.complete) {
                const s = (food.radius || 5) * 2;
                ctx.drawImage(images.current.food, food.x - s/2, food.y - s/2, s, s);
              } else {
                ctx.fillStyle = food.color || '#ffcc00';
                ctx.beginPath();
                ctx.arc(food.x, food.y, food.radius || 3, 0, Math.PI * 2);
                ctx.fill();
              }
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
