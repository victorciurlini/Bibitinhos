# Research — api-websocket (BIT-28: Modo headless)

> Relatório do sub-agente Explore sobre o acoplamento servidor ↔ simulação em `backend/main.py`.

## Arquivos relevantes
- `backend/main.py:43–47` — instância global: `engine = SimulationEngine()`
- `backend/main.py:81–100` — `simulation_loop()` (async, 30 FPS, substeps por acumulador de speed, broadcast)
- `backend/main.py:102–108` — `startup_event()`: cria 10 criaturas e `asyncio.create_task(simulation_loop())`
- `backend/simulation/engine.py:45–85` — `SimulationEngine.__init__` (sem dependência de FastAPI)
- `backend/simulation/physics.py:36–42` — `PhysicsEngine` (pymunk puro)

## Conteúdo relevante

```python
async def simulation_loop():
    speed_accumulator = 0.0
    while True:
        try:
            if not engine.paused:
                speed_accumulator += engine.speed
                while speed_accumulator >= 1.0:
                    engine.step(1 / 30.0)
                    speed_accumulator -= 1.0
            state = engine.get_state()
            state["type"] = "state_update"
            await manager.broadcast(state)
        except Exception:
            import traceback
            traceback.print_exc()
        await asyncio.sleep(1 / 30.0)  # 30 FPS
```

**O engine é 100% independente do FastAPI/WebSocket** — `step()` e `get_state()` são puros. Os bloqueadores para headless são apenas:
1. `simulation_loop()` é async e vive em `main.py` junto com o broadcast
2. A população inicial (10 criaturas) é criada dentro do `@app.on_event("startup")`
3. Loop roda forever, sem condição de parada nem saída de resultados

**Dependências do modo headless:** pymunk, neat-python, numpy — sem FastAPI/uvicorn/Node.

## O que precisa ser feito
1. Extrair o bootstrap da população (`for _ in range(10): engine.add_creature(Creature(engine))`) para função reutilizável, chamada tanto pelo `startup_event` quanto pelo runner headless
2. Loop headless **síncrono e sem sleep** (máxima velocidade): `for _ in range(n_ticks): engine.step(1/30.0)` — o padrão async/30 FPS só faz sentido com clientes conectados
3. CLI com parada condicional (N ticks) e escrita de snapshots JSON
4. `main.py` permanece com seu loop async próprio; nenhuma mudança de protocolo WebSocket

## Perguntas em aberto
1. Propósito principal: experimentos longos/benchmark vs CI — define formato de saída
2. Persistência: snapshots periódicos (JSON/JSONL) vs estado completo
3. Reprodutibilidade: seed do `random` (usado por rtneat_wrapper nas mutações) — expor `--seed`?
