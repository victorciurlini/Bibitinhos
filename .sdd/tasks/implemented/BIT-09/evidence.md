# Evidência — BIT-09: Reprodução Assexuada

**Data de conclusão:** 2026-07-14

## Demanda atendida

Criaturas `ADULT` sozinhas (sem parceiro colidindo), com `Action_Mate` ativo e energia acima de um limiar, agora podem se reproduzir sozinhas — clonam o próprio genoma (com mutação), gerando um `EGG`. A reprodução sexuada (BIT-04) permanece com prioridade e comportamento intocado.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/rtneat_wrapper.py` | modificado | Nova função `clone_genome(genome, genome_id, config)` (deepcopy + novo id) |
| `backend/simulation/creature.py` | modificado | `mate_cooldown` renomeado para `reproduction_cooldown`; novo atributo `collided_with_creature_this_frame` (default `False`) |
| `backend/simulation/engine.py` | modificado | Rename de `mate_cooldown` nas 4 ocorrências do handler sexuado; novas constantes `MIN_ENERGY_TO_REPRODUCE_ASEXUALLY`, `ASEXUAL_REPRODUCTION_ENERGY_COST`, `ASEXUAL_REPRODUCTION_COOLDOWN`; novo laço de reprodução assexuada em `step()`; reset de `collided_with_creature_this_frame` no início de cada frame; handler de colisão sexuada agora marca essa flag em ambas as criaturas |
| `backend/tests/test_reproduction.py` | modificado | Rename de `mate_cooldown` → `reproduction_cooldown` (comportamento sexuado inalterado) |
| `backend/tests/test_asexual_reproduction.py` | criado | 9 testes da via assexuada nova |

## Problemas encontrados (divergência da spec)

A spec descrevia o gatilho assexuado como "se não colidiu com ninguém neste frame", mas o bloco de código fornecido na própria spec só checava `reproduction_cooldown` como proxy — insuficiente. Ao rodar a suíte completa, 3 testes existentes do BIT-04 (`test_action_mate_false_prevents_reproduction`, `test_juvenile_prevents_reproduction`, `test_low_energy_prevents_reproduction`) quebraram: quando a via sexuada falha por causa do **parceiro** (ele é `JUVENILE`, tem `action_mate=False` ou energia baixa), a **outra** criatura do par — elegível sozinha — passava a reproduzir assexuadamente no mesmo frame, o que não era o comportamento esperado por esses testes já aprovados.

**Decisão tomada com o developer** (via pergunta direta, não improvisada): adicionar `Creature.collided_with_creature_this_frame`, setada em ambas as criaturas pelo handler de colisão sexuada (independente do resultado — physical contact, não elegibilidade) e resetada a cada `step()` antes da física rodar. O laço assexuado agora pula qualquer criatura que colidiu com outra criatura neste frame, mesmo que essa colisão não tenha gerado filho. Isso preserva os 3 testes do BIT-04 sem alteração de expectativa, e um teste novo (`test_no_asexual_fallback_when_partner_collision_fails_sexual_conditions`) cobre esse caso especificamente.

## Resultados dos gates de qualidade

- `import main`: OK
- `pytest backend/tests/`: **72 passed**, 0 failed (63 anteriores + 9 novos de `test_asexual_reproduction.py`)
- Frontend não tocado (N/A)
- Backend real subido via uvicorn (porta isolada 8097), ~8s sem traceback, encerrado ao final

## Como validar

1. `cd backend && venv\Scripts\python.exe -m pytest tests/test_asexual_reproduction.py -v` — confirma a via assexuada isolada.
2. `pytest tests/test_reproduction.py -v` — confirma que a via sexuada (BIT-04) não regrediu.
3. Via `manager.py` → Start Tudo → observar por alguns minutos: criaturas `ADULT` isoladas com energia alta devem eventualmente gerar `EGG` sozinhas (mais raro que a via sexuada, pelo limiar de energia mais alto e cooldown mais longo).
