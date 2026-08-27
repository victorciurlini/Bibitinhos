# Research — infra (BIT-29: Docker / CI)

> Relatório do sub-agente Explore sobre dependências, versões, testes e estrutura para containerização e GitHub Actions.

## Arquivos relevantes
- `backend/requirements.txt`, `backend/venv/` (Python 3.10.4)
- `frontend/package.json`, `package-lock.json` (Node v24.18.0 local, npm 11.16.0)
- `manager.py` (orquestração local), `.gitignore`
- Git remote: `https://github.com/victorciurlini/Bibitinhos.git` (branches `develop` default, `master`)
- **Não existe** Dockerfile, docker-compose, `.github/workflows/`, `.env`/`.env.example`

## Dependências

**backend/requirements.txt:**
```
fastapi==0.103.1
uvicorn==0.23.2
websockets==11.0.3
SQLAlchemy==2.0.21
neat-python==0.92
pytest
httpx
questionary
rich
pymunk
numpy
```
- Python mínimo: 3.10 (venv atual: 3.10.4)
- pymunk e numpy têm build nativo, mas há wheels no PyPI (ok em Docker slim)
- `pytest`, `httpx`, `pymunk`, `numpy` sem pin (pytest no venv: 9.0.3)
- `questionary`/`rich` são só do manager.py (desnecessários na imagem)

**frontend/package.json:** deps `react ^18.3.1`, `react-dom ^18.3.1`; devDeps vite ^5.4.10, vitest ^2.1.0, eslint ^9. Scripts: `dev` (vite --port 5173 --strictPort), `build`, `lint`, `preview`, `test` (vitest run). **Não há arquivos de teste frontend hoje** — `vitest run` sem testes falha (precisa `--passWithNoTests` ou omitir do CI).

## Testes (backend)
- Comando: `cd backend && python -m pytest tests/ -v` — **157 passed**, ~3-4 s, ~6 DeprecationWarnings inofensivos do neat-python
- Sem pytest.ini/markers; sem flaky conhecidos

## Env vars / networking
- Nenhuma env var hoje; URLs hardcoded: backend `:8001` (`GET /` health check, `/ws` WebSocket), frontend `:5173`
- CORS: `allow_origins=["*"]` com comentário "em produção, defina a URL exata"
- WebSocket URL hardcoded no frontend (`SimulationCanvas.jsx`) → precisa virar `import.meta.env.VITE_WS_URL` com fallback para Docker
- SQLite `*.db` já no .gitignore (models.py não é usado na simulação viva)

## O que precisa ser feito
1. **`.github/workflows/ci.yml`**: job backend (setup-python 3.10, pip install, pytest) + job frontend (setup-node, npm ci, lint, build); triggers push/PR em develop/master
2. **`Dockerfile`(s)**: multi-stage — frontend `node:24-alpine` (npm ci + build) e backend `python:3.10-slim` (uvicorn `--host 0.0.0.0 --port 8001`)
3. **`docker-compose.yml`**: serviço backend (8001) + serviço frontend servindo `dist/` (nginx:alpine ou `vite preview`), com `VITE_WS_URL` configurável no build
4. **`.dockerignore`**: venv, node_modules, .git, logs, .sdd, docs
5. **Frontend**: parametrizar URL do WebSocket via `import.meta.env.VITE_WS_URL`
6. **Docs**: `docs/deployment.md` ou seção em desenvolvimento.md

## Perguntas em aberto
1. Push de imagem para registry (Docker Hub/GHCR)? — decisão de projeto; default: não (só build local/CI)
2. Coverage report no CI? — não usado hoje; opcional
3. Lint backend (ruff/black)? — não existe hoje; fora de escopo provável
