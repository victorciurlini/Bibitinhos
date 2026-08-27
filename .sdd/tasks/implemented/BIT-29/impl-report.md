# Relatório de implementação — BIT-29: Docker e CI

## Status
CONCLUÍDO (com uma ressalva pré-existente de lint — ver "Problemas encontrados")

## Passos executados
1. Parametrizada a URL do WebSocket no `SimulationCanvas.jsx` via `VITE_WS_URL` com fallback ao valor atual.
2. Criados `backend/Dockerfile` + `backend/.dockerignore` (python:3.10-slim + uvicorn).
3. Criados `frontend/Dockerfile` + `frontend/.dockerignore` (multi-stage node:24-alpine → nginx:alpine, `VITE_WS_URL` como build ARG).
4. Criado `docker-compose.yml` na raiz (backend 8001, frontend 5173→80, depends_on).
5. Criado `.github/workflows/ci.yml` (jobs `backend-tests` e `frontend-build`, gatilhos push/PR em develop/master; sem `npm run test`, conforme spec).
6. Adicionadas seções "Docker (BIT-29)" e "CI (GitHub Actions)" em `docs/desenvolvimento.md`.
7. Rodados todos os gates de qualidade (detalhe abaixo).

## Arquivos modificados
| Arquivo | Alteração |
|---|---|
| `frontend/src/components/SimulationCanvas.jsx` | `const WS_URL = import.meta.env.VITE_WS_URL \|\| 'ws://localhost:8001/ws'` no topo do módulo + `new WebSocket(WS_URL)` (única mudança de comportamento; dev local idêntico) |
| `backend/Dockerfile` | criado — python:3.10-slim, pip install, uvicorn `--host 0.0.0.0 --port 8001` |
| `backend/.dockerignore` | criado — `venv/`, `__pycache__/`, `*.pyc`, `*.log`, `*.db`, `tests/` |
| `frontend/Dockerfile` | criado — build node:24-alpine (`npm ci` + `npm run build` com ARG/ENV `VITE_WS_URL`) → nginx:alpine servindo `dist/` |
| `frontend/.dockerignore` | criado — `node_modules/`, `dist/` |
| `docker-compose.yml` | criado — serviços `backend` (8001:8001) e `frontend` (5173:80, build arg `VITE_WS_URL: ws://localhost:8001/ws`) |
| `.github/workflows/ci.yml` | criado — jobs paralelos `backend-tests` (setup-python 3.10 + cache pip + pytest) e `frontend-build` (setup-node 24 + cache npm + `npm ci` + lint + build) |
| `docs/desenvolvimento.md` | seções "Docker (BIT-29)" e "CI (GitHub Actions)" inseridas antes de "Workflow de tasks" |
| `.gitignore` | **não modificado** — o compose não gera artefatos locais no filesystem do projeto (build fica no daemon; `*.db`/logs já cobertos). A spec previa mudança "se houver" — não houve |

## Problemas encontrados
1. **Lint pré-existente (fora de escopo — NÃO corrigido):** `npm run lint` falha com 1 erro que já existia antes desta task:
   `frontend/src/App.jsx:1:8 — 'React' is defined but never used (no-unused-vars)`.
   `App.jsx` está intocado desde o commit inicial (`43bf457`). Como o job `frontend-build` do CI roda `npm run lint`, **esse erro fará o CI falhar no primeiro push** (critério de aceite "workflow verde no primeiro push" em risco). Correção é trivial (remover o import `React` não usado, desnecessário com o JSX transform do Vite), mas está fora dos arquivos permitidos — decisão fica com o orquestrador.
2. **Daemon do Docker parado:** CLI presente (Docker 29.6.1 / Compose v5.3.0), mas `docker compose build` falhou com `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine` — Docker Desktop não estava rodando e não foi iniciado por decisão de não interferir na máquina. Mitigação: `docker compose config --quiet` passou (validação client-side do compose, sem daemon) e os Dockerfiles foram validados por inspeção (todas as deps do `requirements.txt` têm wheels/são puras para py3.10 slim; `package-lock.json` existe para `npm ci`; ARG/ENV `VITE_WS_URL` vem antes do `npm run build`, então o Vite injeta a var no bundle).
3. **pyyaml ausente no venv:** validado o YAML instalando pyyaml em diretório do scratchpad (via `pip --target`, venv intocado) — `ci.yml` e `docker-compose.yml` parseiam OK.

## Resultado dos gates
| # | Gate | Resultado |
|---|---|---|
| 1 | `import main` | OK — "OK - app importa" |
| 2 | `pytest tests/ -q` | **180 passed**, 8 warnings (deprecations conhecidas do neat-python/pydantic) |
| 3 | `npm run build` | OK — 41 módulos, bundle 166.42 kB, built in 1.86s |
| 4 | `npm run lint` | 1 erro **pré-existente** em `App.jsx` (nenhum erro novo introduzido) |
| 5 | Docker | CLI disponível; `docker compose build` não executou (daemon parado); `docker compose config --quiet` OK; Dockerfiles validados por inspeção |
| 6 | YAML do workflow | OK via pyyaml no scratchpad — jobs `['backend-tests', 'frontend-build']`, services `['backend', 'frontend']` |

## Próximos passos sugeridos ao orquestrador
- Decidir sobre o fix de 1 linha em `App.jsx` (remover `import React`) antes do push, para o critério "CI verde no primeiro push" se sustentar.
- Quando o Docker Desktop estiver ativo, rodar `docker compose up --build` e conferir `localhost:5173` conectado ao WS (critério de aceite 1).
