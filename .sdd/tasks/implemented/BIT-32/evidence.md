# Evidência — BIT-32: Carregar Comida com Efeito Físico

**Data de conclusão:** 2026-08-28

## Demanda atendida

`Action_Grab_Drop` (output 2) e `Load_Sensor` (input 13) agora têm efeito real: bibites podem pegar
um item de comida (inventário de 1 slot), carregá-lo acompanhando a boca e consumi-lo automaticamente
sob fome ou soltá-lo quando o sinal cai — sem mudança no contrato de I/O do NEAT nem no WebSocket.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/creature.py` | modificado | Constantes `HELD_FOOD_CONSUME_ENERGY_FRACTION`/`HELD_FOOD_MOUTH_OFFSET`; atributos `is_holding` (real), `held_food`, `food_grabbed`; métodos `grab_food`/`drop_food`; bloco de consumo/soltura em `update`; `drop_food()` em `die()` |
| `backend/simulation/food.py` | modificado | Atributos `is_held`, `max_ttl`; campo `"held"` em `to_dict()` |
| `backend/simulation/engine.py` | modificado | Import de `HELD_FOOD_MOUTH_OFFSET`; handler de colisão ramifica pegar × comer; TTL pula comida carregada; reposiciona comida na boca a cada step |
| `backend/tests/test_carry_food.py` | criado | 7 testes: pegar, comer normal, TTL pausado, consumo por fome, soltura por sinal, soltura na morte, slot único |

## Resultados dos gates de qualidade

- `import main`: OK
- `pytest tests/`: 253 passed (7 novos + 246 baseline)

## Nota de implementação

`drop_food()` usa `food.ttl = food.max_ttl` (atributo adicionado em `Food.__init__`) em vez de importar
`FOOD_TTL` diretamente — evita importação circular (`food.py` já importa `CREATURE_MASS` de `creature.py`).

O bloco de consumo/soltura em `update` tem guard `if self.is_alive` para garantir que uma criatura que
morre neste frame não consuma a comida (a liberação na morte é tratada por `die()`).

## Como validar

1. `python manager.py` → Start Tudo
2. Abrir o frontend em `http://localhost:5173`
3. Observar que a simulação roda sem erros no `backend.log`
4. (Comportamento evolutivo) Em gerações futuras, bibites que evoluírem `Action_Grab_Drop` aparecerão
   carregando comida — visível como um ponto amarelo na "boca" (frente) da criatura
