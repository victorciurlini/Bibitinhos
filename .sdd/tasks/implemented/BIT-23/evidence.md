# Evidência — BIT-23: Parâmetros Editáveis em Tempo Real

**Data de conclusão:** 2026-07-16

## Demanda atendida

Ajuste das constantes de balanceamento da simulação **em tempo real** pela UI, sem editar
código nem reiniciar o backend. Um registry central (`backend/simulation/params.py`) mapeia 22
parâmetros (4 grupos: Energia, Reprodução, Ecossistema, Ambiente) para seus bindings reais; o
transporte reutiliza o dispatch WebSocket do BIT-24 (`set_param`/`reset_params`) e o eco vem em
`state["params"]`. Ajustes valem só em memória (reiniciar restaura os defaults do código) e há
botão "Restaurar padrões".

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/params.py` | criado | Registry `PARAM_SPECS` (22 params, 4 grupos) + `get_params`/`set_param`/`reset_params` + setters especiais (metabolismo dict, damping do Space) resolvidos via `globals()`. `set_param` faz clamp, coerção int quando `default` é int, e retorna `False` para nome desconhecido / valor não-numérico / NaN |
| `backend/simulation/food.py` | modificado | `FOOD_ENERGY_VALUE = 32.0` extraído; `__init__(..., energy_value=None)` com sentinel |
| `backend/simulation/engine.py` | modificado | `get_state()` inclui `"params": get_params(self)` (import no topo) |
| `backend/main.py` | modificado | Ramos `set_param`/`reset_params` no dispatch do BIT-24 |
| `backend/tests/test_params.py` | criado | 10 cenários da spec, com fixture que reseta no teardown |
| `docs/simulacao.md` | modificado | Nota: valores são defaults tunáveis em runtime via painel (BIT-23) |
| `frontend/src/components/ParamsPanel.jsx` | criado | Conteúdo embutível `{ params, onCommand }`: 22 params em 4 grupos colapsáveis com `<input type="range">` + valor; metadados hardcodados espelhando `PARAM_SPECS`; botão "Restaurar padrões"; eco vs. slider em uso via `activeParamRef`/`localValues` |
| `frontend/src/components/ControlMenu.jsx` | modificado | Nova seção "Parâmetros" (3ª, após Tempo e Inspetor) — **decisão de layout do developer**; prop `params` |
| `frontend/src/components/SimulationCanvas.jsx` | modificado | Expõe `params` (de `state.params`) num `useState` alimentado pelo mesmo interval de 150 ms; passa ao `ControlMenu` |

## Resultados dos gates de qualidade

- `import main`: **OK**
- `pytest tests/`: **153 passed** (143 do BIT-24 + 10 novos do `test_params.py`; só warnings de deprecation pré-existentes do neat-python)
- `npm run build`: **OK**
- `npm run lint`: limpo nos arquivos novos/tocados; resta o erro pré-existente em `App.jsx` (não é regressão)
- **Validação funcional (WS smoke, backend fresco em :8002):** TODOS OS CHECKS PASSARAM
  - `state.params` presente com 22 chaves
  - `set_param` aplica e ecoa; clamp (999 → max 5.0); coerção int (`max_total_food` 75.6 → 76)
  - nome desconhecido + valor `"abc"` = no-op sem derrubar a conexão
  - `reset_params` restaura os defaults da tabela (idle 1.2, max_total_food 110)
- **Verificação no navegador:** seção "Parâmetros" renderiza como 3ª seção do menu esquerdo, com os 4 grupos colapsáveis + botão "Restaurar padrões"; grupo Energia expande com os 6 sliders rotulados; sem white-screen mesmo com `params` ausente (retrocompatível)

## Audit

`bibitinhos-revisor`: **APROVADO — sem bloqueantes**. Conferiu os 22 bindings contra o código
pós-BIT-22, a consistência **chave a chave** entre `PARAM_SPECS` (backend) e os metadados do
`ParamsPanel.jsx` (frontend, sem divergência), a lógica de clamp/coerção/reset, os 10 testes e a
ausência de regressões (contrato NEAT intocado, dispatch aditivo). Ver `review-report.md`.
Oportunidades não-bloqueantes registradas (flicker transitório de ~150 ms, teste de contrato
backend↔frontend se a tabela crescer).

## Como validar

1. **Reiniciar o backend** (`manager.py` → Restart, ou parar/subir): a instância em execução
   pode ter sido iniciada antes do BIT-23 e não servir `params`. Após reiniciar, `state.params`
   passa a chegar e os sliders mostram os valores correntes.
2. Abrir o frontend, ≡ (menu esquerdo) → seção **Parâmetros** → expandir um grupo.
3. Arrastar **"Imposto de ociosidade"** para ~5.0 com a sim rodando: criaturas paradas passam a
   morrer bem mais rápido, **sem reiniciar nada**.
4. **"Arrasto da água"** (grupo Ambiente) em ~0.9: criaturas ficam visivelmente mais deslizantes.
5. **"Restaurar padrões"**: todos os sliders e o comportamento voltam aos valores do código.
6. Reiniciar o backend descarta todos os ajustes (nada persistido).
