# Relatório de implementação — BIT-27: Inspetor de Rede Neural

## Status
CONCLUÍDO

## Passos executados
1. Leitura integral da spec, do estado atual dos arquivos (pós BIT-26) e do padrão de testes do projeto.
2. Verificação do desvio conhecido do venv: `TestClient` de fato não instancia (`TypeError: Client.__init__() got an unexpected keyword argument 'app'` — starlette 0.27 + httpx 0.28.1), inclusive antes de qualquer uso de WebSocket. Adotado o padrão do BIT-26 (teste direto do handler).
3. Backend: labels + `genome_to_dict` no `rtneat_wrapper.py`; helper puro `build_creature_inspection` + ramo `inspect_creature` no dispatch do `main.py`.
4. Testes: `test_genome_inspection.py` com 9 testes (serialização, hidden node, payload da ação).
5. Frontend: `NeuralNetworkViewer.jsx` (SVG), seção colapsável "Rede neural" no `InspectorPanel`, roteamento por `data.type` + envio de `inspect_creature` no `SimulationCanvas`, repasse da prop no `ControlMenu`.
6. Docs: mensagens novas documentadas em `docs/arquitetura.md`; linha de limitações atualizada.
7. Gate de qualidade completo (backend + frontend).

## Arquivos modificados
| Arquivo | Descrição |
|---|---|
| `backend/simulation/rtneat_wrapper.py` | `INPUT_LABELS`/`OUTPUT_LABELS` (espelham a docstring do contrato; comentário avisa que a ordem é parte do contrato estável) + `genome_to_dict(genome, config)` no fim do módulo. Contrato NEAT intocado. |
| `backend/main.py` | Import de `genome_to_dict`; helper puro `build_creature_inspection(engine, creature_id)` (testável direto, não toca o socket); ramo `elif action == "inspect_creature"` no dispatch com `websocket.send_json` (unicast). `state_update`/broadcast intocados. |
| `backend/tests/test_genome_inspection.py` | NOVO — 9 testes: dimensões dos labels vs `genome_config` (sem hardcode de 16/4/20/64), inputs vindos de `input_keys` com label na ordem do contrato, outputs com label/bias/activation, conexões espelhando `genome.connections`, `json.dumps` do dict, hidden node via `mutate_add_node` (determinístico: genoma zero é totalmente conectado), payload da ação com id válido e com id inexistente (`genome: null`). |
| `frontend/src/components/NeuralNetworkViewer.jsx` | NOVO — SVG puro (width 218, altura calculada), 3 colunas (inputs x=12 em fileiras de 13px, hidden x=109, outputs x=206 distribuídos na mesma altura), arestas só `enabled` (acento/ambar por sinal, `strokeWidth = 0.4 + 2.0*|w|/maxAbs`, opacity 0.55), nós `r=3.5` com `<title>` (label/key, bias, activation), rodapé mono com contagens. |
| `frontend/src/components/InspectorPanel.jsx` | Prop nova `genome`; seção colapsável "Rede neural" (classe `.hud-group`, mesmo estilo de cabeçalho do ParamsPanel), aberta por padrão; `genome == null` com criatura selecionada mostra "carregando rede…" em `HUD.textDim`. |
| `frontend/src/components/SimulationCanvas.jsx` | `inspectedGenomeRef` (hot-path) + estado `inspectedGenome`; `ws.onmessage` roteia por `data.type` (`creature_inspection` → ref; `state_update` → `latestWorldState`; outros ignorados); clique de seleção limpa a ref e envia `inspect_creature` uma vez; `inspectInterval` (150 ms) expõe o genoma só se `creature_id` da resposta == seleção corrente; prop `genome` passada ao `ControlMenu`. Convive com o código do BIT-26 (metrics) sem alterá-lo. |
| `frontend/src/components/ControlMenu.jsx` | **Fora da tabela da spec** — repasse mínimo da prop (`genome` na assinatura + `genome={genome}` no `<InspectorPanel>`). Ver "Problemas encontrados". |
| `docs/arquitetura.md` | Linha `inspect_creature` no bloco cliente→servidor + bullet explicando "uma vez por seleção / unicast"; subseção nova "Servidor → cliente (`creature_inspection`, unicast, BIT-27)" com exemplo JSONC (inclui hidden sem label e `genome: null`); limitação "nem inspetor de rede neural" atualizada. |

## Problemas encontrados
1. **ControlMenu.jsx fora da tabela "Arquivos a tocar"** — inconsistência interna da spec: o passo 5 manda "Passar `genome={inspectedGenome}` ao ControlMenu → InspectorPanel", mas o `InspectorPanel` é renderizado DENTRO do `ControlMenu`, então o repasse exige tocar nele. Fiz a mudança mínima possível (2 linhas: assinatura + prop). Alternativa seria bloquear por trivialidade — julguei desproporcional, já que o texto da spec descreve explicitamente esse fluxo.
2. **TestClient não roda no venv** (desvio previsto): confirmado que `TestClient(app)` falha na instanciação com starlette 0.27 + httpx 0.28.1 — não é específico de WebSocket. Solução: a lógica do ramo `inspect_creature` foi extraída para o helper puro `build_creature_inspection` em `main.py` e testada direto (mesmo padrão do BIT-26 em `test_metrics.py`). O ramo do dispatch vira uma linha (`send_json` do helper), não testada por socket real.
3. **Rodapé com acentos ("nós · conexões")** — segui o literal da spec; o restante das strings do HUD é pt-BR sem acentos. Cosmético, fácil de trocar se o revisor preferir consistência com o HUD.
4. Seção "Rede neural" **aberta por padrão** (spec não define): necessário para o critério de aceite "selecionar criatura exibe o grafo" sem clique extra.

## Resultado dos gates
- `venv\Scripts\python.exe -c "import main"` → `OK - app importa`
- `pytest tests/ -q` → **175 passed, 8 warnings** (166 do baseline + 9 novos, nenhum falhando)
- `npm run build` → OK (41 módulos, sem erro)
- `npm run test` (vitest) → 1 passed (suíte existente)

## Pontos de atenção para o revisor
- Contrato NEAT (16 in / 4 out) intocado: só leitura/serialização; nenhuma constante de balanceamento alterada.
- `creature_inspection` é estritamente unicast (`websocket.send_json` no socket que pediu); o broadcast e o `state_update` não mudaram.
- Resposta atrasada de seleção anterior nunca vaza para o painel: o `inspectInterval` compara `creature_id` da resposta com `selectedIdRef.current`.
- Criatura que morre selecionada: o renderLoop já zera `selectedIdRef` (comportamento pré-existente) e o espelho põe `inspectedGenome = null` — painel some sem quebrar.
- Git intocado (sem commit/checkout), conforme instrução do orquestrador.
