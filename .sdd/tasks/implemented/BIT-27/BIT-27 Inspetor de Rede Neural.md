# Spec — BIT-27: Inspetor de Rede Neural

**Linear:** N/A
**Risco:** medium
**Camada(s):** Múltiplas — Backend (Simulação) + API/WebSocket + Frontend

---

## Demanda

Ao inspecionar uma criatura (clique — fluxo do BIT-24), visualizar o cérebro dela: o grafo da rede NEAT (nós de input/hidden/output e conexões com pesos), renderizado numa seção nova do InspectorPanel.

## Abordagem técnica

O genoma é imutável durante a vida da criatura, então ele é enviado **uma vez por seleção** via nova ação WebSocket `inspect_creature`, respondida em **unicast** com `creature_inspection` (protocolo aditivo — nada muda no `state_update`). A serialização vive no `rtneat_wrapper.py` (dono do contrato NEAT), incluindo os nós de input que não existem em `genome.nodes` (validado no venv: Gen 0 tem `genome.nodes` só com keys 0-3; inputs -1..-16 vêm de `config.genome_config.input_keys`). O frontend renderiza o grafo em **SVG puro** com layout em 3 colunas fixas (inputs → hidden → outputs) — o grafo é pequeno (Gen 0: 20 nós, 64 conexões), dispensando lib de visualização.

**Fora de escopo:** ativações de nós em tempo real (FeedForwardNetwork não as expõe; exigiria wrapper da rede), comparação de genomas, persistência de genomas.

## Arquivos a tocar

| Arquivo | Alteração | Descrição |
|---|---|---|
| `backend/simulation/rtneat_wrapper.py` | modificar | labels de I/O + `genome_to_dict(genome, config)` |
| `backend/main.py` | modificar | ação `inspect_creature` → resposta unicast `creature_inspection` |
| `backend/tests/test_genome_inspection.py` | criar | testes da serialização e da ação WebSocket |
| `frontend/src/components/NeuralNetworkViewer.jsx` | criar | grafo SVG da rede |
| `frontend/src/components/InspectorPanel.jsx` | modificar | seção colapsável "Rede neural" |
| `frontend/src/components/SimulationCanvas.jsx` | modificar | enviar `inspect_creature` na seleção; receber/limpar `creature_inspection` |
| `docs/arquitetura.md` | modificar | documentar as duas mensagens novas |

## Passos de implementação

1. **`rtneat_wrapper.py`** — constantes de label (espelham o contrato das linhas 10-27):
   ```python
   INPUT_LABELS = [
       "Visual_Sector_0", "Visual_Sector_1", "Visual_Sector_2", "Visual_Sector_3",
       "Visual_Sector_4", "Visual_Sector_5", "Visual_Sector_6", "Visual_Sector_7",
       "Visual_Sector_8", "Energy_Level", "Age_Degradation", "Hormonal_Level",
       "Biological_Clock", "Load_Sensor", "Kinetic_Linear", "Kinetic_Angular",
   ]
   OUTPUT_LABELS = ["Motor_Forward", "Motor_Torque", "Action_Grab_Drop", "Action_Mate"]
   ```
2. **`genome_to_dict(genome, config)`** no mesmo arquivo:
   ```python
   def genome_to_dict(genome, config):
       """Serializa a topologia do genoma em dict JSON-safe para o inspetor."""
       gc = config.genome_config
       nodes = {}
       for i, key in enumerate(gc.input_keys):        # -1..-16, sem NodeGene proprio
           nodes[str(key)] = {"key": key, "type": "input", "label": INPUT_LABELS[i]}
       for key, node in genome.nodes.items():          # outputs (0..3) e hidden (>=4)
           entry = {
               "key": key,
               "type": "output" if key in gc.output_keys else "hidden",
               "bias": node.bias,
               "activation": node.activation,
           }
           if key in gc.output_keys:
               entry["label"] = OUTPUT_LABELS[gc.output_keys.index(key)]
           nodes[str(key)] = entry
       connections = [
           {"from": in_key, "to": out_key, "weight": conn.weight, "enabled": bool(conn.enabled)}
           for (in_key, out_key), conn in genome.connections.items()
       ]
       return {"key": genome.key, "nodes": nodes, "connections": connections}
   ```
   Nota: `input_keys` mapeia índice i → key `-(i+1)` (validado: `[-1, ..., -16]`), então `INPUT_LABELS[i]` casa com `gc.input_keys[i]`.
3. **`main.py`** — no dispatch do `websocket_endpoint`, novo ramo:
   ```python
   elif action == "inspect_creature":
       cid = msg.get("creature_id")
       creature = next((c for c in engine.creatures if c.id == cid), None)
       payload = {"type": "creature_inspection", "creature_id": cid,
                  "genome": genome_to_dict(creature.genome, creature.config) if creature else None}
       await websocket.send_json(payload)
   ```
   (Resposta unicast ao socket que pediu, não broadcast.)
4. **Testes (`test_genome_inspection.py`):**
   - `genome_to_dict(create_zero_genome(...))`: 20 nós (16 input + 4 output, 0 hidden), 64 conexões, todos os labels presentes, `json.dumps` funciona.
   - Genoma com nó hidden (aplicar `mutate_genome` até surgir, ou construir manualmente): nó aparece com `type: "hidden"`.
   - Ação WebSocket via `TestClient` do FastAPI (padrão do `test_interactive_controls.py`): `inspect_creature` de id válido retorna `creature_inspection` com genome; id inexistente retorna `genome: null`.
5. **`SimulationCanvas.jsx`:**
   - No ponto onde o clique define `selectedIdRef.current` (linha ~320): se id ≠ null, `wsRef.current.send(JSON.stringify({action: "inspect_creature", creature_id: id}))`; se deselecionou, limpar genoma.
   - No `ws.onmessage`: se `data.type === "creature_inspection"`, guardar em `inspectedGenomeRef.current = data` (ref, hot-path). No `inspectInterval` (150 ms): `setInspectedGenome(ref.current && ref.current.creature_id === selectedIdRef.current ? ref.current.genome : null)`.
   - Obs.: o handler atual assume `state_update`; condicionar o caminho existente a `data.type === "state_update"` para não poluir `latestWorldState`.
   - Passar `genome={inspectedGenome}` ao `ControlMenu` → `InspectorPanel`.
6. **`NeuralNetworkViewer.jsx`** — SVG (width 218, altura calculada):
   - 3 colunas: inputs x=12, hidden x=109, outputs x=206. Linhas: inputs em 16 fileiras (espaçamento 13px, ~220px de altura), outputs em 4 fileiras distribuídas na mesma altura, hidden distribuídos verticalmente entre as colunas.
   - Arestas (só `enabled: true`): `<line>` com stroke `HUD.accent` se `weight > 0`, `HUD.warm` se `< 0`; `strokeWidth = 0.4 + 2.0 * |weight| / maxAbsWeight`; `opacity 0.55`.
   - Nós: `<circle r=3.5>` preenchido por tipo (input: `HUD.textDim`, hidden: `HUD.accent`, output: `HUD.warm`), com `<title>` mostrando label/key, bias e activation.
   - Rodapé em texto mono: contagens (`20 nós · 64 conexões`).
7. **`InspectorPanel.jsx`:** nova seção colapsável "Rede neural" (mesmo padrão visual dos grupos do ParamsPanel, classe `.hud-group`), renderizando `<NeuralNetworkViewer genome={genome} />`; enquanto `genome == null` com criatura selecionada, mostrar "carregando rede…" em `HUD.textDim`.
8. **`docs/arquitetura.md`:** documentar `inspect_creature` (cliente→servidor) e `creature_inspection` (servidor→cliente, unicast).

## Contratos técnicos

### Backend (Simulação)
- `genome_to_dict(genome, config) -> dict` e constantes `INPUT_LABELS`/`OUTPUT_LABELS` em `rtneat_wrapper.py`.

### API/WebSocket
- Cliente → Servidor: `{"action": "inspect_creature", "creature_id": 42}`
- Servidor → Cliente (unicast):
  ```json
  {"type": "creature_inspection", "creature_id": 42,
   "genome": {"key": 42,
     "nodes": {"-1": {"key": -1, "type": "input", "label": "Visual_Sector_0"},
                "0": {"key": 0, "type": "output", "label": "Motor_Forward", "bias": 0.49, "activation": "tanh"}},
     "connections": [{"from": -1, "to": 0, "weight": 0.5, "enabled": true}]}}
  ```
  `genome: null` quando a criatura não existe mais.

### Frontend
- `NeuralNetworkViewer({ genome })`; `InspectorPanel` ganha prop `genome`.
- `SimulationCanvas` envia `inspect_creature` a cada nova seleção e roteia mensagens por `data.type`.

## Critérios de aceite

- [ ] Selecionar criatura no canvas exibe o grafo da rede no InspectorPanel (16 inputs, 4 outputs, hidden se houver).
- [ ] Cores/espessuras refletem sinal e magnitude dos pesos; hover mostra bias/activation.
- [ ] Criatura morta/inexistente → `genome: null`, painel não quebra.
- [ ] `state_update` intocado; cliente segue funcionando sem clicar em nada.
- [ ] Testes novos verdes; `pytest backend/tests/` verde; `python -c "import main"` ok.

## Rollback

Reverter a branch BIT-27: deletar `NeuralNetworkViewer.jsx` e `test_genome_inspection.py`; restaurar `rtneat_wrapper.py`, `main.py`, `SimulationCanvas.jsx`, `InspectorPanel.jsx`, `docs/arquitetura.md`.
