## Arquivos relevantes

- `frontend/src/components/SimulationCanvas.jsx` — único componente de renderização, consome WebSocket `ws://localhost:8001/ws`, desenha fundo/criaturas/comida via Canvas 2D API
- `backend/main.py` — `simulation_loop()` faz `engine.get_state()` e envia via `manager.broadcast(state)`, 30 FPS
- `backend/simulation/engine.py` — `SimulationEngine.get_state()` monta o payload (`time`, `generation`, `width`, `height`, `creatures`, `foods`, `oases`)
- `backend/simulation/creature.py` — `Creature.to_dict()` já inclui `"vision": self.vision` (array de 9 floats) e `"rotation": self.body.angle`
- `backend/simulation/sensors.py` — `VISION_RADIUS = 200.0`, `NUM_VISION_SECTORS = 9` (constantes só do lado backend, não expostas no payload)

## Conteúdo relevante para a demanda

`SimulationCanvas.jsx` já recebe `creature.x`, `creature.y`, `creature.rotation` e `creature.vision` a cada frame via WebSocket (`data.creatures[i]`), dentro do loop de render (`renderLoop`, linhas 90-121). O sprite da criatura já é desenhado com `ctx.translate(creature.x, creature.y)` + `ctx.rotate(creature.rotation || 0)` — o mesmo par de transformações serve para desenhar os cones de visão alinhados à orientação da criatura.

`VISION_RADIUS` (200.0) não é enviado hoje no payload do WebSocket — só existe como constante Python em `sensors.py`. Sem o raio, o frontend não sabe até onde desenhar os cones (evitar hardcode duplicado, mesmo raciocínio do BIT-08 ao extrair `CREATURE_MASS` como constante única).

O sistema de coordenadas usado por `compute_vision()` (`sensors.py`) mapeia o setor 0 como centrado exatamente na direção "para frente" da criatura (`relative_angle == 0`), com os demais setores distribuídos em ordem anti-horária (ângulo crescente = anti-horário, convenção matemática padrão) a cada `sector_width = 2π / NUM_VISION_SECTORS`. O canvas já usa `ctx.rotate(creature.rotation)` da mesma forma que o sprite, então desenhar o setor `i` centrado em `creature.rotation + i * sector_width` reproduz fielmente a geometria real do sensor.

## O que precisa ser feito

1. **Backend (`engine.py`)**: incluir `"vision_radius": VISION_RADIUS` no dicionário retornado por `get_state()` (import de `VISION_RADIUS` de `simulation.sensors`), ao lado de `width`/`height`. Mudança aditiva no payload do WebSocket — não quebra nenhum consumidor existente.
2. **Frontend (`SimulationCanvas.jsx`)**: dentro do loop que já desenha cada `creature`, desenhar um leque de setores (`ctx.moveTo` + `ctx.arc` formando "fatias de pizza", uma por setor) centrado em `creature.rotation`, raio `data.vision_radius`, `fillStyle = 'rgba(144, 238, 144, 0.5)'` (verde claro, 50% opacidade) — usando `sectorCount = creature.vision.length` em vez do literal `9`, para não duplicar o número mágico do backend.
3. Nenhuma mudança de contrato de dados além do campo aditivo `vision_radius` — sem risco de quebra em outros consumidores (não há outros, o único cliente é este componente).

## Perguntas em aberto

Nenhuma — geometria dos setores e formato visual (verde claro, 50% opacidade, todos os 9 sempre visíveis, sem distinguir ativo/inativo) já confirmados com o developer.
