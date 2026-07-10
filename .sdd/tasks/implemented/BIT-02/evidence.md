# Evidência — BIT-02: Atuadores NEAT (conectar FeedForwardNetwork aos motores)

**Data de conclusão:** 2026-07-10
**Linear:** N/A

## Demanda atendida

A locomoção da `Creature` deixou de ser um impulso fixo para frente e passou a vir da saída real de uma `neat.nn.FeedForwardNetwork`, construída a partir do genoma de cada criatura. A rede roda no brain tick de 10 FPS (mesmo acumulador de BIT-01), lendo 16 inputs (9 cones de visão + energia + idade + 2 placeholders + carga + feedback cinético linear/angular) e produzindo 4 outputs: `Motor_Forward`/`Motor_Torque` (aplicados fisicamente a 30 FPS) e `Action_Grab_Drop`/`Action_Mate` (cacheados, sem efeito de jogo ainda — ficam para BIT-03/04).

Implementado via sub-agente implementador + sub-agente revisor independente (fluxo de coordenação com gate de qualidade).

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/creature.py` | modificado | `__init__` ganha `genome=None`; cria `self.config`/`self.genome`/`self.net`; novo método `think(engine)`; `update()` aplica motor/torque cacheados; custo de energia proporcional à magnitude real do motor |
| `backend/simulation/engine.py` | modificado | `next_genome_id()` monotônico; `creature.think(self)` chamado no brain tick (10 FPS), logo após `compute_vision` |
| `backend/tests/test_creature_think.py` | criado | 7 testes (6 do implementador + 1 adicionado na revisão) |

## Desvio da spec (correção pós-revisão)

O sub-agente revisor encontrou que o pseudocódigo original da spec cobra `motor_cost` de **todas** as criaturas, inclusive `EGG` — mas o impulso/torque só é aplicado fisicamente fora do estágio `EGG`. Resultado: um ovo podia perder energia proporcional a uma saída de motor que nunca teve efeito físico algum (motor "fantasma"), acelerando a morte de Gen 0 de forma não intencional. Corrigido movendo o cálculo de `motor_cost` para dentro do mesmo `if self.life_stage != LifeStage.EGG:` (motor_cost = 0.0 para EGG). Adicionado teste `test_egg_pays_no_motor_cost_even_with_strong_motor_output` cobrindo o caso.

Duas observações de baixa severidade do revisor foram aceitas como estão (herdadas de tasks anteriores / literais da spec, não bloqueantes): clamp inferior morto em `Kinetic_Feedback` linear (velocidade é sempre `>=0`) e docstring de `rtneat_wrapper.py` desatualizada quanto à codificação de visão inativa (fala em `-1.0`, implementação usa `0.0` desde BIT-01) — fica para limpeza futura.

## Resultados dos gates de qualidade

- Sub-agente implementador: `pytest backend/tests/` → 20/20 passed
- Sub-agente revisor (independente, rodou a suíte de novo): 20/20 passed, aprovado com ressalvas
- Após correção do achado #1 da revisão + teste novo: `pytest backend/tests/ -v` → **21/21 passed**
- Smoke test manual (implementador e revisor, separadamente): `SimulationEngine` com 5-10 criaturas, 20 steps de `1/30s`, sem exceção

## Como validar

```powershell
cd C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos
backend\venv\Scripts\python.exe -m pytest backend/tests/ -v
```

Manualmente: `manager.py` → Start Tudo → abrir frontend — o movimento das criaturas deixa de ser sempre reto (saída da rede, não mais determinístico).
