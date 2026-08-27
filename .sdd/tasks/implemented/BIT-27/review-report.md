# Relatório de revisão — BIT-27: Inspetor de Rede Neural

## Veredito
**APROVADO**

## Resultado dos gates (rodados pelo revisor)
- `venv\Scripts\python.exe -c "import main"` → OK
- `venv\Scripts\python.exe -m pytest tests/ -q` → **175 passed, 8 warnings** (166 baseline + 9 novos)
- `npm run build` → OK (41 módulos, 1.47s)

## ERROS BLOQUEANTES
Nenhum.

## Verificações realizadas

### Invariante crítica — contrato NEAT
- [OK] `git diff d02a7f5` em `neat_config.ini`, `creature.py`, `engine.py`, `params.py`: **zero mudanças**. Em `rtneat_wrapper.py` só há adições (labels + `genome_to_dict`); seeds Gen 0, mutação, crossover e constantes de balanceamento intocados.
- [OK] `INPUT_LABELS`/`OUTPUT_LABELS` (rtneat_wrapper.py:74-85) espelham exatamente a docstring canônica do módulo (linhas 10-27): setores visuais 0-8 → keys -1..-9, Energy(9), Age(10), Hormonal(11), Clock(12), Load(13), Kinetic linear/angular(14-15); outputs 0-3 na ordem Motor_Forward, Motor_Torque, Action_Grab_Drop, Action_Mate.

### Corretude do `genome_to_dict` (rtneat_wrapper.py:162-187)
- [OK] Inputs derivados de `config.genome_config.input_keys` com `INPUT_LABELS[i]` casando com key `-(i+1)`; outputs classificados via `gc.output_keys` com label/bias/activation; hidden (key >= 4) sem label, com bias/activation; conexões com from/to/weight/`bool(enabled)`; `json.dumps` validado em teste. Implementação idêntica ao pseudocódigo da spec.

### Backend — ação WebSocket (main.py:50-63, 102-106)
- [OK] Resposta estritamente unicast (`websocket.send_json` no socket que pediu); broadcast/`state_update` intocados. Id inexistente → `genome: null`. Contrato da mensagem bate com a spec e com `docs/arquitetura.md`.

### Testes (test_genome_inspection.py — 9 testes)
- [OK] Não triviais: dimensões vêm de `genome_config` (sem hardcode de 16/4/20/64), labels conferidos por índice contra `input_keys`/`output_keys`, conexões espelhadas contra `genome.connections`, hidden via `mutate_add_node` (determinístico no genoma zero totalmente conectado), payload com id válido e inexistente.

### Frontend
- [OK] Roteamento por `data.type` em `SimulationCanvas.jsx:116-126` é seguro: o broadcast já carrega `state["type"] = "state_update"` (main.py:125, pré-existente), então o hot-path 30 FPS e o fluxo de metrics do BIT-26 continuam funcionando; `creature_inspection` vai para ref (sem re-render no hot-path).
- [OK] Seleção (SimulationCanvas.jsx:350-357): limpa a ref a cada clique (seleção, troca ou deseleção) e envia `inspect_creature` uma vez por nova seleção. O espelho de 150 ms (linha 396) só expõe o genoma se `creature_id` da resposta == seleção corrente — resposta atrasada de seleção anterior e criatura morta nunca vazam para o painel.
- [OK] `NeuralNetworkViewer.jsx`: SVG width 218 cabe no painel de 244px; inputs em ordem do contrato (sort descendente de key: -1 no topo); cores/espessura/opacity conforme spec; `<title>` com label/key + bias/activation; arestas filtradas por `enabled` e por nós posicionados (defensivo).
- [OK] `InspectorPanel.jsx`: seção colapsável no padrão `.hud-group`, "carregando rede…" em `HUD.textDim` enquanto `genome == null`; `genome: null` não quebra (viewer retorna null).

### Desvios declarados pelo implementer
1. **ControlMenu.jsx (2 linhas)** — ACEITO. Inconsistência interna da spec: o passo 5 exige `genome` chegar ao InspectorPanel "via ControlMenu", que o renderiza; o repasse é a mudança mínima necessária.
2. **Helper puro em vez de TestClient** — ACEITO. Confirmei o precedente idêntico no BIT-26 (`test_metrics.py:138`, mesmo motivo: starlette 0.27 + httpx 0.28 não convivem no venv). O ramo do dispatch fica com uma linha não coberta por socket real, risco mínimo.
3. **Seção aberta por padrão** — ACEITO. Spec omissa; necessário para o critério de aceite "selecionar exibe o grafo" sem clique extra.

## OPORTUNIDADES DE MELHORIA (não bloqueiam)
1. `frontend/src/components/NeuralNetworkViewer.jsx:77` — rodapé "nós · conexões" usa acentos, enquanto o restante das strings do HUD é pt-BR sem acentos ("Metricas", "Clique num bibite..."). Cosmético; segue o literal da spec, mas destoa do padrão do HUD.
2. `backend/main.py:57` — `next((c for c in engine.creatures ...))` duplica `engine.get_creature_by_id()` já existente (engine.py:109). A spec ditou o `next(...)`, mas reusar o método reduziria duplicação.
3. `backend/tests/test_genome_inspection.py` — não há teste garantindo que `INPUT_LABELS[i]` casa semanticamente com a docstring (só dimensões e ordem posicional); aceitável, pois a fonte é a mesma constante.

## Resumo
Pode fechar a task. Todos os critérios de aceite cumpridos, contrato NEAT intocado, protocolo WS retrocompatível (aditivo), 175 testes verdes e build do frontend OK. Os 3 desvios declarados são justificados; as melhorias listadas são cosméticas e opcionais.
