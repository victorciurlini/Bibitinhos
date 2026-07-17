# Spec — BIT-29: Docker e CI

**Linear:** N/A
**Risco:** low
**Camada(s):** Infra (+ 1 linha no Frontend)

---

## Demanda

Containerizar o Bibitinhos (backend + frontend) com Docker/docker-compose e criar um pipeline de CI no GitHub Actions que roda os testes do backend e o build/lint do frontend a cada push/PR em `develop`/`master`.

## Abordagem técnica

Dois Dockerfiles (um por serviço, imagens oficiais slim/alpine — pymunk/numpy têm wheels no PyPI, sem toolchain de build) orquestrados por um `docker-compose.yml`: backend `python:3.10-slim` rodando uvicorn, frontend build multi-stage `node:24-alpine` → `nginx:alpine` servindo o `dist/`. A única mudança de código é parametrizar a URL do WebSocket (hoje hardcoded em `SimulationCanvas.jsx:85`) via `import.meta.env.VITE_WS_URL` com fallback ao valor atual — sem Docker, nada muda. CI com dois jobs paralelos (pytest e build+lint do frontend); **sem** push para registry, coverage ou deploy (fora de escopo).

**Não depende** dos outros BITs do milestone (o CI rodará os testes que existirem no momento do merge).

## Arquivos a tocar

| Arquivo | Alteração | Descrição |
|---|---|---|
| `backend/Dockerfile` | criar | python:3.10-slim + uvicorn |
| `backend/.dockerignore` | criar | venv, caches, logs |
| `frontend/Dockerfile` | criar | multi-stage node build → nginx |
| `frontend/.dockerignore` | criar | node_modules, dist |
| `docker-compose.yml` | criar | orquestração dos dois serviços |
| `.github/workflows/ci.yml` | criar | jobs backend-tests e frontend-build |
| `frontend/src/components/SimulationCanvas.jsx` | modificar | URL do WS via `VITE_WS_URL` |
| `.gitignore` | modificar | artefatos locais de compose (se houver) |
| `docs/desenvolvimento.md` | modificar | seção "Docker" e "CI" |

## Passos de implementação

1. **`SimulationCanvas.jsx`:** no topo do módulo:
   ```javascript
   const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8001/ws';
   ```
   e na linha 85: `const ws = new WebSocket(WS_URL);`
2. **`backend/Dockerfile`:**
   ```dockerfile
   FROM python:3.10-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   EXPOSE 8001
   CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
   ```
   `backend/.dockerignore`: `venv/`, `__pycache__/`, `*.pyc`, `*.log`, `*.db`, `tests/` (imagem de runtime não precisa; CI roda pytest fora do Docker).
3. **`frontend/Dockerfile`:**
   ```dockerfile
   FROM node:24-alpine AS build
   WORKDIR /app
   COPY package*.json ./
   RUN npm ci
   COPY . .
   ARG VITE_WS_URL=ws://localhost:8001/ws
   ENV VITE_WS_URL=$VITE_WS_URL
   RUN npm run build

   FROM nginx:alpine
   COPY --from=build /app/dist /usr/share/nginx/html
   EXPOSE 80
   ```
   `frontend/.dockerignore`: `node_modules/`, `dist/`.
   Nota: `VITE_WS_URL` é resolvida em **build time** (Vite injeta no bundle) — por isso é `ARG` do build, não env de runtime.
4. **`docker-compose.yml`** (raiz):
   ```yaml
   services:
     backend:
       build: ./backend
       ports:
         - "8001:8001"
     frontend:
       build:
         context: ./frontend
         args:
           VITE_WS_URL: ws://localhost:8001/ws
       ports:
         - "5173:80"
       depends_on:
         - backend
   ```
   (O browser acessa o backend via `localhost:8001` publicado — por isso a URL do WS aponta para localhost, não para o hostname interno do compose.)
5. **`.github/workflows/ci.yml`:**
   ```yaml
   name: CI

   on:
     push:
       branches: [develop, master]
     pull_request:
       branches: [develop, master]

   jobs:
     backend-tests:
       runs-on: ubuntu-latest
       defaults:
         run:
           working-directory: backend
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
           with:
             python-version: "3.10"
             cache: pip
             cache-dependency-path: backend/requirements.txt
         - run: pip install -r requirements.txt
         - run: python -m pytest tests/ --tb=short

     frontend-build:
       runs-on: ubuntu-latest
       defaults:
         run:
           working-directory: frontend
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-node@v4
           with:
             node-version: "24"
             cache: npm
             cache-dependency-path: frontend/package-lock.json
         - run: npm ci
         - run: npm run lint
         - run: npm run build
   ```
   Não incluir `npm run test` — não há arquivos de teste no frontend hoje e `vitest run` sem testes falha; adicionar quando existirem.
6. **Validação local:** `docker compose up --build` → `http://localhost:5173` carrega a simulação conectada ao backend; `GET http://localhost:8001/` responde o health check. (Se Docker não estiver disponível na máquina, validar Dockerfiles por revisão e confiar no CI.)
7. **Docs:** `desenvolvimento.md` ganha seções "Docker" (compose up, portas, VITE_WS_URL) e "CI" (o que roda, quando).

## Contratos técnicos

### Infra
- Serviços compose: `backend` (host 8001) e `frontend` (host 5173 → nginx 80).
- Build arg do frontend: `VITE_WS_URL` (default `ws://localhost:8001/ws`).
- Workflow `CI` com jobs `backend-tests` e `frontend-build`; gatilhos push/PR em develop/master.

### Frontend
- `const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8001/ws'` — comportamento local inalterado.

## Critérios de aceite

- [ ] `docker compose up --build` sobe os dois serviços; simulação visível em `localhost:5173` e conectada ao WS.
- [ ] Workflow CI verde no GitHub (pytest + lint + build) no primeiro push da branch.
- [ ] Desenvolvimento local sem Docker permanece idêntico (manager.py, portas, WS URL default).
- [ ] `pytest backend/tests/` verde localmente; frontend `npm run build` ok.

## Rollback

Reverter a branch BIT-29: deletar Dockerfiles, `.dockerignore`s, `docker-compose.yml`, `.github/workflows/ci.yml`; restaurar `SimulationCanvas.jsx`, `.gitignore` e docs.
