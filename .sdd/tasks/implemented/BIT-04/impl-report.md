## Status
CONCLUIDO

## Passos executados
1. Li `creature.py`, `engine.py`, `physics.py`, `rtneat_wrapper.py` atuais para confirmar contratos existentes (`Creature(engine, x, y, genome=...)`, `LifeStage`, `organic_crossover`, `mutate_genome`, `space.on_collision`, `COLLISION_CATEGORY_CREATURE`).
2. Validei empiricamente (script descartável fora do escopo do repo, em `AppData/.../scratchpad/test_pymunk_selfcollision.py`) os dois pontos de risco levantados pela task, usando o pymunk 7.2.0 real do venv:
   - `space.on_collision(CREATURE, CREATURE, begin=...)` — colisão de uma categoria com ela mesma dispara `begin` normalmente (shapes trocados/self-collision não é caso especial no pymunk 7.2.0).
   - Criar `Body`/`Shape` novo e chamar `space.add()` dentro do callback `begin`, com `space.step()` do pai em andamento, funciona sem exceção (confirmado por múltiplos steps, contagem de `bodies` crescendo corretamente a cada `add()`).
3. `backend/simulation/creature.py`: adicionado `self.mate_cooldown = 0.0` no `__init__` (junto dos demais atributos de estado) e decremento `self.mate_cooldown = max(0.0, self.mate_cooldown - dt)` no início de `update()`.
4. `backend/simulation/engine.py`: adicionados imports `LifeStage` (de `simulation.creature`) e `organic_crossover`, `mutate_genome` (de `simulation.rtneat_wrapper`); constantes de módulo `REPRODUCTION_ENERGY_COST=30.0`, `REPRODUCTION_COOLDOWN=10.0`, `MIN_ENERGY_TO_MATE=50.0`; segundo handler `_on_creature_creature_collision` registrado via `space.on_collision(COLLISION_CATEGORY_CREATURE, COLLISION_CATEGORY_CREATURE, begin=...)` logo após o handler de comida existente (BIT-03), implementado exatamente como especificado (validações de vida/estágio/cooldown/action_mate/energia, débito de energia, ativação de cooldown, crossover+mutação, instanciação do filho no ponto médio, `add_creature`).
5. Criei `backend/tests/test_reproduction.py` com 7 testes (ver seção de testes abaixo).
6. Rodei `pytest backend/tests/ -v` — 32 passed (25 pré-existentes + 7 novos), 0 falhas.
7. Rodei a suíte `test_reproduction.py` isolada 8 vezes seguidas para checar estabilidade (ver "Problemas encontrados" — genoma zero tem inicialização estocástica de bias, então havia risco de flakiness; testes ajustados ficaram 100% estáveis nas 8 repetições).
8. Smoke test manual (script descartável em scratchpad, fora do repo): `SimulationEngine` real, 20 criaturas ADULT com `action_mate=True` forçado (via stub de `think`) e energia alta, em 5 posições sobrepostas (4 criaturas cada), rodando 120 steps (~4s simulados). Resultado: população cresceu de 20 para 30 já no primeiro `step()` (múltiplas duplas se acasalando simultaneamente, cada uma bloqueada individualmente pelo próprio cooldown) e permaneceu estável em 30 pelos 119 steps restantes — sem exceções, sem crescimento explosivo.

## Arquivos modificados
- `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend\simulation\creature.py` — novo atributo `mate_cooldown` e seu decremento em `update()`.
- `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend\simulation\engine.py` — novos imports, constantes de reprodução, e segundo collision handler `_on_creature_creature_collision` registrado no `__init__`.
- `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend\tests\test_reproduction.py` — criado (novo arquivo), 7 testes cobrindo caso positivo, genoma do filho vem de crossover+mutação (verificado via spy, não por contagem de conexões), 3 casos negativos (action_mate=False, JUVENILE, energia insuficiente), cooldown impedindo reprodução repetida em steps consecutivos, e smoke test de simulação completa.

## Resultado dos testes
```
backend/venv/Scripts/python.exe -m pytest backend/tests/ -v
...
32 passed, 6 warnings in 0.48s
```
Nenhuma falha. Os 6 warnings são `DeprecationWarning` pré-existentes do neat-python (config defaults), não relacionados a esta task.

`test_reproduction.py` isolado, 8 execuções consecutivas: `7 passed` em todas, sem flakiness.

## Problemas encontrados
1. **Divergência descoberta durante os testes (não uma ambiguidade da spec, mas um comportamento do código existente que exigiu ajuste no meu teste, não no código de produção):** `creature.think()` roda a cada brain tick (10 FPS, `BRAIN_TICK_INTERVAL=1/10.0` em `engine.py`) e **sobrescreve** `action_mate` com a saída da rede neural (`outputs[3] > 0.0`). Para o genoma zero (Gen 0), o bias de saída é inicializado aleatoriamente pela config NEAT (`bias_init_type='gaussian'`), então `action_mate` após um `think()` real é ~50/50 True/False — verifiquei isso empiricamente rodando `think()` em 15 genomas zero distintos (8 True, 7 False). Isso tornaria flaky qualquer teste que force `action_mate=True` manualmente e depois rode steps suficientes para disparar um brain tick (>= 0.1s simulados). Resolvi isso nos dois testes multi-step (`test_cooldown_prevents_repeated_reproduction_across_consecutive_steps` e `test_smoke_full_simulation_runs_without_exception_with_reproduction_active`) fazendo stub de `c.think = lambda engine: None` nas criaturas-pai controladas pelo teste, isolando a lógica de reprodução da estocasticidade da rede neural — sem alterar nenhum arquivo de produção. Os testes de um único step (que não atingem o threshold do brain tick) não precisaram desse stub.
2. **Ordem de `arbiter.shapes` não é garantida:** o teste que verifica que `organic_crossover` é chamado com os genomas dos pais corretos inicialmente assumiu a ordem `(c1, c2)`; empiricamente o pymunk entregou `(c2, c1)` nessa execução. Isso é esperado e correto (o handler é simétrico e trata ambas as ordens igualmente), então ajustei a asserção do teste para `set(...) == {c1.genome, c2.genome}` em vez de comparar tupla ordenada.
3. Optei por **não** comparar contagem de conexões do genoma do filho (`len(child.genome.connections)`) contra os pais para provar que veio de crossover+mutação — essa contagem pode mudar com `mutate_genome` (mutações estruturais são possíveis conforme `neat_config.ini`), o que tornaria o teste flaky. Em vez disso, usei `monkeypatch` para espionar `organic_crossover`/`mutate_genome` (já testadas isoladamente em `test_rtneat_wrapper.py`) e confirmar que são chamadas com os genomas dos pais e que o genoma final do filho é exatamente o resultado dessa cadeia — mais robusto e determinístico.

Nenhum bloqueio real: a spec foi seguida à risca (código de produção idêntico ao pseudocódigo fornecido); os ajustes acima foram só no código de teste, para evitar flakiness inerente à natureza estocástica do genoma zero, não uma mudança de comportamento do handler.

## Próximos passos (se BLOQUEADO)
N/A — task concluída.
