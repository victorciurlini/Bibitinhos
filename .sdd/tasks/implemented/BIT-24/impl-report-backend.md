# Impl Report — BIT-24 (Backend): Controles Interativos da Simulação

## Status
CONCLUÍDO

## Escopo executado
Somente os passos de backend da spec: **1, 2, 3, 4 e 9** + a seção de contrato WebSocket em
`docs/arquitetura.md`. Frontend (passos 5–8) não tocado, conforme instruído.

## Passos executados
1. **creature.py — identidade e inspeção**: `self.id = self.genome.key` atribuído no `__init__`
   logo após a criação do genoma; `to_dict()` ganhou `id, max_energy, age, reproduction_cooldown,
   motor_forward, motor_torque, action_mate, action_grab_drop` (todos os campos antigos mantidos).
2. **engine.py — controle de tempo**: constante de módulo `ALLOWED_SPEEDS = (0.5, 1.0, 2.0, 4.0)`;
   atributos `self.paused = False` e `self.speed = 1.0` no `__init__`; método `set_time_control`
   (speed inválido = no-op). `get_state()` ganhou `paused` e `speed` no topo do dict.
3. **engine.py — arrasto**: atributos `_held_creature`/`_drag_target`; métodos `get_creature_by_id`,
   `start_drag`, `drag_to` (clampa aos limites do mundo), `end_drag`. Re-pin no `step()`
   imediatamente antes de `self.physics.step(dt)` (solta se a criatura morreu).
4. **main.py — loop + dispatch**: `simulation_loop` com acumulador de velocidade por substeps de
   `dt` fixo (1/30); pausado não roda step mas o broadcast continua. `websocket_endpoint` passou a
   fazer parse JSON + dispatch (`set_time_control`, `drag` com fases start/move/end), ignorando
   mensagens malformadas/ações desconhecidas; `WebSocketDisconnect` chama `engine.end_drag()`.
9. **test_interactive_controls.py**: criado, 15 testes cobrindo os 8 cenários da spec.

## Arquivos modificados
- `backend/simulation/creature.py` — `self.id = self.genome.key` no `__init__`; novos campos em `to_dict()`.
- `backend/simulation/engine.py` — `ALLOWED_SPEEDS`; estado de tempo/drag no `__init__`; métodos
  `set_time_control`, `get_creature_by_id`, `start_drag`, `drag_to`, `end_drag`; re-pin no `step()`;
  `paused`/`speed` no `get_state()`.
- `backend/main.py` — `simulation_loop` com acumulador de substeps; `websocket_endpoint` com parse
  e dispatch de comandos; `engine.end_drag()` no disconnect. Engine movido para antes do endpoint
  (o handler referencia `engine`).
- `backend/tests/test_interactive_controls.py` — novo; 15 testes (import de `ALLOWED_SPEEDS`, sem hardcode).
- `docs/arquitetura.md` — seção "Contrato WebSocket" ampliada: state_update com campos novos
  (`paused`/`speed` no topo + campos por criatura) e bloco novo "Cliente → servidor" com os comandos.

## Problemas / decisões
- **Mapa é 1400, não 2000.** A spec (passo 9, cenário 5) exemplifica `(-50, 3000) → (0, 2000)`
  assumindo mapa 2000; o `physics.py` atual usa `map_width = map_height = 1400` (BIT-22). Seguindo
  a convenção do projeto (testes importam, nunca hardcodam), o teste de clamp usa `engine.height`/
  `engine.width` em vez de literais — passa independente do tamanho do mapa. Não alterei os literais
  "2000×2000" já existentes no corpo de `docs/arquitetura.md` (fora do meu escopo; drift pré-existente).
- **Cenário de morte durante o drag**: a spec descreve o re-pin no topo do `step()` que solta a
  criatura morta. O teste marca `is_alive = False` e chama `engine.step(1/30)`, verificando
  `_held_creature is None` — consistente com o re-pin implementado antes de `physics.step`.
- **Ordem em main.py**: como o `websocket_endpoint` agora referencia `engine`, movi a criação do
  `engine` (e o import do SimulationEngine/Creature) para antes da definição do endpoint. O
  `startup_event` e o resto do fluxo permanecem intactos.

## Resultado dos gates
- `import main` → `OK import`.
- `pytest tests/ -v` → **142 passed, 6 warnings** (warnings são deprecations pré-existentes do
  neat-python, não relacionadas a esta task).
- `test_interactive_controls.py` isolado → **15 passed**.
