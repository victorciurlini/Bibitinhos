# Research — infra (BIT-28: Modo headless)

> Relatório do sub-agente Explore sobre `manager.py`, scripts e estrutura do repo para a demanda de modo headless.

## Arquivos relevantes
- `manager.py` (raiz, ~247 linhas) — TUI com `rich`/`questionary`
- `manager.bat` — wrapper Windows
- `backend/main.py` — entrada do servidor
- `backend/requirements.txt`, `backend/venv/` (Python 3.10.4)
- `docs/desenvolvimento.md` — como rodar localmente

## Conteúdo relevante

**manager.py hoje:**
- TUI interativa (questionary) — start/stop/restart backend e frontend independentemente
- Backend: `python -m uvicorn main:app --port 8001 --reload` (cwd `backend/`)
- Frontend: `npm run dev` (cwd `frontend/`, Vite porta 5173)
- Status por checagem de porta via `socket` (IPv4+IPv6); logs em `backend.log`/`frontend.log`
- Menu para rodar `pytest backend/tests/ -v` e `npm run test`

**Não existe CLI de simulação** — nenhum script roda o engine fora do uvicorn. Os testes pytest já exercitam o engine standalone (prova de que funciona sem servidor).

**Dependências já satisfeitas** pelo requirements.txt: pymunk, neat-python==0.92, numpy (essenciais); fastapi/uvicorn ficam sem uso no modo headless.

## O que precisa ser feito
1. **Criar `backend/cli.py`** — entry point argparse (`--ticks`, `--creatures`, `--output`, `--snapshot-interval`, `--seed`), roda síncrono em máxima velocidade, salva snapshots JSON e imprime resumo
2. **Testes** em `backend/tests/test_headless*.py` (roda N ticks, valida snapshots e campos)
3. **Documentar** em `docs/desenvolvimento.md` seção "Modo headless"
4. **manager.py**: opcionalmente adicionar item de menu "Rodar headless" — não obrigatório (CLI separado é suficiente e mais útil para CI)

## Perguntas em aberto
1. Frequência de snapshot: por segundo simulado vs por N ticks (proposta: a cada N ticks, configurável)
2. Formato: JSON único vs JSONL (proposta: JSON único com metadata + lista de snapshots)
3. Integrar ao menu do manager? (opcional, baixa prioridade)
