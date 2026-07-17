import { useRef, useEffect, useState } from 'react';
import ControlMenu from './ControlMenu';

const OFFSCREEN_TINT_SIZE = 64;
const TINT_ALPHA = 0.55;
const DRAG_THRESHOLD_PX = 5; // deslocamento de tela que separa clique de arrasto
const HIT_SLOP_WORLD = 6; // folga do hit-test, em unidades de mundo
const INSPECT_INTERVAL_MS = 150; // taxa de atualizacao do painel/controles (sem re-render a 30 FPS)
const METRICS_SERIES_MAX = 600; // espelha METRICS_HISTORY_MAX do backend (~10 min a 1 amostra/s)

const SimulationCanvas = () => {
  const canvasRef = useRef(null);
  const latestWorldState = useRef(null);
  const animationFrameId = useRef(null);
  const images = useRef({});
  const tintCanvasRef = useRef(null);
  const [status, setStatus] = useState('Connecting...');

  // Estado quente de interacao fica em refs (nao dispara re-render a 30 FPS).
  const wsRef = useRef(null);
  const viewTransformRef = useRef({ scale: 1, offsetX: 0, offsetY: 0 });
  const selectedIdRef = useRef(null);
  const dragRef = useRef(null); // null ou { creatureId, startX, startY, moved }

  // BIT-27: ultima mensagem creature_inspection recebida (unicast, uma por selecao).
  // Ref no hot-path do WS; o espelho reativo so expoe o genoma da selecao corrente.
  const inspectedGenomeRef = useRef(null);

  // Espelho reativo (~150 ms) do que o painel/controles precisam mostrar.
  const [inspectedCreature, setInspectedCreature] = useState(null);
  const [inspectedGenome, setInspectedGenome] = useState(null);
  const [paused, setPaused] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [params, setParams] = useState(null);

  // BIT-26: agregados correntes (do state_update) + serie temporal local (1 amostra/s simulado),
  // semeada via GET /metrics/history para sobreviver a reloads/reconexoes do frontend.
  const [metrics, setMetrics] = useState(null);
  const metricsSeriesRef = useRef([]);
  const [metricsSeries, setMetricsSeries] = useState([]);

  // Envia um comando pelo WS se ele estiver aberto.
  const sendCommand = (obj) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(obj));
    }
  };

  const drawTintedSprite = (ctx, img, size, color) => {
    if (!tintCanvasRef.current) {
      const c = document.createElement('canvas');
      c.width = OFFSCREEN_TINT_SIZE;
      c.height = OFFSCREEN_TINT_SIZE;
      tintCanvasRef.current = c;
    }
    const off = tintCanvasRef.current;
    const octx = off.getContext('2d');
    octx.clearRect(0, 0, OFFSCREEN_TINT_SIZE, OFFSCREEN_TINT_SIZE);
    octx.drawImage(img, 0, 0, OFFSCREEN_TINT_SIZE, OFFSCREEN_TINT_SIZE);
    octx.globalCompositeOperation = 'source-atop';
    octx.globalAlpha = TINT_ALPHA;
    octx.fillStyle = color;
    octx.fillRect(0, 0, OFFSCREEN_TINT_SIZE, OFFSCREEN_TINT_SIZE);
    octx.globalAlpha = 1;
    octx.globalCompositeOperation = 'source-over';
    ctx.drawImage(off, -size / 2, -size / 2, size, size);
  };

  useEffect(() => {
    const loadImg = (src) => {
      const img = new Image();
      img.src = src;
      return img;
    };
    images.current.bibity = loadImg('/sprites/bibity.png');
    images.current.egg = loadImg('/sprites/egg.png');
    images.current.food = loadImg('/sprites/food.png');

    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    
    // Resize canvas to fit container
    const resizeCanvas = () => {
      canvas.width = canvas.parentElement.clientWidth || 800;
      canvas.height = canvas.parentElement.clientHeight || 600;
      // Draw initial dark background
      ctx.fillStyle = '#0a1e2e';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    };
    
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();

    // BIT-26: semeia a serie de metricas com o historico do backend (bootstrap do painel).
    // Falha de rede e silenciosa de proposito: a serie passa a crescer so com o WS mesmo.
    fetch('http://localhost:8001/metrics/history')
      .then((res) => res.json())
      .then((data) => {
        if (data && Array.isArray(data.history)) {
          metricsSeriesRef.current = data.history.slice(-METRICS_SERIES_MAX);
          setMetricsSeries([...metricsSeriesRef.current]);
        }
      })
      .catch(() => {});

    // Setup WebSocket
    const ws = new WebSocket('ws://localhost:8001/ws');
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus('Connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // BIT-27: roteamento por tipo — creature_inspection (unicast) nao pode
        // poluir latestWorldState (o renderLoop assume o formato do state_update).
        if (data.type === 'creature_inspection') {
          inspectedGenomeRef.current = data;
        } else if (data.type === 'state_update') {
          latestWorldState.current = data;
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

    const renderLoop = () => {
      const data = latestWorldState.current;
      
      if (data) {
        // Clear canvas
        ctx.fillStyle = '#0a1e2e';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        const worldWidth = data.width || 2000;
        const worldHeight = data.height || 2000;
        const scale = Math.min(canvas.width / worldWidth, canvas.height / worldHeight);
        
        if (Number.isFinite(scale) && scale > 0) {
          ctx.save();

          const offsetX = (canvas.width - worldWidth * scale) / 2;
          const offsetY = (canvas.height - worldHeight * scale) / 2;

          // Guarda a transform corrente para o hit-test / toWorld dos handlers de mouse.
          viewTransformRef.current = { scale, offsetX, offsetY };

          ctx.translate(offsetX, offsetY);
          ctx.scale(scale, scale);

          // Fundo aquatico do mundo: gradiente vertical (mais claro no topo, mais fundo embaixo)
          const worldGradient = ctx.createLinearGradient(0, 0, 0, worldHeight);
          worldGradient.addColorStop(0, '#1a5079');
          worldGradient.addColorStop(1, '#0d2c44');
          ctx.fillStyle = worldGradient;
          ctx.fillRect(0, 0, worldWidth, worldHeight);

          // Oasis: zona de fertilidade, atras de tudo que e vivo/comestivel.
          // Opacidade cai junto com o TTL (fade-out natural antes de expirar).
          if (data.oases) {
            data.oases.forEach(oasis => {
              const frac = oasis.ttl_fraction ?? 1;
              const grad = ctx.createRadialGradient(oasis.x, oasis.y, 0, oasis.x, oasis.y, oasis.radius);
              grad.addColorStop(0, `rgba(80, 200, 120, ${0.10 + 0.15 * frac})`);
              grad.addColorStop(1, 'rgba(80, 200, 120, 0)');
              ctx.fillStyle = grad;
              ctx.beginPath();
              ctx.arc(oasis.x, oasis.y, oasis.radius, 0, Math.PI * 2);
              ctx.fill();
            });
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
                drawTintedSprite(ctx, img, s, creature.color || '#4CAF50');
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

            // Anel de destaque da criatura selecionada. Se o id sumiu do state
            // (a criatura morreu), limpa a selecao para o painel/anel sumirem.
            if (selectedIdRef.current != null) {
              const sel = data.creatures.find(c => c.id === selectedIdRef.current);
              if (sel) {
                ctx.strokeStyle = '#ffffff';
                ctx.lineWidth = 2 / scale;
                ctx.beginPath();
                ctx.arc(sel.x, sel.y, (sel.radius || 10) + 6, 0, Math.PI * 2);
                ctx.stroke();
              } else {
                selectedIdRef.current = null;
              }
            }
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

    // Converte coordenadas de tela (evento) para coordenadas de mundo, usando a
    // transform corrente calculada no renderLoop.
    const toWorld = (e) => {
      const rect = canvas.getBoundingClientRect();
      const { scale, offsetX, offsetY } = viewTransformRef.current;
      return {
        x: (e.clientX - rect.left - offsetX) / scale,
        y: (e.clientY - rect.top - offsetY) / scale,
      };
    };

    // Retorna a criatura mais proxima do ponto de mundo dentro do raio + folga, ou null.
    const hitTest = (worldX, worldY) => {
      const data = latestWorldState.current;
      if (!data || !data.creatures) return null;
      let best = null;
      let bestDist = Infinity;
      for (const c of data.creatures) {
        const dx = c.x - worldX;
        const dy = c.y - worldY;
        const dist = Math.hypot(dx, dy);
        if (dist <= (c.radius || 10) + HIT_SLOP_WORLD && dist < bestDist) {
          best = c;
          bestDist = dist;
        }
      }
      return best;
    };

    const handleMouseDown = (e) => {
      const w = toWorld(e);
      const hit = hitTest(w.x, w.y);
      dragRef.current = {
        creatureId: hit ? hit.id : null,
        startX: e.clientX,
        startY: e.clientY,
        moved: false,
      };
    };

    const handleMouseMove = (e) => {
      const drag = dragRef.current;
      if (!drag) return;
      const screenDist = Math.hypot(e.clientX - drag.startX, e.clientY - drag.startY);
      if (drag.creatureId == null) return; // clique no vazio nunca vira arrasto
      const w = toWorld(e);
      if (!drag.moved && screenDist >= DRAG_THRESHOLD_PX) {
        drag.moved = true;
        canvas.style.cursor = 'grabbing';
        sendCommand({ action: 'drag', phase: 'start', creature_id: drag.creatureId });
      }
      if (drag.moved) {
        sendCommand({ action: 'drag', phase: 'move', creature_id: drag.creatureId, x: w.x, y: w.y });
      }
    };

    const finishDrag = (e) => {
      const drag = dragRef.current;
      if (!drag) return;
      if (drag.moved) {
        sendCommand({ action: 'drag', phase: 'end', creature_id: drag.creatureId });
      } else {
        // Sem arrasto: foi um clique. Seleciona o alvo (ou deseleciona no vazio).
        const screenDist = Math.hypot(e.clientX - drag.startX, e.clientY - drag.startY);
        if (screenDist < DRAG_THRESHOLD_PX) {
          const w = toWorld(e);
          const hit = hitTest(w.x, w.y);
          selectedIdRef.current = hit ? hit.id : null;
          // BIT-27: nova selecao pede o genoma UMA vez (ele e imutavel em vida);
          // deselecao (ou troca) descarta o genoma anterior.
          inspectedGenomeRef.current = null;
          if (hit) {
            sendCommand({ action: 'inspect_creature', creature_id: hit.id });
          }
        }
      }
      dragRef.current = null;
      canvas.style.cursor = 'default';
    };

    const handleMouseUp = (e) => finishDrag(e);
    const handleMouseLeave = (e) => finishDrag(e);

    canvas.addEventListener('mousedown', handleMouseDown);
    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('mouseup', handleMouseUp);
    canvas.addEventListener('mouseleave', handleMouseLeave);

    // Espelha a ~150 ms o que os overlays precisam (evita re-render a 30 FPS).
    const inspectInterval = setInterval(() => {
      const data = latestWorldState.current;
      if (!data) return;
      if (typeof data.paused === 'boolean') setPaused(data.paused);
      if (typeof data.speed === 'number') setSpeed(data.speed);
      if (data.params && typeof data.params === 'object') setParams(data.params);
      if (data.metrics && typeof data.metrics === 'object') {
        const m = data.metrics;
        setMetrics(m);
        // Apenda 1 amostra por segundo simulado (mesmo criterio de amostragem do backend).
        const series = metricsSeriesRef.current;
        const last = series.length > 0 ? series[series.length - 1] : null;
        if (typeof m.time === 'number' && (!last || Math.floor(m.time) > Math.floor(last.time))) {
          series.push(m);
          if (series.length > METRICS_SERIES_MAX) series.shift();
          setMetricsSeries([...series]);
        }
      }
      const id = selectedIdRef.current;
      const sel = id != null && data.creatures ? data.creatures.find(c => c.id === id) : null;
      setInspectedCreature(sel || null);
      // BIT-27: expoe o genoma so se a resposta unicast corresponde a selecao corrente
      // (criatura morta/deselecionada => null; respostas atrasadas de outra selecao tambem).
      const insp = inspectedGenomeRef.current;
      setInspectedGenome(insp && insp.creature_id === selectedIdRef.current ? insp.genome : null);
    }, INSPECT_INTERVAL_MS);

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      canvas.removeEventListener('mousedown', handleMouseDown);
      canvas.removeEventListener('mousemove', handleMouseMove);
      canvas.removeEventListener('mouseup', handleMouseUp);
      canvas.removeEventListener('mouseleave', handleMouseLeave);
      clearInterval(inspectInterval);
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
        top: 12,
        right: 12,
        padding: '6px 11px',
        display: 'flex',
        alignItems: 'center',
        gap: 7,
        backgroundColor: 'rgba(9, 26, 30, 0.74)',
        backdropFilter: 'blur(10px)',
        WebkitBackdropFilter: 'blur(10px)',
        border: '1px solid rgba(70, 229, 176, 0.16)',
        borderRadius: 10,
        boxShadow: '0 6px 24px rgba(0, 0, 0, 0.45)',
        color: '#e6f4ef',
        zIndex: 10,
        fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif",
        fontSize: '12px'
      }}>
        <span style={{
          width: 7,
          height: 7,
          borderRadius: '50%',
          backgroundColor: '#46e5b0',
          boxShadow: '0 0 6px rgba(70, 229, 176, 0.9)'
        }} />
        {status}
      </div>
      <canvas
        ref={canvasRef}
        style={{ display: 'block', width: '100%', height: '100%', backgroundColor: '#0a1e2e' }}
      />
      <ControlMenu
        paused={paused}
        speed={speed}
        creature={inspectedCreature}
        genome={inspectedGenome}
        params={params}
        metrics={metrics}
        metricsSeries={metricsSeries}
        onCommand={sendCommand}
      />
    </div>
  );
};

export default SimulationCanvas;
