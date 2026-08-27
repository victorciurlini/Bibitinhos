# Review — BIT-29: Docker e CI

**Veredito: APROVADO** (registrado pelo orquestrador a partir da saída do revisor)

## Gates (rodados pelo revisor)
- `import main`: OK
- `pytest tests/ -q`: **180 passed**, 8 warnings (deprecations conhecidas)
- `npm run lint`: OK (0 erros — erro pré-existente do App.jsx eliminado)
- `npm run build`: OK (166.42 kB, gzip 53.57 kB)
- `docker compose config --quiet`: OK
- Injeção build-time do `VITE_WS_URL`: verificada empiricamente — build com `VITE_WS_URL=ws://exemplo-docker:9999/ws` colocou a URL no bundle; rebuild default restaurou o fallback

## Erros bloqueantes
Nenhum.

## Oportunidades de melhoria (não bloqueantes)
- `backend/Dockerfile:4` — imagem de runtime instala deps de dev (`pytest`, `httpx`, `questionary`, `rich`) porque o `requirements.txt` é único; um `requirements-dev.txt` separado enxugaria a imagem (task futura).
- `frontend/.dockerignore` — poderia incluir `npm_install.log` (infla o build context; não chega à imagem final por ser multi-stage).

## Verificações OK
- `.github/workflows/ci.yml` idêntico à spec: triggers push/PR em develop/master; `backend-tests` (setup-python@v5 3.10, cache pip, pytest); `frontend-build` (setup-node@v4 Node 24, cache npm, `npm ci` → lint → build). Sem `npm run test`, registry, coverage ou deploy.
- `backend/Dockerfile` python:3.10-slim com ordem de camadas correta; `neat_config.ini` entra na imagem (dependência de runtime via `os.path.dirname(__file__)` em `rtneat_wrapper.py:45`).
- `frontend/Dockerfile` multi-stage node:24-alpine → nginx:alpine; `ARG/ENV VITE_WS_URL` antes do `npm run build` (condição para o Vite injetar no bundle — confirmado por build real).
- `docker-compose.yml`: backend 8001:8001, frontend 5173:80 com `depends_on`, build arg `ws://localhost:8001/ws` (correto — o browser fala com a porta publicada no host).
- `SimulationCanvas.jsx`: diff restrito a `WS_URL` (topo do módulo, fallback idêntico ao valor antigo) e `new WebSocket(WS_URL)`.
- Desvio 1 (`.gitignore` intocado): justificado — compose não gera artefatos locais.
- Desvio 2 (compose build não executado — daemon do Docker Desktop parado): sancionado pela própria spec (passo 6). Validação manual de `docker compose up --build` fica pendente; risco residual baixo.
- Desvio 3 (orquestrador removeu `import React` morto de `App.jsx`): seguro — eslint.config.js usa `jsx-runtime` e o plugin-react do Vite usa o JSX runtime automático; sem o fix, o critério "CI verde no primeiro push" falharia.
- Regressões: diff vs `e4f5a56` restrito a infra, docs e às 2 mudanças de frontend; suíte 100% verde.

## Pendência (fora do gate)
- `docker compose up --build` de ponta a ponta quando o Docker Desktop estiver ativo.
