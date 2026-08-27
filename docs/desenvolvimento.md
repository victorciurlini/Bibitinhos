# Guia de Desenvolvimento

## Rodar localmente

```bash
# TUI (Windows): sobe/derruba backend e frontend, mostra status das portas
manager.bat            # ou: python manager.py

# Manual
cd backend  && venv\Scripts\python.exe -m uvicorn main:app --port 8001 --reload
cd frontend && npm run dev
```

- Backend: `http://localhost:8001` (health em `/`, stream em `/ws`)
- Frontend: `http://localhost:5173`
- Logs do TUI: `backend.log` / `frontend.log` na raiz (PIDs em `*.pid`)

## Testes

```bash
backend\venv\Scripts\python.exe -m pytest backend/tests/ -v
```

Convenções da suíte:

- **Nunca hardcodar valores de balanceamento** — importar as constantes dos módulos
  (`from simulation.creature import IDLE_PENALTY_RATE`, etc.). É isso que permite
  retunar o ecossistema sem quebrar a suíte (padrão firmado no BIT-16/20).
- Testes de comportamento montam criaturas com estado forçado (fase, energia,
  velocidade) e chamam `update()`/`compute_vision()` direto, sem subir o servidor.
- A validação que importa em mudanças de balanceamento é **funcional**: rodar via
  `manager.py` por alguns minutos e observar o comportamento (as specs listam os
  critérios observáveis).

## Modo headless (BIT-28)

Roda a simulação sem frontend e sem servidor — loop síncrono em velocidade máxima
(sem `sleep`/asyncio), útil para experimentos longos, benchmarks e CI:

```bash
cd backend
venv\Scripts\python.exe cli.py --ticks 9000 --seed 42 --output run.json
```

Flags (todas opcionais):

| Flag | Default | Descrição |
|---|---|---|
| `--ticks` | 9000 | steps de 1/30 s (9000 = 5 min simulados) |
| `--creatures` | 10 | população inicial (Gen 0) |
| `--snapshot-interval` | 300 | ticks entre snapshots de métricas (300 = 10 s) |
| `--seed` | nenhum | reprodutibilidade: mesmo seed → mesma série de snapshots |
| `--output` | nenhum | arquivo JSON de saída (sem ele, só imprime o progresso) |

Saída JSON: `{"metadata": {...flags do run...}, "snapshots": [...]}`, onde cada
snapshot é o dict de `compute_metrics()` (contrato do BIT-26: `time`, `population`,
`stage_counts`, `avg_energy`, `avg_age`, `births_total`, `deaths_total`, `food_count`,
`oases_count`). Sempre há um snapshot no tick 0 e um no tick final.

Programaticamente: `HeadlessRunner(initial_creatures, seed).run(ticks, snapshot_interval,
on_snapshot)` em `backend/simulation/runner.py`; `populate(engine, count)` é o mesmo
bootstrap de população usado pelo `startup_event` do servidor.

## Docker (BIT-29)

Alternativa ao `manager.py` para subir o stack completo sem instalar Python/Node:

```bash
docker compose up --build
```

- Backend: `python:3.10-slim` + uvicorn, publicado em `http://localhost:8001`
  (health em `/`, stream em `/ws`) — mesma porta do dev local.
- Frontend: build multi-stage (`node:24-alpine` roda `npm run build` →
  `nginx:alpine` serve o `dist/`), publicado em `http://localhost:5173`.
- **`VITE_WS_URL`**: a URL do WebSocket é resolvida em **build time** (o Vite
  injeta no bundle), por isso é um build `arg` no `docker-compose.yml`, não env
  de runtime. Default: `ws://localhost:8001/ws` — o browser fala com o backend
  pela porta publicada no host, não pelo hostname interno do compose. Para
  servir em outro host, ajuste o arg e refaça o build do frontend.
- Sem Docker nada muda: o fallback no `SimulationCanvas.jsx`
  (`import.meta.env.VITE_WS_URL || 'ws://localhost:8001/ws'`) mantém o
  desenvolvimento local idêntico.

## CI (GitHub Actions)

Workflow `CI` (`.github/workflows/ci.yml`) roda a cada push/PR em
`develop`/`master`, com dois jobs paralelos:

- **backend-tests**: Python 3.10, `pip install -r requirements.txt`,
  `python -m pytest tests/ --tb=short`.
- **frontend-build**: Node 24, `npm ci`, `npm run lint`, `npm run build`.

Sem push para registry, coverage ou deploy (fora de escopo). `npm run test`
não roda no CI por enquanto — não há arquivos de teste no frontend e o
`vitest run` sem testes falha; adicionar ao workflow quando existirem.

## Workflow de tasks (`.sdd/tasks/`)

Sem Linear — todo o fluxo é local, e **a pasta onde a task está reflete o seu estado**:

```
.sdd/tasks/refiner/BIT-XX/      →  spec sendo refinada (demanda → spec técnica)
.sdd/tasks/implementer/BIT-XX/  →  em implementação (spec aprovada)
.sdd/tasks/implemented/BIT-XX/  →  concluída (spec + evidence.md + relatórios)
```

- Skills do Claude Code: `/refiner` (analisa demanda e produz spec) e `/implementer`
  (executa a spec). Cada BIT-XX guarda `*.md` da spec, `evidence.md` e, quando houve
  revisão por sub-agente, `impl-report.md` / `review-report.md`.
- A numeração BIT-XX é definitiva (BIT-11 não existe; a sequência pulou).
- **Manter o roadmap:** ao criar ou fechar uma task, atualize o [`roadmap.md`](roadmap.md)
  (mova a entrada entre 🔧 → 🔜 → ✅ conforme o estado) e reflita o resumo no bloco
  `## Roadmap` do `README.md` — os dois no mesmo commit, para não haver lista de pendências
  duplicada ou desatualizada.

## Fluxo git

```
BIT-XX (branch da task) → develop (após testes verdes) → master (só ao fechar milestone)
```

- Uma branch por task, nome igual à pasta (`BIT-20`).
- Commits em pt-BR, prefixo convencional: `feat(BIT-XX): ...`, `fix:`, `chore:`, `docs:`.
- Identidade: conta pessoal `victorciurlini` via config local do repo.

## Onde mexer para cada tipo de mudança

| Quero mudar... | Arquivo |
|---|---|
| Balanceamento de energia/locomoção | `backend/simulation/creature.py` (constantes no topo) |
| Regras/custos de reprodução | `backend/simulation/engine.py` (constantes no topo) |
| Visão (raio, FOV, semântica do sinal) | `backend/simulation/sensors.py` |
| Contrato de I/O do cérebro, seeds da Gen 0 | `backend/simulation/rtneat_wrapper.py` + `neat_config.ini` |
| Oásis / Jardim do Éden | `backend/simulation/oasis.py` (+ orquestração em `engine.py`) |
| Física global (damping, paredes, mundo) | `backend/simulation/physics.py` |
| Renderização | `frontend/src/components/SimulationCanvas.jsx` |

Cuidados recorrentes (aprendidos a caro preço — não regredir):

- `LATERAL_GRIP_RATE` < ~11.1 quebra o teste de derrapagem lateral (BIT-07/17).
- Mudar o contrato de I/O do NEAT invalida genomas — o contrato (16 in / 4 out,
  ordem e semântica) está documentado na docstring de `rtneat_wrapper.py` e deve
  permanecer estável; seeds alteram só valores iniciais, nunca topologia.
- Se a população colapsar após retunagem, a escada de ajuste do BIT-20 é:
  `IDLE_PENALTY_RATE` ↓ → `Food.energy_value` ↑ → `MOVEMENT_REFERENCE_SPEED` ↓.
- O imposto de ociosidade deve continuar medido pela **velocidade real** do corpo
  (nunca pelo output do motor) e o EGG deve continuar isento.
