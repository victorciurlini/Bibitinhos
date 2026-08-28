# Evidência — BIT-38: Sensor de Proximidade de Paredes

**Data de conclusão:** 2026-08-28

## Demanda atendida

Adicionados 4 sensores de proximidade de paredes (Wall_North, Wall_South, Wall_West, Wall_East) ao contrato de I/O do NEAT, expandindo de 16 para 20 inputs. Cada sensor retorna um valor normalizado [0,1] (0 = perto da parede, 1 = parede oposta), calculado em `creature.think()` a cada brain tick.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/neat_config.ini` | modificado | `num_inputs` 16→20; cabeçalho atualizado com inputs 16-19 (Wall_*) |
| `backend/simulation/rtneat_wrapper.py` | modificado | `INPUT_LABELS` expandido com 4 novos labels; bias Motor_Torque zerado em `create_zero_genome` (fix BIT-37 flakiness) |
| `backend/simulation/creature.py` | modificado | `think()` calcula wall_north/south/west/east e os inclui como inputs 16-19 |
| `backend/tests/test_rtneat_wrapper.py` | modificado | 3 testes atualizados: num_inputs 16→20, conexões 104→128, ativação com 20 inputs |
| `backend/tests/test_exploration_pressure.py` | modificado | Ativação de rede atualizada de 16 para 20 inputs (linha 205) |

## Resultados dos gates de qualidade

- `import main`: OK
- `pytest backend/tests/`: 246 passed, 0 failed, 8 warnings

## Como validar

1. `manager.py` → Start Tudo → aguardar criaturas Gen-0 aparecerem
2. Clicar em uma criatura → Inspetor de rede neural no HUD
3. Verificar que os 4 novos inputs aparecem com labels Wall_North, Wall_South, Wall_West, Wall_East
4. Observar valores: criatura perto da borda superior → Wall_North ≈ 0.0; criatura no centro → Wall_N ≈ 0.5
