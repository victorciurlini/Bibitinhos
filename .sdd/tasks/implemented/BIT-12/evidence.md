# Evidência — BIT-12: Cones de Visão no Canvas

**Data de conclusão:** 2026-07-14

## Demanda atendida

O sensor de visão (9 cones de `compute_vision()`) agora é visível no canvas: cada criatura exibe um leque de setores verde claro translúcido, girando junto com sua rotação, alimentado por um novo campo aditivo `vision_radius` no payload do WebSocket.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/engine.py` | modificado | Import de `VISION_RADIUS` de `simulation.sensors` (junto de `compute_vision`); `get_state()` passa a incluir `"vision_radius": VISION_RADIUS` no dicionário retornado, ao lado de `width`/`height`. |
| `frontend/src/components/SimulationCanvas.jsx` | modificado | Dentro do `forEach` de `data.creatures`, antes do bloco que desenha o sprite, adicionado bloco que desenha um leque de `creature.vision.length` setores (fatias via `moveTo` + `arc`), raio `data.vision_radius` (fallback 200), cor `rgba(144, 238, 144, 0.5)`, centrados em `creature.rotation + i * sectorWidth`. Usa `ctx.translate` sem `ctx.rotate` explícito (ângulo já embutido no cálculo de cada setor), reproduzindo a mesma origem de coordenadas do sprite. |

## Resultados dos gates de qualidade

- `import main`: OK — `OK - app importa`
- `pytest tests/`: 57 passed, 6 warnings (warnings pré-existentes de `neat.config`, não relacionados a esta mudança)
- `npm run test`: 1 passed (`App.test.jsx`)
- `npm run build`: OK — build de produção gerado sem erros (`dist/assets/index-DUTAFgcF.js`, 145.51 kB)

## Validação funcional (backend)

Subida via `venv\Scripts\python.exe -m uvicorn main:app --port 8099` (porta 8001 já ocupada por outra sessão concorrente rodando em paralelo neste repositório — comportamento esperado, documentado no aviso de concorrência). Log confirmou `Application startup complete.` e `Uvicorn running on http://127.0.0.1:8099` sem nenhum traceback. Processo derrubado logo em seguida.

## Como validar

A confirmação visual final (o leque verde claro aparecendo corretamente ao redor de cada criatura, girando com a rotação) precisa ser feita pelo developer no browser, pois esta sessão não tem acesso a essa ferramenta:

1. Rodar `manager.py` (ou subir backend + `npm run dev` no frontend manualmente).
2. Abrir `http://localhost:5173` no browser.
3. Observar cada criatura no canvas: deve haver um leque de 9 setores verde claro (50% opacidade) cobrindo 360° ao redor dela, sempre visível.
4. Verificar que o leque gira junto com a criatura (setor frontal sempre alinhado à frente do sprite) conforme ela se movimenta.
5. Confirmar que não houve regressão visual no fundo, sprites e comida já existentes.
