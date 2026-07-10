# Spec — BIT-05: Metabolismo e Longevidade

**Linear:** N/A
**Risco:** low
**Camada(s):** Backend (Simulação)

---

## Demanda

Hoje "comer" (BIT-03) só reabastece energia, mas a única fonte de gasto de energia é o custo de motor (`motor_cost`, proporcional à saída da rede NEAT) — uma criatura cuja rede converge para saídas próximas de zero pode nunca perder energia e é, na prática, imortal sem nunca comer. Não existe pressão evolutiva real para aprender a comer, nem qualquer noção de envelhecimento/degradação natural.

Introduzir **metabolismo passivo**: toda criatura viva (fora do estágio `EGG`) gasta energia por segundo só por estar viva, com taxa crescente por `LifeStage` (`JUVENILE` < `ADULT` < `ELDER`). Isso torna comer uma necessidade real de sobrevivência — criaturas que não aprendem a se alimentar morrem de fome mesmo paradas — e cria "longevidade" como métrica emergente: comer bem literalmente estende quanto tempo uma criatura sobrevive. `ELDER` tem a maior taxa (degradação acelerada por idade avançada), criando turnover populacional natural mesmo para criaturas bem alimentadas.

## Abordagem técnica

Somar um custo metabólico fixo por `LifeStage` (`METABOLISM_RATE_BY_STAGE`, energia/segundo) ao `motor_cost` já existente em `Creature.update()`, mudança isolada em `creature.py`. Não depende de nenhuma outra `BIT-XX` além do que já está em `develop` (BIT-00 a BIT-04). O input `Energy_Level` que a rede NEAT já recebe em `think()` (BIT-02) reflete `self.energy/self.max_energy`, então o cérebro já "sente" o dreno mais rápido automaticamente — nenhuma mudança no contrato de I/O do NEAT é necessária.

## Arquivos a tocar

| Arquivo (path relativo à raiz do projeto) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/creature.py` | modificar | Nova constante `METABOLISM_RATE_BY_STAGE`; `update()` soma o custo metabólico do estágio atual ao custo de energia por frame |
| `backend/tests/test_creature_think.py` | modificar | Corrigir `test_update_energy_cost_proportional_to_motor_magnitude` (assumia `quiet_cost == 0.0` para ADULT parado) |
| `backend/tests/test_reproduction.py` | modificar | Corrigir 4 asserções de energia exata que assumiam custo zero para ADULT/JUVENILE parados num único step |
| `backend/tests/test_metabolism.py` | criar | Testes do metabolismo passivo: taxa por estágio, EGG sem custo, comer compensa o dreno |

## Passos de implementação

> Passo 1 é a mudança de produção; passos 2-3 corrigem regressões que o passo 1 introduz nos testes existentes; passo 4 é independente (pode ser feito em paralelo ao 2-3, mas depende do passo 1 já estar implementado para importar a constante).

1. **`backend/simulation/creature.py`** — adicionar a constante no topo do módulo (junto de `AGE_DEGRADATION_SCALE` etc.) e ajustar `update()`:
   ```python
   METABOLISM_RATE_BY_STAGE = {
       LifeStage.EGG: 0.0,
       LifeStage.JUVENILE: 0.3,
       LifeStage.ADULT: 0.8,
       LifeStage.ELDER: 2.0,
   }
   ```
   Em `update(self, dt, engine)`, trocar o bloco final:
   ```python
   motor_cost = 0.0
   if self.life_stage != LifeStage.EGG:
       forward_impulse = (self.motor_forward * self.speed * dt, 0)
       self.body.apply_impulse_at_local_point(forward_impulse, (0, 0))
       self.body.torque = self.motor_torque * MOTOR_TORQUE_SCALE
       motor_cost = abs(self.motor_forward) * self.speed * 0.1 + abs(self.motor_torque) * self.size * 0.05

   metabolism_cost = METABOLISM_RATE_BY_STAGE[self.life_stage]
   self.energy -= dt * (motor_cost + metabolism_cost)
   if self.energy <= 0:
       self.is_alive = False
   ```
   `LifeStage.EGG` mantém custo total zero (motor E metabolismo), preservando o comportamento já coberto por `test_egg_pays_no_motor_cost_even_with_strong_motor_output` (BIT-02) — não precisa alterar esse teste.

   Valores propostos (ajustáveis, não são um valor "mágico" imutável — documentar no código que são tunáveis): com `max_energy=100.0` e essas taxas, uma criatura que nunca come nem se move sobrevive ~2.4 energia no fim do `JUVENILE` (8s×0.3) + ~16 energia no fim do `ADULT` (20s×0.8) ≈ 18.4 gastos ao entrar em `ELDER` aos 30s de idade; a partir daí, a 2.0/s, os ~81.6 restantes duram mais ~40s — morte natural por volta de 70s de idade se nunca comer, bem antes disso se também gastar energia se movendo. Comer (20 energia por `Food` default) estende isso diretamente.

2. **`backend/tests/test_creature_think.py`** — em `test_update_energy_cost_proportional_to_motor_magnitude`, a criatura `quiet` (ADULT, motor zerado) agora tem custo igual ao metabolismo do estágio, não zero. Importar `METABOLISM_RATE_BY_STAGE` e `LifeStage` de `simulation.creature` e trocar:
   ```python
   assert quiet_cost == 0.0
   ```
   por:
   ```python
   import pytest
   ...
   expected_quiet_cost = (1 / 30.0) * METABOLISM_RATE_BY_STAGE[LifeStage.ADULT]
   assert quiet_cost == pytest.approx(expected_quiet_cost)
   ```
   O restante do teste (comparação `active_cost > quiet_cost`) continua válido sem alteração.

3. **`backend/tests/test_reproduction.py`** — as 4 asserções abaixo precisam incorporar o metabolismo de 1 step (`dt = 1/30.0`) do(s) estágio(s) relevante(s). Importar `METABOLISM_RATE_BY_STAGE` de `simulation.creature` e usar `pytest.approx`:
   - `test_adult_pair_with_action_mate_reproduces_on_collision`:
     ```python
     dt = 1 / 30.0
     expected = 100.0 - REPRODUCTION_ENERGY_COST - dt * METABOLISM_RATE_BY_STAGE[LifeStage.ADULT]
     assert c1.energy == pytest.approx(expected)
     assert c2.energy == pytest.approx(expected)
     ```
   - `test_action_mate_false_prevents_reproduction`: ambas ficam `ADULT` sem reproduzir; trocar `== 100.0` por `== pytest.approx(100.0 - dt * METABOLISM_RATE_BY_STAGE[LifeStage.ADULT])` para `c1` e `c2`.
   - `test_juvenile_prevents_reproduction`: `c1` é `ADULT`, `c2` é `JUVENILE` — cada um usa a taxa do seu próprio estágio no `pytest.approx`.
   - `test_low_energy_prevents_reproduction`: `c1` é `ADULT` com energia `100.0` → `pytest.approx(100.0 - dt * METABOLISM_RATE_BY_STAGE[LifeStage.ADULT])`; `c2` é `ADULT` com energia `MIN_ENERGY_TO_MATE - 1.0` → `pytest.approx(MIN_ENERGY_TO_MATE - 1.0 - dt * METABOLISM_RATE_BY_STAGE[LifeStage.ADULT])`.

   `test_child_genome_comes_from_crossover_and_mutation_not_zero_genome`, `test_cooldown_prevents_repeated_reproduction_across_consecutive_steps` e o smoke test não fazem asserção exata de energia — não precisam de alteração.

4. **`backend/tests/test_feeding.py`**: **não precisa de alteração** — todas as `Creature` desses testes ficam em `LifeStage.EGG` (idade 0, um único step não cruza o limiar de 2s), e `EGG` mantém custo zero. Confirmar isso ao rodar a suíte (não deve haver falha nesse arquivo); se por algum motivo houver, é sinal de que a premissa acima estava errada e precisa investigação, não um ajuste cego de asserção.

5. **`backend/tests/test_metabolism.py`** (criar) — testes mínimos:
   - Criatura `JUVENILE`/`ADULT`/`ELDER` com motor zerado perde energia proporcional à taxa do estágio num `update()` (`pytest.approx`).
   - Criatura `EGG` com motor zerado não perde energia nenhuma.
   - Taxas são estritamente crescentes: `METABOLISM_RATE_BY_STAGE[JUVENILE] < METABOLISM_RATE_BY_STAGE[ADULT] < METABOLISM_RATE_BY_STAGE[ELDER]`.
   - Integração: uma criatura `ADULT` parada (sem comer) ao longo de vários `update()` chega a `is_alive=False` eventualmente só por metabolismo (ex.: simular `dt` grande o suficiente ou muitos steps pequenos até `energy<=0`).
   - Integração inversa: uma criatura `ADULT` parada que come periodicamente (chamar o handler de colisão de BIT-03 manualmente ou via `engine.step()` com `Food` sobreposta) sobrevive além do tempo que sobreviveria só com metabolismo — confirma que comer estende a longevidade.

6. **Rodar a suíte completa** (`backend\venv\Scripts\python.exe -m pytest backend/tests/ -v`) e confirmar 100% verde (hoje: 41 testes, incluindo BIT-06 Oásis/Jardim do Éden já mergeada; após esta task: 41 + novos de `test_metabolism.py`, nenhum dos 41 quebrado após os ajustes dos passos 2-3).

## Contratos técnicos

### Backend (Simulação)
- Nova constante em `creature.py`: `METABOLISM_RATE_BY_STAGE: dict[LifeStage, float]` — `{EGG: 0.0, JUVENILE: 0.3, ADULT: 0.8, ELDER: 2.0}` (energia/segundo).
- `Creature.update(dt, engine)`: comportamento estendido — custo de energia por frame passa a ser `dt * (motor_cost + metabolism_cost)` em vez de só `dt * motor_cost`. Nenhuma mudança de assinatura pública.
- Nenhuma mudança em `SimulationEngine`, `Food`, `rtneat_wrapper.py`, `neat_config.ini`, protocolo WebSocket ou frontend.

## Critérios de aceite

- [ ] Criatura `JUVENILE`/`ADULT`/`ELDER` parada (motor zerado) perde energia por segundo de acordo com `METABOLISM_RATE_BY_STAGE` do seu estágio.
- [ ] Criatura `EGG` não perde energia (nem motor, nem metabolismo) — comportamento herdado de BIT-02 preservado.
- [ ] Taxas de metabolismo são estritamente crescentes por estágio: `ELDER > ADULT > JUVENILE > EGG (0.0)`.
- [ ] Uma criatura que nunca come eventualmente morre só de metabolismo passivo, mesmo sem gastar energia com motor.
- [ ] Uma criatura que come periodicamente sobrevive mais tempo do que sobreviveria só com metabolismo passivo (comer aumenta longevidade, de forma mensurável em teste).
- [ ] `pytest backend/tests/test_metabolism.py` 100% verde.
- [ ] Nenhuma regressão: suíte completa (`backend/tests/`) 100% verde, incluindo as 5 asserções corrigidas em `test_creature_think.py`/`test_reproduction.py`.

## Rollback

Reverter `METABOLISM_RATE_BY_STAGE` e a linha `metabolism_cost = ...`/`self.energy -= dt * (motor_cost + metabolism_cost)` em `creature.py` para `self.energy -= dt * motor_cost`; reverter as asserções alteradas em `test_creature_think.py`/`test_reproduction.py` de volta para `== 0.0`/`== 100.0`/etc.; deletar `backend/tests/test_metabolism.py`. Sem estado persistente/migração envolvida.
