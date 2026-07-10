## Veredito
APROVADO COM RESSALVAS

Nenhum bug bloqueante de correção encontrado (ordem de inicialização, tamanho do vetor de inputs, aplicação de impulso/torque, checagem de `EGG`, `next_genome_id()` e testes — todos corretos e batendo com a spec). Há uma inconsistência de lógica (criaturas em `EGG` pagam custo de energia por um motor que não é aplicado fisicamente) herdada literalmente do pseudocódigo da spec, que recomendo confirmar como intencional antes do merge — não é um bug introduzido pelo implementador, mas é um comportamento estranho o suficiente para merecer uma decisão consciente.

## Critérios de aceite — checklist

- [x] **Criaturas se movem de forma não-determinística (saída da rede, não mais impulso fixo)** — atendido por design: `create_zero_genome`→`configure_new()` usa `weight_init_stdev=1.0`, ou seja "genoma zero" não é peso-zero, é um genoma novo com pesos gaussianos aleatórios por criatura; combinado com `self.body.angle` aleatório e visão variável, a saída de `net.activate()` diverge entre criaturas. Não executei a simulação completa via `manager.py`/frontend (fora do escopo de uma revisão só-leitura), então a validação visual em si não foi confirmada ao vivo, mas a lógica implica o comportamento esperado.
- [x] **`net.activate()` roda sem exceção para todas as criaturas vivas a cada brain tick, incluindo Gen 0** — confirmado por `test_think_runs_without_exception_on_fresh_creature` e `test_think_runs_for_all_alive_creatures_via_engine_step` (20 steps, 5 criaturas, via `engine.step()` real). Verifiquei também que `list(self.vision)` sempre tem tamanho 9 (`sensors.compute_vision` sempre retorna `[0.0]*NUM_VISION_SECTORS` com atribuições por índice, nunca append/resize) + 7 sensores adicionais = 16, batendo exatamente com `num_inputs=16` do `neat_config.ini`.
- [x] **`motor_forward`/`motor_torque` no range aproximado `[-1,1]`** — confirmado por `test_think_outputs_motor_within_tanh_range`, consistente com `activation_default=tanh` do config para Gen 0. Ressalva de robustez (não bloqueante): `activation_options = tanh sigmoid relu` no config permite mutação futura de um node para `relu`, que é ilimitado — isso quebraria a garantia de range em gerações futuras (fora do escopo de BIT-02, que não dispara mutação).
- [x] **Custo de energia por frame é proporcional à magnitude do motor, não mais constante fixo** — implementado (`motor_cost = abs(motor_forward)*speed*0.1 + abs(motor_torque)*size*0.05`). Ver bug #1 abaixo sobre aplicação também a criaturas em `EGG`.
- [x] **`action_grab_drop`/`action_mate` existem como atributos booleanos** — confirmado (`outputs[i] > 0.0` produz `bool` nativo do Python), testado em `test_think_action_flags_are_bool`.
- [x] **`pytest backend/tests/test_creature_think.py` 100% verde** — confirmado, rodei eu mesmo (ver seção abaixo).
- [x] **Nenhuma regressão em `pytest backend/tests/`** — confirmado, 20/20 passed.

## Resultado real do pytest

Comando: `backend\venv\Scripts\python.exe -m pytest backend/tests/ -v` (a partir da raiz)

```
collected 20 items

backend/tests/test_creature_think.py::test_think_runs_without_exception_on_fresh_creature PASSED
backend/tests/test_creature_think.py::test_think_outputs_motor_within_tanh_range PASSED
backend/tests/test_creature_think.py::test_think_action_flags_are_bool PASSED
backend/tests/test_creature_think.py::test_update_after_think_never_increases_energy PASSED
backend/tests/test_creature_think.py::test_update_energy_cost_proportional_to_motor_magnitude PASSED
backend/tests/test_creature_think.py::test_think_runs_for_all_alive_creatures_via_engine_step PASSED
backend/tests/test_rtneat_wrapper.py::test_load_neat_config_parses_topology PASSED
backend/tests/test_rtneat_wrapper.py::test_load_neat_config_is_cached PASSED
backend/tests/test_rtneat_wrapper.py::test_create_zero_genome_is_fully_connected PASSED
backend/tests/test_rtneat_wrapper.py::test_network_activates_with_16_inputs_returns_4_outputs PASSED
backend/tests/test_rtneat_wrapper.py::test_network_activate_wrong_input_size_raises PASSED
backend/tests/test_rtneat_wrapper.py::test_organic_crossover_with_no_fitness_does_not_raise PASSED
backend/tests/test_rtneat_wrapper.py::test_mutate_genome_runs_without_error PASSED
backend/tests/test_sensors.py::test_no_neighbors_returns_all_zero PASSED
backend/tests/test_sensors.py::test_food_directly_ahead_activates_cone_zero PASSED
backend/tests/test_sensors.py::test_creature_directly_behind_activates_opposite_cone PASSED
backend/tests/test_sensors.py::test_neighbor_outside_radius_does_not_activate_any_cone PASSED
backend/tests/test_sensors.py::test_creature_never_detects_itself PASSED
backend/tests/test_sensors.py::test_engine_step_only_recomputes_vision_at_brain_tick_rate PASSED
backend/tests/test_simulation.py::test_simulation_basic PASSED

======================= 20 passed, 6 warnings in 0.42s ========================
```

Bate exatamente com o relatado no `impl-report.md` (20 passed, mesmos 6 warnings de `DeprecationWarning` do neat-python, pré-existentes e não relacionados à mudança).

## Bugs / problemas encontrados

### 1. [Severidade média] Criaturas em `EGG` pagam custo de energia de um motor que nunca é aplicado fisicamente

Em `creature.py::update()`:

```python
if self.life_stage != LifeStage.EGG:
    forward_impulse = (self.motor_forward * self.speed * dt, 0)
    self.body.apply_impulse_at_local_point(forward_impulse, (0, 0))
    self.body.torque = self.motor_torque * MOTOR_TORQUE_SCALE

# fora do if — roda para TODAS as criaturas, inclusive EGG
motor_cost = abs(self.motor_forward) * self.speed * 0.1 + abs(self.motor_torque) * self.size * 0.05
self.energy -= dt * motor_cost
```

`think()` é chamado no brain tick para **todas** as criaturas vivas (`engine.py`, bloco do brain tick não filtra por `life_stage`), então uma criatura em `EGG` recebe `motor_forward`/`motor_torque` reais e não-triviais da rede (dependendo do genoma, podem estar longe de zero). O bloco de movimento é corretamente pulado para `EGG` (impulso/torque não aplicados — nenhuma criatura em ovo se move fisicamente, o que atende ao critério "criaturas em EGG não devem mover"), mas o cálculo de `motor_cost` logo abaixo **não** está dentro do mesmo `if`, então o ovo perde energia proporcional a uma saída de motor que não teve nenhum efeito físico. Cenário concreto: uma criatura recém-nascida (`EGG`, idade 0-2) com um genoma cujo output de `Motor_Forward`/`Motor_Torque` seja próximo de `±1.0` (perfeitamente possível mesmo com pesos gaussianos aleatórios de `create_zero_genome`) perde energia a cada frame de física por "tentar se mover" sem nunca de fato se mover — isso acelera a morte de ovos por inanição de forma não intencional e não documentada.

Este trecho é uma cópia literal do pseudocódigo do passo 4 da spec (`spec.md` linhas 96-116), então não é um desvio do implementador — ele seguiu a spec à risca. Ainda assim, sinalizo porque (a) o comentário acima da linha ("Consumo de energia proporcional à magnitude real do motor") sugere que a intenção é vincular custo a efeito físico real, e (b) nenhum teste em `test_creature_think.py` cobre especificamente o caso `EGG` (todos os testes de custo de energia forçam `life_stage = ADULT` antes de chamar `update()`, evitando justamente o branch onde esse comportamento aparece). Recomendo decisão consciente do time (mover o `motor_cost` para dentro do `if`, ou aceitar como "custo metabólico de tentar se mover mesmo em ovo") antes do merge — não é um crash nem uma quebra de contrato, mas afeta diretamente a sobrevivência de Gen 0/ovos em produção.

### 2. [Severidade baixa] Clamp inferior morto em `Kinetic_Feedback` linear

```python
max(-1.0, min(1.0, self.body.velocity.length / KINETIC_LINEAR_NORM)),        # Kinetic_Feedback (linear)
```

`pymunk.Vec2d.length` é sempre `>= 0` (é magnitude, não velocidade com sinal), então o `max(-1.0, ...)` nunca é exercitado — o valor está sempre em `[0, 1]`, nunca `[-1, 0)`. Não é um bug funcional (não causa comportamento incorreto), só um branch morto que pode confundir leitura futura do código. Também é cópia literal da spec (linha 83 do `spec.md`), não desvio do implementador.

### 3. [Severidade baixa / não-bloqueante] Docstring de `rtneat_wrapper.py` desatualizada quanto à codificação da visão

O docstring do módulo (linha 11) diz: `Visual_Sectors (9 cones de visao; Gen 0: 3 ativos, resto -1.0)`, mas a implementação real (`sensors.compute_vision`, de BIT-01, não tocada por este diff) usa `0.0` para setores inativos e `1.0` para ativos — nunca `-1.0`. Isso é herdado de uma task anterior (BIT-00/BIT-01), não introduzido por BIT-02, mas como BIT-02 é quem efetivamente consome esse contrato em `think()`, vale uma limpeza de doc numa task futura para evitar confusão de quem for debugar os inputs da rede.

### Não encontrei

- Nenhum problema de ordem de inicialização em `__init__`: `self.energy`, `self.max_energy`, `self.speed`, `self.size`, `self.vision` são todos atribuídos **antes** do bloco de criação de `config`/`genome`/`net`, e `think()` só é chamado depois via `engine.step()` (nunca dentro do próprio `__init__`), então todos os atributos que `think()` usa já existem na primeira chamada.
- Nenhum caso em que `self.vision` teria tamanho diferente de 9 (`compute_vision` sempre devolve lista de tamanho fixo `NUM_VISION_SECTORS=9`, atribuição por índice, nunca resize).
- `next_genome_id()` começa em 1 corretamente (`_next_genome_id=0` no `__init__`, incrementa antes de retornar).
- Impulso/torque aplicados corretamente: impulso local no eixo x (`forward_impulse`) via `apply_impulse_at_local_point`, torque escalar direto em `body.torque`, ambos usando os outputs cacheados de `think()`, reaplicados a cada frame de física (30 FPS) como pede a spec.
- `energy <= 0` mata a criatura corretamente (`is_alive=False`); criaturas mortas são filtradas do brain tick no frame seguinte (`if creature.is_alive:`) antes de serem removidas de `self.creatures` no final do mesmo `step()`, então não há risco de `think()` rodar com energia negativa "vazando" para o próximo tick.
- Assinatura de `Creature.__init__` retrocompatível: todos os chamadores existentes (`main.py:75`, `engine.py:74`, testes) continuam funcionando sem alteração, `genome=None` é o default.

## Observações de qualidade (não bloqueantes)

- `test_update_energy_cost_proportional_to_motor_magnitude` testa só "custo com motor em 1.0 > custo com motor em 0.0", não testa proporcionalidade real (ex.: motor em 0.5 custar a metade do motor em 1.0). A spec permite explicitamente essa versão mais fraca ("ou apenas checar que energia nunca aumenta"), então está dentro do combinado — mas é uma cobertura mais fraca do que o nome do teste sugere.
- `test_think_runs_for_all_alive_creatures_via_engine_step` não faz nenhum `assert` sobre o resultado (só confirma ausência de exceção ao longo de 20 steps). Cumpre o critério de aceite literal ("roda sem exceção"), mas é o tipo de teste que só pega regressões grosseiras (crash), não regressões de comportamento.
- Nenhum teste cobre o cenário de criatura em `EGG` chamando `think()`+`update()` (ver bug #1) — teria pego a inconsistência de custo de energia se existisse.
