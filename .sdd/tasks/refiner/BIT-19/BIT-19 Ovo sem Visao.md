# Spec — BIT-19: Ovo sem Visão

**Linear:** N/A (ver memória `bibitinhos-workflow-sem-linear`)
**Risco:** low
**Camada(s):** Backend (Simulação)

---

## Demanda

Um ovo (`LifeStage.EGG`) não deve possuir linha de visão — a visão é atribuída apenas ao bibite nascido (a partir de JUVENILE). Hoje o brain tick roda `compute_vision()` + `think()` para toda criatura viva, inclusive ovos, e o frontend desenha o cone de visão neles (o payload chega com `vision = [0.0]*9`, e o canvas desenha o cone para qualquer `vision.length > 0`).

## Abordagem técnica

Estender ao sensor/cérebro o padrão de dormência que o estágio EGG já tem para motor e metabolismo (`update()` ignora motor no EGG; `METABOLISM_RATE_BY_STAGE[EGG] = 0.0`): o brain tick em `engine.py` passa a pular criaturas em `LifeStage.EGG` (nem visão, nem `think()`), e `to_dict()` passa a enviar `vision: []` para ovos. O frontend **não precisa de mudança**: o guard existente `creature.vision && creature.vision.length > 0` em `SimulationCanvas.jsx` já pula o desenho do cone quando a lista vem vazia.

Sem dependência de outras tasks. Não conflita com BIT-17 (Ambiente Aquático) nem BIT-18 (Renovação de Comida/Oásis): nenhuma das duas toca o brain tick ou `to_dict()` de `Creature` (BIT-17 adiciona só um comentário em `creature.py`, longe do `to_dict`).

## Arquivos a tocar

| Arquivo (path relativo à raiz do projeto) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/engine.py` | modificar | brain tick pula criaturas em `LifeStage.EGG` |
| `backend/simulation/creature.py` | modificar | `to_dict()` envia `vision: []` quando `life_stage == EGG` |
| `backend/tests/test_sensors.py` | modificar | envelhecer a criatura do teste de tick rate (senão vira vácuo) + teste novo de skip do ovo |
| `backend/tests/test_creature_think.py` | modificar | envelhecer as criaturas do smoke test + testes novos (retomada pós-hatch, payload do ovo) |

## Passos de implementação

> Passos 1 e 2 são independentes; 3 e 4 dependem de 1-2.

1. **`backend/simulation/engine.py`** — no bloco "2. Brain tick" de `step()`, trocar:
   ```python
   for creature in self.creatures:
       if creature.is_alive:
           creature.vision = compute_vision(creature, self)
           creature.think(self)
   ```
   por:
   ```python
   # Ovo e dormante: sem visao e sem think, coerente com motor/metabolismo zero do estagio.
   # A visao so passa a existir no bibite nascido (JUVENILE+), primeiro brain tick pos-hatch.
   for creature in self.creatures:
       if creature.is_alive and creature.life_stage != LifeStage.EGG:
           creature.vision = compute_vision(creature, self)
           creature.think(self)
   ```
   `LifeStage` já é importado em `engine.py` — nenhum import novo.

2. **`backend/simulation/creature.py`** — em `to_dict()`, trocar `"vision": self.vision` por:
   ```python
   "vision": [] if self.life_stage == LifeStage.EGG else self.vision,
   ```
   `self.vision` interno continua `[0.0] * 9` desde o `__init__` (largura fixa dos 16 inputs de `think()` preservada; os outputs cacheados ficam em 0.0 até o primeiro brain tick pós-hatch, o que é inofensivo — o motor já era ignorado no EGG).

3. **`backend/tests/test_sensors.py`**:
   - Em `test_engine_step_only_recomputes_vision_at_brain_tick_rate`, após `make_engine_with_creature()`, envelhecer a criatura para que o teste continue exercitando o caminho real do tick (sem isso a asserção `<= 1` vira vácua com 0 chamadas):
     ```python
     _creature.age = 5.0
     _creature.life_stage = LifeStage.JUVENILE
     ```
   - Teste novo `test_egg_never_computes_vision_via_engine_step(monkeypatch)`: mesmo padrão de `counting_compute_vision` monkeypatchado em `engine_module`, criatura recém-criada (EGG, age 0), rodar `sim.step(1/30.0)` por 6 frames (0.2s — cobre 2 brain ticks) → `call_count["n"] == 0` e `creature.vision == [0.0] * NUM_VISION_SECTORS`.

4. **`backend/tests/test_creature_think.py`**:
   - Em `test_think_runs_for_all_alive_creatures_via_engine_step`, após criar as 5 criaturas, setar `c.age = 5.0` e `c.life_stage = LifeStage.JUVENILE` em cada uma (importar `LifeStage` se ainda não importado) — mantém o propósito original do smoke test.
   - Teste novo `test_egg_does_not_think_via_engine_step()`: criatura EGG com `net.activate` monkeypatchado (ou contador em `think`) → após 6 frames de `engine.step(1/30.0)`, `motor_forward == 0.0`, `motor_torque == 0.0` e o contador em 0.
   - Teste novo `test_vision_resumes_after_hatching()`: criatura com `age = 1.9` (EGG); rodar `engine.step(1/30.0)` por ~30 frames (1s: hatch em age > 2 acontece no meio) → depois do hatch, ao menos um brain tick executou (`creature.life_stage != LifeStage.EGG` e contador de `compute_vision` monkeypatchado `>= 1`).
   - Teste novo `test_to_dict_egg_has_empty_vision()`: criatura EGG → `to_dict()["vision"] == []`; setar `life_stage = LifeStage.JUVENILE` → `to_dict()["vision"]` com 9 floats.

## Contratos técnicos

### Backend (Simulação)
- Nenhuma assinatura muda; nenhuma constante nova.
- Comportamento novo: `engine.step()` não chama `compute_vision`/`think` para criaturas em `LifeStage.EGG`; `Creature.vision` permanece `[0.0] * 9` durante o estágio EGG.

### API/WebSocket
- `state_update.creatures[i].vision`: `[]` quando `life_stage == "EGG"`; 9 floats nos demais estágios. Mudança retrocompatível com o consumidor atual (o canvas guarda por `vision.length > 0`).

### Frontend
- Sem mudança. O guard existente em `SimulationCanvas.jsx` (`creature.vision && creature.vision.length > 0`) deixa de desenhar o cone em ovos automaticamente ao receber `[]`.

## Critérios de aceite

- [ ] Durante o estágio EGG, `compute_vision` e `think` nunca executam para a criatura (verificado via monkeypatch/contador em teste).
- [ ] Após o hatch (age > 2), visão e think retomam no brain tick seguinte, sem intervenção manual.
- [ ] `to_dict()["vision"] == []` para EGG; 9 floats para JUVENILE/ADULT/ELDER.
- [ ] Visual: ovos no canvas sem cone de visão; bibites nascidos com cone normal (verificação manual via `manager.py` → Start Tudo).
- [ ] `pytest backend/tests/` 100% verde (testes novos + ajustes nos dois testes existentes + nenhuma regressão).

## Rollback

Reverter `backend/simulation/engine.py` e `backend/simulation/creature.py` (git checkout); remover os testes novos e restaurar os dois testes ajustados. Sem estado persistente/migração envolvida.
