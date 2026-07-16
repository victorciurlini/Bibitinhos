# Research — Simulação + Frontend (verificação) — BIT-19

> Investigação feita diretamente pelo orquestrador (leitura de código na mesma conversa), sem sub-agente.
> Inclui a verificação de frontend porque a conclusão é "nada a mudar lá" — não justificou relatório próprio.

## Arquivos relevantes

- `backend/simulation/engine.py` — brain tick (bloco 2 de `step()`): `compute_vision` + `think()` para toda criatura viva
- `backend/simulation/creature.py` — `LifeStage` (EGG/JUVENILE/ADULT/ELDER), `self.vision = [0.0]*9` no `__init__`, `think()`, `to_dict()`
- `backend/simulation/sensors.py` — `compute_vision(creature, engine)`, `NUM_VISION_SECTORS = 9`
- `frontend/src/components/SimulationCanvas.jsx` — desenho do cone de visão
- `backend/tests/test_sensors.py` e `backend/tests/test_creature_think.py` — testes afetados

## Conteúdo relevante para a demanda

### Backend

- Brain tick (`engine.py`, a cada `BRAIN_TICK_INTERVAL = 0.1s`):
  ```python
  for creature in self.creatures:
      if creature.is_alive:
          creature.vision = compute_vision(creature, self)
          creature.think(self)
  ```
  **Não filtra por estágio de vida** — ovos enxergam e pensam. `LifeStage` já é importado em `engine.py`.
- `Creature.__init__`: `self.life_stage = LifeStage.EGG`, `self.vision = [0.0] * 9`. Hatch em `update()`: `age > 2` → JUVENILE.
- `Creature.update()` já ignora o motor no estágio EGG ("EGG nao move nem paga custo de motor") e `METABOLISM_RATE_BY_STAGE[EGG] = 0.0` — o precedente de "ovo é dormante" já existe; a visão/cérebro são a lacuna.
- `to_dict()` envia `"vision": self.vision` incondicionalmente.
- `think()` consome `list(self.vision)` + 7 sinais internos (largura fixa de 16 inputs). Se o ovo não pensar, os outputs cacheados ficam em 0.0 (valor do `__init__`) até o primeiro brain tick pós-hatch — inofensivo.

### Frontend (verificado — sem mudança necessária)

- `SimulationCanvas.jsx` desenha o cone apenas se `creature.vision && creature.vision.length > 0`. Hoje ovos chegam com `[0.0]*9` (length 9) e o cone é desenhado — os 9 setores são preenchidos com opacidade fixa, independente dos valores.
- Se o backend enviar `vision: []` para ovos, o guard existente pula o cone automaticamente.

### Testes existentes afetados

- `test_sensors.py::test_engine_step_only_recomputes_vision_at_brain_tick_rate` — a criatura do helper `make_engine_with_creature()` nasce EGG (age 0); com o skip de ovos, `compute_vision` passa a nunca ser chamado e a asserção `<= 1` vira vácua. Precisa envelhecer a criatura para o teste continuar significativo.
- `test_creature_think.py::test_think_runs_for_all_alive_creatures_via_engine_step` — smoke test com 5 criaturas EGG por 20 steps (0.67s simulados, ainda ovos); passa a exercitar só o caminho do skip. Envelhecer as criaturas mantém o propósito original.

## O que precisa ser feito

1. `engine.py`: brain tick pula criaturas em `LifeStage.EGG` (nem `compute_vision`, nem `think`).
2. `creature.py::to_dict()`: `"vision": []` quando `life_stage == EGG` (frontend pula o cone sozinho).
3. Ajustar os dois testes acima + novos testes (ovo não computa visão; visão retoma pós-hatch; payload do ovo com `vision == []`).

## Perguntas em aberto

Nenhuma. Decisão tomada: o ovo também não roda `think()` (cérebro dormante coerente com motor/metabolismo zero do estágio), não apenas a visão.
