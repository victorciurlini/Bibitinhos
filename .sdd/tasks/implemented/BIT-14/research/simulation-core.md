## Contexto

Feedback direto do developer após validar visualmente o resultado do BIT-12 (render dos cones) + BIT-13 (sinal ponderado): a visão estava "muito grande" (raio) e "muito ampla" (cobria os 360° ao redor da criatura) — pediu um cone frontal, na frente da "cabeça" do bibite, não um leque completo.

## Parâmetros confirmados com o developer (AskUserQuestion)

- Ângulo do cone (FOV): **120°** (recomendado — cobre "canto de olho" dos dois lados sem ser omnidirecional).
- Raio de alcance: **80** (reduzido de 200 — developer escolheu a opção mais agressiva das 3 apresentadas, ~8x o raio do corpo da criatura em vez de ~20x).

## Arquivos relevantes

- `backend/simulation/sensors.py` — `compute_vision()`, geometria do sensor (já alterada no BIT-13 para sinal com tipo, mas ainda cobria 360°)
- `backend/simulation/rtneat_wrapper.py` — docstring do contrato de I/O (`Visual_Sectors`)
- `backend/simulation/engine.py` — `get_state()` já expõe `vision_radius` (BIT-12); precisa expor também o novo FOV
- `frontend/src/components/SimulationCanvas.jsx` — desenho do leque (BIT-12), assumia 360° completo
- `backend/tests/test_sensors.py` — testes de geometria (BIT-13), vários assumiam setor 0 = "para frente" e testavam detecção atrás da criatura

## O que precisa ser feito

1. `sensors.py`: restringir a detecção a uma janela angular de `VISION_FOV_DEGREES` (120°) centrada no eixo frontal da criatura; fora dela, nenhum setor ativa, independente de distância. Setor do meio (índice `NUM_VISION_SECTORS // 2` = 4) passa a ser o "para frente" (antes era o índice 0). `VISION_RADIUS` reduzido de 200 para 80.
2. `rtneat_wrapper.py`: atualizar a descrição de `Visual_Sectors` no contrato de I/O documentado (índice central, ângulo do cone, exclusão total do que está atrás).
3. `engine.py`: expor `vision_fov_degrees` em `get_state()`, ao lado de `vision_radius` já existente (mesmo raciocínio anti-número-mágico do BIT-12).
4. `SimulationCanvas.jsx`: desenhar o leque de setores só dentro do cone frontal de `vision_fov_degrees`, não mais 360° — usa o mesmo `data.vision_radius` (agora 80, propagado automaticamente sem mudança de código) mais o novo `data.vision_fov_degrees`.
5. `test_sensors.py`: setor "para frente" agora é o do meio (índice 4, não 0); testes que colocavam vizinho atrás da criatura para validar detecção passam a validar o oposto (fora do cone = sem sinal); novo teste de borda do FOV (logo fora de ±60°).

## Validação

Suíte completa (`pytest backend/tests/`) rodada após as mudanças: 63 passed. `npm run build`/`npm run test` no frontend: OK. Backend real subido via uvicorn (porta isolada) por ~8s sem traceback.
