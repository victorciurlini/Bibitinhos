## Arquivos relevantes

- `backend/simulation/creature.py` — `Creature.__init__` (linha 111: `self.energy = 100.0`, hardcoded, sempre cheio ao nascer, inclusive filhos gerados por reprodução)
- `backend/simulation/engine.py` — constantes de reprodução (linhas 20-25) e os dois handlers de reprodução (`_on_creature_creature_collision` sexuado, laço assexuado em `step()`, ambos do BIT-09)
- `backend/tests/test_reproduction.py`, `backend/tests/test_asexual_reproduction.py` — testes que consomem as constantes por import (não hardcoded), portanto se adaptam automaticamente a mudança de valor

## Conteúdo relevante para a demanda

### Valores atuais (confirmados lendo o código) vs. o que o developer descreveu como intenção original

| Constante | Valor atual | Valor pedido pelo developer |
|---|---|---|
| Energia inicial (`Creature.__init__`) | `100.0` (100%, hardcoded) | `75.0` (75% de `max_energy`) |
| `MIN_ENERGY_TO_MATE` (sexuada) | `50.0` (50%) | `100.0` (100%) |
| `REPRODUCTION_ENERGY_COST` (sexuada) | `30.0` (30%) | `50.0` (50%) |

Isso confirma o diagnóstico do developer: hoje uma criatura nasce **já cheia** (100%) e só precisa de **metade** da energia máxima para acasalar — ou seja, ela pode se reproduzir sem nunca ter comido, e ainda sobra energia de sobra depois (custa só 30%). Não há nenhuma pressão real para aprender a buscar comida antes de se reproduzir, o que explica o aglomerado de criaturas acasalando sem esforço e a ausência de pressão evolutiva contra os comportamentos degenerados (ficar parado, andar reto até bater na parede) — parar ou andar sem rumo já é "bom o suficiente" para reproduzir sob essas condições.

### Efeito colateral descoberto: reprodução assexuada (BIT-09) ficaria mais fácil que a sexuada

O BIT-09 foi desenhado deliberadamente como via "mais difícil que a sexuada" (`MIN_ENERGY_TO_REPRODUCE_ASEXUALLY = 70.0` > `MIN_ENERGY_TO_MATE = 50.0` da época; `ASEXUAL_REPRODUCTION_ENERGY_COST = 50.0` > `REPRODUCTION_ENERGY_COST = 30.0` da época; cooldown 2x mais longo). Se só a via sexuada for endurecida para `MIN_ENERGY_TO_MATE = 100.0` / custo `50.0`, a via assexuada (`70.0` / `50.0`) passa a exigir **menos** energia que a sexuada e custar o **mesmo** — invertendo a relação original ("via de emergência, não deve ser dominante", texto do próprio BIT-09). Como `100.0` já é o teto de `max_energy`, não dá pra tornar o limiar assexuado "mais alto" que o sexuado — a solução é igualar o limiar (`100.0`, o próprio teto) e manter o **custo** como diferencial, aplicando o mesmo delta de +20 que já existia na relação original (`50 = 30 + 20` → `70 = 50 + 20`), preservando o cooldown 2x já existente como segundo diferencial.

### Risco de regressão em testes — validado por grep, não apenas suposição

Testes de reprodução (`test_reproduction.py`, `test_asexual_reproduction.py`) importam as constantes (`from simulation.engine import ... REPRODUCTION_ENERGY_COST, MIN_ENERGY_TO_MATE...`) em vez de hardcodar os valores nas asserções — os cálculos de energia esperada (`100.0 - REPRODUCTION_ENERGY_COST - ...`) se ajustam automaticamente aos novos valores. Os testes que usam `energy=100.0` como padrão de fixture continuam válidos porque `100.0 >= 100.0` (novo limiar) ainda passa na checagem `< MIN_ENERGY_TO_MATE`.

Busquei (`grep`) todo uso de `.energy`/`100.0` em `backend/tests/` para confirmar que nenhum teste **fora** dos arquivos de reprodução depende do valor *default* de energia ao nascer (100.0 hardcoded em `Creature.__init__`): `test_feeding.py`, `test_metabolism.py`, `test_creature_think.py` sempre setam `.energy` explicitamente antes de qualquer asserção, ou comparam antes/depois de forma relativa (`energy_before = creature.energy`). `test_locomotion.py` e `test_oasis.py` não referenciam `.energy` em nenhuma asserção. Ou seja, mudar a energia inicial de `100.0` para `75.0` não deveria quebrar nenhum teste existente fora dos arquivos de reprodução — mas a suíte completa deve ser rodada para confirmar.

## O que precisa ser feito

1. `creature.py`: extrair `STARTING_ENERGY = 75.0` como constante de módulo (mesmo padrão de `CREATURE_MASS`) e usar em `self.energy = STARTING_ENERGY` no `__init__` (aplica a todas as criaturas novas: Gen 0, filhos de reprodução sexuada/assexuada, respawns do Jardim do Éden — não há necessidade de caso especial).
2. `engine.py`: `MIN_ENERGY_TO_MATE` 50→100, `REPRODUCTION_ENERGY_COST` 30→50, `MIN_ENERGY_TO_REPRODUCE_ASEXUALLY` 70→100, `ASEXUAL_REPRODUCTION_ENERGY_COST` 50→70 (preserva o delta +20 sobre a sexuada). `REPRODUCTION_COOLDOWN`/`ASEXUAL_REPRODUCTION_COOLDOWN` inalterados (não pedido, relação 2x já existente continua válida).
3. Rodar a suíte completa para confirmar que nada quebrou (expectativa, por análise estática: nada quebra, mas precisa rodar de verdade).

## Perguntas em aberto

Nenhuma — grep confirmou que a mudança de energia inicial é segura para os testes existentes; ajuste proporcional da via assexuada resolvido preservando a relação de dificuldade original do BIT-09 sem precisar perguntar (matematicamente, 100% já é o teto, então igualar o limiar e manter o delta de custo é a única forma de preservar "assexuada é mais difícil").
