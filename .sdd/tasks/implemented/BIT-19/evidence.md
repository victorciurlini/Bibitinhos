# Evidência — BIT-19: Ovo sem Visão

**Data de conclusão:** 2026-07-16

## Demanda atendida

Ovos (`LifeStage.EGG`) deixam de ter linha de visão: o brain tick não roda `compute_vision`
nem `think()` para criaturas em EGG, e `to_dict()` envia `vision: []` nesse estágio. A visão só
passa a existir no bibite nascido (JUVENILE+), no primeiro brain tick pós-hatch. O frontend não
precisou mudar — o guard `vision.length > 0` já pula o desenho do cone com lista vazia.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/engine.py` | modificado | Brain tick pula `LifeStage.EGG` (`is_alive and life_stage != EGG`) |
| `backend/simulation/creature.py` | modificado | `to_dict()["vision"] = [] if EGG else self.vision` |
| `backend/tests/test_sensors.py` | modificado | Criatura do teste de tick rate envelhecida (JUVENILE) + `test_egg_never_computes_vision_via_engine_step` |
| `backend/tests/test_creature_think.py` | modificado | Smoke test envelhecido + `test_egg_does_not_think_via_engine_step`, `test_vision_resumes_after_hatching`, `test_to_dict_egg_has_empty_vision` |

## Resultados dos gates de qualidade

- `import main`: **OK**
- `pytest tests/`: **157 passed** (153 anteriores + 4 novos; só warnings de deprecation pré-existentes do neat-python)
- Frontend: não tocado (mudança retrocompatível; o canvas já ignora `vision` vazio)

## Audit

Revisado diretamente pelo orquestrador (mudança de baixo risco, ~15 linhas, spec-exata): o
diff de `engine.py`/`creature.py` bate exatamente com a spec e a suíte inteira passa. Sem
bloqueantes.

## Como validar

`manager.py` → Start Tudo → abrir o frontend: ovos (recém-nascidos, estágio EGG) aparecem
**sem cone de visão**; ao "chocar" (age > 2 → JUVENILE) o cone surge normalmente no brain tick
seguinte, sem intervenção.
