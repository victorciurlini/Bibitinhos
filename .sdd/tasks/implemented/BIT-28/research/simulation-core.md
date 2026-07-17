# Research — simulation-core (BIT-28: Modo headless)

> Relatório do sub-agente Explore sobre `backend/simulation/` + `backend/main.py` para a demanda de modo headless.

## Arquivos relevantes
- `backend/main.py` (linhas 1-109)
- `backend/simulation/engine.py` (linhas 139-333)
- `backend/simulation/creature.py` (linhas 111-265)
- `backend/simulation/params.py` (linhas 134-154)
- Testes: `backend/tests/test_*.py` (todos executam engine sem WebSocket)

## Conteúdo relevante

**Acoplamento atual com FastAPI/WebSocket (main.py:49-109):**
```python
app = FastAPI()
manager = ConnectionManager()          # gerenciador WebSocket global (linhas 17-36)
engine = SimulationEngine()            # engine global (linha 47)

# WebSocket endpoint (linhas 49-79): recebe msgs do cliente
# (set_time_control, drag, set_param); broadcast é feito no simulation_loop

async def simulation_loop():           # linhas 81-100
    speed_accumulator = 0.0
    while True:
        if not engine.paused:
            speed_accumulator += engine.speed
            while speed_accumulator >= 1.0:
                engine.step(1/30.0)    # ← INDEPENDENTE de WebSocket!
                speed_accumulator -= 1.0
        state = engine.get_state()
        await manager.broadcast(state)
        await asyncio.sleep(1/30.0)    # 30 FPS

@app.on_event("startup")
async def startup_event():
    for _ in range(10):
        engine.add_creature(Creature(engine))
    app.state.sim_task = asyncio.create_task(simulation_loop())
```

**Observação crítica: o engine JÁ é totalmente standalone.**
- `engine.step(dt)` é puro, sem I/O, sem WebSocket
- `simulation_loop()` apenas chama `step()` e faz broadcast
- Os testes (`backend/tests/test_*.py`) já rodam o engine headless: instanciam `SimulationEngine`, chamam `step()` diretamente, 100+ steps sem broadcast

**O que impede um script CLI headless hoje:**
1. `simulation_loop()` é `async` e requer `asyncio.run()`
2. Startup cria engine e criaturas iniciais dentro do FastAPI (`startup_event`)
3. Sem forma padrão de "executar N ticks e salvar resultados"

## O que precisa ser feito
1. **Criar `backend/simulation/runner.py`** com `SimulationRunner`:
   - `__init__(initial_creatures=10, **params)`: instancia engine, aplica parâmetros
   - `step(n_ticks)`: executa N ticks síncronos (dt fixo 1/30)
   - `get_state()`: snapshot corrente
   - `save_snapshot(filepath)`: salva JSON do state
2. **Criar CLI** (`backend/cli.py` ou similar) com argparse:
   - `--ticks`, `--creatures`, `--output`, `--interval`, `--params` (JSON override)
   - Loop: roda em máxima velocidade (sem sleep), salva snapshots periódicos, imprime resumo
3. **Refatorar `main.py`** para reutilizar o runner/bootstrap (criação das criaturas iniciais fora do `startup_event`), mantendo comportamento atual do servidor
4. **Testes**: runner básico (100 ticks, população > 0), snapshots periódicos, override de parâmetros

## Perguntas em aberto
1. Snapshot ideal: apenas agregados (pop, births, deaths) ou estado completo (criaturas/comida)?
2. Requisito de determinismo (seed fixo → mesma execução)? Impactaria gestão de `random.seed()`
3. Modo fast-forward/benchmark desejado? (sem sleep — recomendado como default do CLI)
4. Integração com SQLite (models.py) para histórico persistente?

## Dependências
Sem bloqueadores. Nota do agente: BIT-26 (métricas) poderia reutilizar o `SimulationRunner`, mas não é obrigatório — as métricas podem viver no engine.
