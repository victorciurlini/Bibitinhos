# Research — simulation-core (BIT-30: Instrumentação de Linhagem & Hereditariedade)

> Relatório do orquestrador (arquivos lidos e validados diretamente na sessão, conforme §84 do
> protocolo do refiner). Foco: o que existe hoje para medir evolução e onde inserir os rastros.

## Arquivos relevantes
- `backend/simulation/creature.py` (`Creature.__init__` 111-163, `update` 182-237, `to_dict` 245-264)
- `backend/simulation/engine.py` (`_on_creature_food_collision` 49-63; reprodução sexuada 155-199;
  reprodução assexuada 201-231; remoção de mortos 279-286; Éden/extinção 291-316; `get_state` 319-333)
- `backend/simulation/metrics.py` (**a ser criado pelo BIT-26** — `compute_metrics(engine)` + amostragem)
- `backend/simulation/rtneat_wrapper.py` (`clone_genome`, `organic_crossover` — para referência)
- `backend/tests/test_metrics.py` (**a ser criado pelo BIT-26**)

## Situação atual (o problema que a task resolve)

**Não existe nenhuma métrica de evolução.** `SimulationEngine.current_generation` está fixo em `1` e
nunca incrementa (`engine.py:73`). Não há:
- profundidade de linhagem por criatura (quantas reproduções separam a criatura da Gen 0);
- contagem de comidas ingeridas nem de filhos gerados por indivíduo;
- contagem de extinções totais (quantas vezes a população zerou e o Éden re-semeou do zero);
- tempo de vida médio dos que morreram.

Sem isso é impossível responder à pergunta que originou a demanda ("os bibites evoluem ou só
resetam?"). O sintoma-chave a expor é **`max_generation` ao longo do tempo**: se as linhagens
persistem, ela sobe; se a população reseta a cada extinção (`engine.py:293-295`, que instancia
`Creature(self)` = genoma zero seedado), ela fica presa perto de 0.

## Pontos de inserção (validados no código)

**Nascimento / linhagem.** Filhos são criados em `engine.step()`:
- Sexuado (`engine.py:196`): `Creature(self, cx, cy, genome=child_genome)` — geração do filho =
  `max(a.generation, b.generation) + 1`.
- Assexuado (`engine.py:227`): `Creature(self, ...)` — geração = `creature.generation + 1`.
- Éden/extinção (`engine.py:295`): `Creature(self)` — geração = 0 (re-semeadura do zero, hoje).
- Gen 0 inicial (em `main.py`, fora deste módulo): geração = 0.

`Creature.__init__` precisa aceitar `generation=0` e guardar em `self.generation`.

**Comer.** `_on_creature_food_collision` (`engine.py:49-58`) já tem a referência `creature`; basta
`creature.food_eaten += 1` junto do ganho de energia.

**Filhos gerados.** Nos dois ramos de reprodução, incrementar `children_count` de cada pai
(sexuado: ambos; assexuado: o clonador).

**Morte / tempo de vida.** O laço de remoção de mortos (`engine.py:279-286`) tem cada `c` morto com
`c.age` = tempo de vida final; acumular num somatório para a média.

**Extinção.** O ramo `if len(self.creatures) == 0:` (`engine.py:293`) é o único ponto onde a
população zera; incrementar `extinctions_total` ali.

## O que precisa ser feito
1. Novos atributos em `Creature`: `generation`, `food_eaten`, `children_count` (param `generation` no `__init__`).
2. Engine calcula a geração de cada filho no nascimento e incrementa `children_count` dos pais.
3. `food_eaten` incrementado no handler de colisão com comida.
4. Engine: `extinctions_total`, `_lifespan_sum` (soma das idades dos mortos) para a média.
5. Estender `compute_metrics()` (BIT-26) com `max_generation`, `avg_generation`, `extinctions_total`, `avg_lifespan`.
6. `Creature.to_dict()` expõe `generation`, `food_eaten`, `children_count` (para o inspetor/futuro painel).
7. Testes cobrindo cálculo de geração no nascimento, incrementos e agregados.

## Dependência
**BIT-26** cria `metrics.py`, `compute_metrics()` e os contadores `births_total`/`deaths_total` +
`metrics_history`. BIT-30 **estende** esse módulo. Se BIT-26 ainda não estiver mergeado quando o
BIT-30 for implementado, o implementer cria os campos no mesmo lugar previsto pelo BIT-26 (sem
duplicar módulo). `deaths_total` (do BIT-26) é o denominador de `avg_lifespan`.

## Perguntas em aberto (resolvidas na spec)
- Geração da re-semeadura do Éden: **0** neste BIT (a re-semeadura ainda é do zero). O BIT-31 muda
  isso para preservar a geração do genoma do hall of fame — é lá que a persistência aparece.
- `%` que chega a ADULT / caça bem-sucedida: **fora de escopo** deste BIT (cohort tracking) — mapeado
  como refinamento futuro das métricas.
