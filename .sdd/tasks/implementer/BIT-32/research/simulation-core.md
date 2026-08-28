# Research — simulation-core (BIT-32: Carregar Comida com Efeito Físico)

> Relatório do orquestrador (arquivos lidos/validados diretamente na sessão, §84 do protocolo).
> Contexto: decisão de rumo **B** (manter os seeds da Gen 0 e criar headroom evolutivo *acima* deles).
> Carregar comida é a primeira tarefa com teto acima do que os seeds já resolvem (andar/comer/acasalar).

## Situação atual (o débito técnico que a task fecha)

O contrato de I/O do cérebro **já reserva** os pinos, mas eles não têm efeito:
- **Output 2 — `Action_Grab_Drop`** (`creature.py:179`): `self.action_grab_drop = outputs[2] > 0.0`. Lido, nunca usado.
- **Input 13 — `Load_Sensor`** (`creature.py:172`): `1.0 if self.is_holding else 0.0`.
- **`self.is_holding`** (`creature.py:163`): comentado como *"placeholder do Load_Sensor; mecanica de
  grab fora de escopo desta task"* — sempre `False`.

Roadmap/débitos: *"`Action_Grab_Drop` / `Load_Sensor` são lidos mas não têm efeito físico (sem
inventário nem Weld Joint)."* Esta task adiciona o **inventário de 1 slot** (não um Weld Joint).

## Por que isto é headroom evolutivo (e não redundante com comer)

Os seeds resolvem "virar para a comida + comer no contato". Comer é imediato (o handler de colisão
transfere energia na hora — `engine.py:54-58`). Carregar cria uma estratégia **nova, não semeada**:
pegar comida excedente quando se está **cheio** (energia no teto, comer não caberia) e consumi-la
depois, durante a escassez — em vez de deixar o excedente **apodrecer** (comida tem `FOOD_TTL=30s`,
`food.py:8`) ou ser disputado. Um bibite que aprende a "estocar uma refeição" sobrevive melhor aos
vãos entre oásis. Nenhum seed cobre isso → é exatamente o que a evolução pode descobrir e a seleção
premiar. **Não haverá seed para `Action_Grab_Drop`** — é o comportamento-alvo a evoluir.

## Arquivos relevantes
- `backend/simulation/creature.py` (`__init__` 137-163; `update` 182-237; `die` 239-243; `to_dict` 245-264)
- `backend/simulation/engine.py` (handler de colisão comida 49-63; TTL da comida 233-238; step)
- `backend/simulation/food.py` (`Food`: `is_active`, `ttl`, `consume()`, `FOOD_TTL`, `FOOD_RADIUS`)
- `backend/simulation/physics.py` (`space.add/remove` — padrão já usado em `Food.consume()`/`Creature.die()`)

## Modelo escolhido: inventário lógico (sem constraint física)

Em vez de PivotJoint/Weld (lifecycle frágil: remover em drop/consumo/morte, instabilidade do solver),
**pegar = remover o corpo da comida do `space` e guardar a referência na criatura** (como um item que
entra no inventário). Robusto, sem colisões-fantasma, e espelha o que o projeto já faz em dois lugares:
`Food.consume()` remove do space; o drag do BIT-24 reposiciona um corpo a cada step. A comida carregada
continua na lista `engine.foods` (logo é transmitida ao frontend) com a posição reposicionada para a
"boca" da criatura a cada step, então **renderiza acompanhando o bibite sem mudança no frontend**.

## Semântica resolvida (decisões de design para a spec)
- **Slot único.** Segurando, não pega outra; contato com nova comida segue comendo normalmente (se
  couber energia). Sem output livre para um 5º atuador.
- **Pegar:** contato com comida + `action_grab_drop` alto + **não** segurando → pega (não come).
- **Consumir a reserva:** automático quando `energia/max < HELD_FOOD_CONSUME_ENERGY_FRACTION` (0.5).
  Automático porque não há output livre para "comer a reserva"; o limiar de 0.5 garante que pegar no
  teto e só comer na fome de fato **bufferiza** (senão o metabolismo derrubaria a energia 1 tick após
  pegar e consumiria na hora, anulando o carregar).
- **Soltar:** segurando + `action_grab_drop` **baixo** → solta no lugar (a comida volta ao mundo, TTL
  volta a correr). Dá ao cérebro o controle de abortar o transporte.
- **TTL pausado enquanto carregada** (é o ponto do estoque: preservar contra o apodrecimento).
- **Morte segurando:** solta a comida de volta ao mundo (não some — `die()` libera).
- **Prioridade em `update`:** consumir-se-com-fome antes de soltar-por-sinal-baixo (sobrevivência primeiro).

## Sem mudança de contrato
- I/O do NEAT: **inalterado** (usa `Action_Grab_Drop`/`Load_Sensor` que já existem). Sem seed novo.
- WebSocket: `foods[]` já é transmitido; comida carregada continua aparecendo (posição na boca). Um
  flag `held` no `to_dict()` da comida é **opcional** (só para o frontend estilizar), não requerido.

## O que precisa ser feito
1. `Creature`: `held_food`, usar `is_holding` de verdade, `food_grabbed`; métodos `grab_food`/`drop_food`;
   consumo da reserva e checagem de soltar em `update`; soltar em `die`.
2. `Food`: flag `is_held` (pausa TTL e protege de remoção enquanto carregada).
3. `engine`: no handler de colisão, ramificar pegar × comer; pular TTL de comida carregada; reposicionar
   a comida carregada na boca a cada step.
4. Constante `HELD_FOOD_CONSUME_ENERGY_FRACTION`.
5. Testes: pegar em vez de comer; carregar preserva TTL; consumir na fome; soltar por sinal; soltar na morte.

## Ordem recomendada (não é dependência de código)
BIT-32 é independente do BIT-30/31 no código, mas só dá para **avaliar se o carregar evolui** com as
métricas do BIT-30 e sem o reset do BIT-31. Recomendado implementar **depois** de BIT-30/31.

## Perguntas em aberto (resolvidas)
- Penalidade de senescência reprodutiva / custo de carregar (peso extra, mais lento)? **Fora de escopo**
  — mapeado como polimento futuro. O corpo da comida sai do space, então não há custo físico de arrasto.
