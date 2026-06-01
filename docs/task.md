# Tarefas de Execução: Manager TUI & Testes

## Infraestrutura de Testes
- `[x]` Atualizar dependências: adicionar `pytest`, `httpx`, `questionary` e `rich` no `backend/requirements.txt`.
- `[x]` Criar testes iniciais no backend (`backend/tests/test_simulation.py`).
- `[x]` Configurar `vitest` no frontend (`package.json`, `vite.config.js`).
- `[x]` Criar testes unitários básicos no frontend (`frontend/src/tests/App.test.jsx`).

## Implementação da Interface TUI
- `[x]` Criar arquivo wrapper `manager.bat` na raiz.
- `[x]` Implementar base do `manager.py` (importação do `rich` e `questionary`).
- `[x]` Implementar lógica de Painel de Status (verificação de portas 8000 e 5173 via `netstat` filtrando `LISTENING`).
- `[x]` Implementar rotinas de Start (via `subprocess.Popen` com flag `CREATE_NO_WINDOW`).
- `[x]` Implementar rotinas de Stop (via `taskkill /F /T /PID`).
- `[x]` Implementar rotina de Build (Frontend) e Execução de Testes (Pytest/Vitest).
- `[x]` Implementar visualização dinâmica de Logs (`backend.log` e `frontend.log`).
- `[x]` Garantir loop contínuo e tratamento de `KeyboardInterrupt`.
