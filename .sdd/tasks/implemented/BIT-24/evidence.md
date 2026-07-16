# Evidência — BIT-24: Controles Interativos da Simulação

**Data de conclusão:** 2026-07-16

## Demanda atendida

Fundação de comandos cliente→servidor sobre o WebSocket existente e três recursos sobre ela:
controle de tempo (pausar / 0.5x–4x por substeps de `dt` fixo), inspeção client-side de um
bibite (clique → painel ao vivo com energia, idade, fase, visão e saídas do cérebro) e arrasto
de um bibite pelo mapa (teleporte re-fixado a cada frame de física). Protocolo WebSocket
aditivo e retrocompatível.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/creature.py` | modificado | `self.id = self.genome.key` no `__init__`; `to_dict()` ganhou id, age, max_energy, reproduction_cooldown, motor_forward, motor_torque, action_mate, action_grab_drop (mantendo os campos antigos) |
| `backend/simulation/engine.py` | modificado | `ALLOWED_SPEEDS`; estado `paused`/`speed`/`_held_creature`/`_drag_target`; `set_time_control` (com coerção de `speed` protegida contra não-numéricos), `get_creature_by_id`, `start_drag`, `drag_to`, `end_drag`; re-pin do drag antes de `physics.step(dt)`; `paused`/`speed` no `get_state()` |
| `backend/main.py` | modificado | `simulation_loop` com acumulador de substeps de `dt` fixo (1/30); `websocket_endpoint` com parse JSON + dispatch (`set_time_control`, `drag`); `end_drag()` no disconnect; `engine` criado antes do endpoint |
| `backend/tests/test_interactive_controls.py` | criado | 16 testes: 8 cenários da spec + coerção de `speed` não-numérico (correção do audit) |
| `docs/arquitetura.md` | modificado | Seção de contrato WebSocket ampliada (comandos cliente→servidor + campos novos do state) |
| `frontend/src/components/SimulationCanvas.jsx` | modificado | Refs (`wsRef`, `viewTransformRef`, `selectedIdRef`, `dragRef`), helpers (`sendCommand`, `toWorld`, `hitTest`), handlers de mouse (clique/seleção + drag com threshold de 5px), anel de seleção no renderLoop, interval de 150 ms alimentando `inspectedCreature`/`paused`/`speed`; compõe o `ControlMenu`; badge de Status movido para `top:10 right:10` |
| `frontend/src/components/ControlMenu.jsx` | criado | Menu HUD recolhível no canto superior esquerdo (botão ≡, escondido por padrão). Expandido, abre painel à esquerda com seções **Tempo** e **Inspetor** — feedback do usuário no teste de aceitação |
| `frontend/src/components/InspectorPanel.jsx` | criado | Conteúdo embutível (inline, sem posicionamento próprio): id, fase+idade, barra de energia, dieta, cooldown, 9 setores de visão, barras bipolares do cérebro + badges. Renderizado dentro do `ControlMenu` |
| `frontend/src/components/TimeControls.jsx` | criado | Conteúdo embutível (inline): ⏸/▶ e 0.5x/1x/2x/4x, botão ativo pelo eco do servidor. Renderizado dentro do `ControlMenu` |

## Resultados dos gates de qualidade

- `import main`: **OK**
- `pytest tests/`: **143 passed** (0 falhas; só warnings de deprecation pré-existentes do neat-python)
- `npm run build`: **OK**
- `npm run lint`: limpo nos arquivos novos/tocados da BIT-24; resta 1 erro pré-existente em `App.jsx` (`'React' is defined but never used`), não tocado por esta task e já vermelho em `develop` — não é regressão
- **Validação funcional** (smoke test WS end-to-end contra uvicorn real): TODOS OS CHECKS PASSARAM
  - state ecoa `paused`/`speed`; criaturas trazem `id` + campos de inspeção
  - `speed=2.0` aplica; `speed:"abc"`/`[1,2]` são no-op sem derrubar a conexão (bloqueante do audit resolvido)
  - `paused` alterna; drag fixa a criatura em ~(123,456)
  - ação desconhecida + JSON malformado = no-op, conexão viva

## Audit

Auditado pelo `bibitinhos-revisor`: 1 bloqueante (coerção de `speed` no dispatch podia derrubar
a conexão com input não-numérico). **Corrigido** em `engine.set_time_control` + teste novo; ver
`review-report.md` (seção "Resolução do bloqueante"). Não-bloqueantes registrados: drift
"2000×2000" em `docs/arquitetura.md` (pré-existente do BIT-22, mapa real é 1400 — deixado para
task de doc-fix) e `prop-types` via `eslint-disable` nos componentes novos (aceitável dado "sem
libs novas").

## Como validar

1. `manager.py` → subir backend (:8001) e frontend (:5173) — ou serviços já rodando.
2. **Menu recolhível**: por padrão só aparece o botão **≡** no canto superior esquerdo (o badge
   de Status fica no topo-direita). Clicar no ≡ abre o menu à esquerda com as seções **Tempo** e
   **Inspetor**; o **×** no cabeçalho recolhe de volta.
3. **Tempo** (dentro do menu): **⏸** congela todas as criaturas; **▶** retoma. **2x/4x** aceleram
   visivelmente sem mudar a física (mesmo `dt` por step); **0.5x** desacelera. O botão ativo
   reflete o servidor.
4. **Inspetor** (dentro do menu): **clicar** num bibite mostra anel de destaque + id, fase, idade,
   energia, cooldown, 9 setores de visão e saídas do cérebro, atualizando ~a cada 150 ms; sem
   seleção, mostra a dica "Clique num bibite para inspecionar"; clicar no vazio deseleciona; se o
   bibite morre, o anel some e o inspetor volta à dica.
5. **Arrastar** um bibite: ele segue o cursor em tempo real (inclusive com a simulação pausada)
   e, ao soltar, continua vivendo do novo ponto. Cliques (< 5px) não disparam arrasto.

> Verificado ao vivo no navegador (2026-07-16): menu recolhido/expandido, pausa/retomada,
> seleção com anel e inspetor populando dentro do menu (#73 ADULT, energia, visão, cérebro).
