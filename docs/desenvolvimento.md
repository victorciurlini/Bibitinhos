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
