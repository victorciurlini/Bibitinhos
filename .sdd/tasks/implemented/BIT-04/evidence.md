# Evidência — BIT-04: Reprodução sexuada (colisão de ADULTs com Action_Mate)

**Data de conclusão:** 2026-07-10
**Linear:** N/A

## Demanda atendida

Registrado um segundo collision handler Pymunk (criatura×criatura): quando duas criaturas `ADULT` colidem fisicamente, ambas com `action_mate=True` (saída real do cérebro NEAT), sem cooldown ativo e com energia mínima, nasce uma nova `Creature` (`EGG`) via `organic_crossover` + `mutate_genome` dos genomas dos pais. É o único caminho de criação de novas criaturas além do "Jardim do Éden" (respawn em população zero).

Implementado via sub-agente implementador + sub-agente revisor independente.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/creature.py` | modificado | `self.mate_cooldown = 0.0` no `__init__`; decremento em `update()` |
| `backend/simulation/engine.py` | modificado | Segundo `space.on_collision(CREATURE, CREATURE, begin=_on_creature_creature_collision)`: valida ADULT/cooldown/action_mate/energia mínima, debita `REPRODUCTION_ENERGY_COST` dos pais, aplica `REPRODUCTION_COOLDOWN`, gera filho via crossover+mutação no ponto médio |
| `backend/tests/test_reproduction.py` | criado | 7 testes: caso positivo completo, genoma do filho vem de crossover+mutação (via spy), 3 casos negativos (action_mate=False / JUVENILE / energia insuficiente), cooldown bloqueando reprodução repetida, smoke test |

## Pontos de risco investigados na revisão (sem bugs encontrados)

- **Duplo-disparo por múltiplos contact points no mesmo step** (risco mais crítico, investigado a fundo): testado com overlap total entre 2 criaturas e com 4 criaturas mutuamente sobrepostas (6 pares) — sempre exatamente 1 filho por par elegível, energia debitada uma única vez. Shapes de criatura são `pymunk.Circle` (só 1 contact point por par) e o Pymunk 7.2.0 dispara `begin` uma única vez por par por step.
- **Conflito entre handler de comida (BIT-03) e handler de criatura×criatura (BIT-04)** na mesma space: testado com colisão simultânea (mesma criatura tocando comida e outra criatura no mesmo frame) — ambos disparam corretamente, sem interferência.
- **Aritmética de energia**: `MIN_ENERGY_TO_MATE=50.0` checado antes do débito de `REPRODUCTION_ENERGY_COST=30.0`; com `max_energy=100.0`, pior caso pós-débito é `20.0` — nunca negativo.
- **Stub de `think()` nos testes multi-step**: confirmado que é só isolamento de teste (evita flakiness da rede estocástica decidindo `action_mate`); revisor rodou um cenário 100% orgânico (sem stub) e a reprodução ocorreu corretamente pelo caminho de produção real.

## Resultados dos gates de qualidade

- Sub-agente implementador: `pytest backend/tests/` → 32/32 passed (25 + 7 novos), suíte de reprodução repetida 8x sem flakiness
- Sub-agente revisor (independente, com testes próprios de duplo-disparo): 32/32 passed — **veredito APROVADO**
- Observações não-bloqueantes da revisão (aceitas, fora de escopo desta task): ausência de cap populacional (não pedido pela spec), lag de um frame pré-existente entre colisão e estado atualizado (padrão já existente, não regressão)

## Como validar

```powershell
cd C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos
backend\venv\Scripts\python.exe -m pytest backend/tests/ -v
```

Manualmente: `manager.py` → Start Tudo → abrir frontend, deixar rodar por um tempo — a população deve crescer organicamente via reprodução, não só via "Jardim do Éden".

**Nota:** havia um processo backend antigo (`uvicorn`, PID ativo na porta 8001) rodando código anterior a este merge — reinicie via `manager.py` (Stop → Start) antes de validar visualmente para garantir que está rodando o código atualizado.
