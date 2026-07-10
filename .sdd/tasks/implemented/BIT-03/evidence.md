# Evidência — BIT-03: Comer (colisão criatura×comida)

**Data de conclusão:** 2026-07-10
**Linear:** N/A

## Demanda atendida

Registrado o collision handler Pymunk (`space.on_collision`) entre `Creature` e `Food`: ao colidir, a criatura ganha `food.energy_value` de energia (respeitando o teto `max_energy`) e a comida é consumida (removida do space + `is_active=False`). Antes desta task, nada chamava `Food.consume()` — comida nunca era "comida" de fato.

Implementado via sub-agente implementador + sub-agente revisor independente.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/creature.py` | modificado | `shape.collision_type = COLLISION_CATEGORY_CREATURE` + `shape.owner = self` |
| `backend/simulation/food.py` | modificado | número mágico `2` trocado por `COLLISION_CATEGORY_FOOD`; `shape.collision_type` + `shape.owner = self` |
| `backend/simulation/engine.py` | modificado | `space.on_collision(CREATURE, FOOD, begin=_on_creature_food_collision)` registrado no `__init__` |
| `backend/tests/test_feeding.py` | criado | 4 testes: transferência de energia, remoção da comida, cap em `max_energy`, caso negativo (longe) |

## Pontos de risco investigados na revisão (sem bugs encontrados)

- Ordem de `arbiter.shapes` (creature sempre primeiro): confirmada contra o código-fonte do Pymunk 7.2.0 instalado + 50 trials empíricos alternando ordem de criação.
- `space.remove()` dentro do callback `begin`: documentado como seguro no Pymunk 7.2.0 (remoção adiada para o fim do `step()`).
- Race de duas criaturas na mesma comida no mesmo step: testado manualmente — sem duplicação de energia (`is_active` setado sincronamente evita double-consume).
- Réplica do loop real de `main.py` (300 steps / 10s simulados, sem o try/except que engole exceções): sem erros.

## Resultados dos gates de qualidade

- Sub-agente implementador: `pytest backend/tests/` → 25/25 passed (21 + 4 novos)
- Sub-agente revisor (independente, rodou a suíte de novo): 25/25 passed — **veredito APROVADO**, nenhum bug bloqueante
- Observações não-bloqueantes da revisão (aceitas como estão, não requerem ação): try/except já defensivo em `food.consume()` fica parcialmente redundante com a semântica documentada do Pymunk; closure vs. função de módulo é estilo, não bug; falta teste explícito para o cenário "duas criaturas na mesma comida" (comportamento correto confirmado manualmente pelo revisor, mas não capturado em teste automatizado — fica como débito menor para task futura)

## Como validar

```powershell
cd C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos
backend\venv\Scripts\python.exe -m pytest backend/tests/ -v
```

Manualmente: `manager.py` → Start Tudo → abrir frontend — criaturas que encostam em comida devem vê-la sumir e a energia (visível via `to_dict()`/inspeção) subir.
