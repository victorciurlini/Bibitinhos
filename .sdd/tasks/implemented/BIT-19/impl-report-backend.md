# Impl Report — BIT-19: Ovo sem Visão (backend)

## Status
CONCLUÍDO

## Passos executados
1. `engine.py` — no bloco "2. Brain tick" de `step()`, o loop passou a pular criaturas em
   `LifeStage.EGG` (guard `and creature.life_stage != LifeStage.EGG`): ovos não computam `compute_vision`
   nem `think`. `LifeStage` já estava importado; nenhum import novo.
2. `creature.py` — em `to_dict()`, `"vision"` agora envia `[]` quando `life_stage == LifeStage.EGG`,
   caso contrário `self.vision` (os 9 setores). O `self.vision` interno segue `[0.0] * 9` desde o
   `__init__` (largura fixa dos 16 inputs de `think()` preservada).
3. `test_sensors.py` — envelheci a criatura de `test_engine_step_only_recomputes_vision_at_brain_tick_rate`
   (age 5.0 / JUVENILE) para não tornar a asserção `<= 1` vácua; adicionei
   `test_egg_never_computes_vision_via_engine_step` (contador de `compute_vision` monkeypatchado em
   `engine_module`, 6 frames, `call_count == 0` e `creature.vision == [0.0] * NUM_VISION_SECTORS`).
4. `test_creature_think.py` — adicionei `from simulation import engine as engine_module`; envelheci as
   5 criaturas do smoke test (age 5.0 / JUVENILE); 3 testes novos:
   `test_egg_does_not_think_via_engine_step` (contador em `net.activate`, motores em 0.0, segue EGG),
   `test_vision_resumes_after_hatching` (age 1.9 → 30 frames cruzam o hatch em age > 2; contador de
   `compute_vision >= 1` e `life_stage != EGG`), `test_to_dict_egg_has_empty_vision`
   (EGG → `[]`; JUVENILE → 9 floats).

## Arquivos modificados
- `backend/simulation/engine.py` — brain tick pula `LifeStage.EGG` (visão e think dormentes no ovo).
- `backend/simulation/creature.py` — `to_dict()["vision"]` vira `[]` no estágio EGG.
- `backend/tests/test_sensors.py` — envelhece criatura do teste de tick rate + teste novo de skip do ovo.
- `backend/tests/test_creature_think.py` — import de `engine_module`, smoke test envelhecido + 3 testes novos.

## Problemas encontrados / decisões
- Nenhuma divergência com a spec. O `test_vision_resumes_after_hatching` usa atribuição direta de
  `engine_module.compute_vision` com `try/finally` (o teste não recebe fixture `monkeypatch`, conforme
  a assinatura sugerida na spec); efeito equivalente, restauração garantida.
- Confirmado no código atual: o hatch (age > 2 → JUVENILE) acontece em `Creature.update()`, que roda
  APÓS o brain tick no mesmo `step()` — por isso 1.9 + 30 frames (~1s) cruza o limiar com folga.
- Frontend não tocado (guard `vision.length > 0` já existente cobre o payload `[]`), conforme escopo.

## Resultado dos gates
- `import main` → `OK - app importa`.
- `pytest tests/` → **157 passed** (153 pré-existentes + 4 novos), 0 falhas, 6 warnings (deprecations
  pré-existentes do neat-python, sem relação com esta task).
