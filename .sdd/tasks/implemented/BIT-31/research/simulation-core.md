# Research — simulation-core (BIT-31: Hall of Fame contra Reset Evolutivo)

> Relatório do orquestrador (arquivos lidos/validados diretamente na sessão, §84 do protocolo).

## O problema (diagnóstico que originou a task)

A evolução no Bibitinhos é rtNEAT "orgânico": não há `neat.Population.run()` nem fitness clássico;
genomas nascem por eventos (crossover na reprodução sexuada, clone na assexuada) e a seleção é o
filtro de sobrevivência (quem chega a ADULT, come e acasala propaga o genoma).

**O maior ofensor à acumulação de gerações é a re-semeadura do Éden na extinção total**
(`engine.py:293-296`):

```python
if len(self.creatures) == 0:
    for _ in range(10):
        self.add_creature(Creature(self))   # genoma ZERO seedado — descarta todo o aprendizado
    self._eden_active = False
```

`Creature(self)` sem `genome=` cai em `create_zero_genome()` (`creature.py:155`), que reconstrói o
genoma da Gen 0 com os seeds fixos (`rtneat_wrapper.py:90-114`). Ou seja: **cada extinção joga fora
o pool genético e recomeça da geração 0**. A memória do projeto registra ~6 extinções em 5 min — a
profundidade de linhagem nunca acumula.

## Arquivos relevantes
- `backend/simulation/engine.py` (extinção 291-316; morte 279-286; reprodução 155-231)
- `backend/simulation/creature.py` (`__init__` aceita `genome=`; `generation`/`children_count` do BIT-30)
- `backend/simulation/rtneat_wrapper.py` (`clone_genome(genome, id, config)` = deepcopy + nova key;
  `mutate_genome(genome, config)`)
- `backend/simulation/oasis.py` (`EDEN_POPULATION_THRESHOLD`, params do oásis do Éden)

## Mecanismo proposto (validado contra as APIs)

**Hall of Fame:** cache dos melhores genomas já vistos, preservado através de extinções.
- Proxy de fitness computado **na morte**: `score = age + W * children_count` (longevidade +
  reprodução; `age` = tempo de vida final, `children_count` vem do BIT-30). Recompensa tanto viver
  muito quanto deixar descendência.
- Ao morrer, se o `score` supera o pior do hall (ou o hall não está cheio), guarda-se um
  **deepcopy** do genoma + score + geração. `clone_genome()` já faz deepcopy seguro (validado:
  `copy.deepcopy` do `DefaultGenome` funciona; é o que a reprodução assexuada usa).
- **Na extinção total**, em vez de 10 genomas zero, re-semeia clonando+mutando genomas do hall
  (round-robin pelos melhores), **preservando a geração** guardada (a linhagem evolutiva continua de
  onde parou — é isso que faz `max_generation` deixar de resetar). Se o hall estiver vazio (primeira
  extinção antes de qualquer morte registrada — raro), cai no comportamento atual (genoma zero).

**Dependência:** BIT-30 (precisa de `children_count` e `generation` por criatura). Sem o BIT-30 não
há proxy de fitness nem geração para preservar.

## Decisões de design (resolvidas para a spec)
- `HALL_OF_FAME_SIZE = 12`, `HALL_OF_FAME_CHILDREN_WEIGHT = 20.0` (um filho "vale" ~20 s de vida;
  calibrável depois via o registry de params do BIT-23 — não obrigatório nesta task).
- Preservar a geração: a criatura re-semeada nasce com a `generation` do genoma no hall (não 0).
- Não mexer no `EDEN_POPULATION_THRESHOLD` nem na generosidade do Éden aqui — "disparar o Éden mais
  cedo" fica como tuning separado (mapeado no roadmap), para manter a task focada na preservação do pool.
- Guardar genomas por deepcopy no momento da morte evita alias com o objeto vivo (que seria removido).

## O que precisa ser feito
1. `SimulationEngine`: atributo `hall_of_fame` (lista de entradas `{score, genome, generation}`, cap N).
2. Método/rotina que, na morte de uma criatura, calcula o score e atualiza o hall (mantém top-N).
3. Trocar a re-semeadura de extinção para clonar+mutar do hall (com fallback ao genoma zero se vazio),
   preservando a geração.
4. Constantes `HALL_OF_FAME_SIZE`, `HALL_OF_FAME_CHILDREN_WEIGHT`.
5. Testes: hall recebe os melhores; extinção com hall populado re-semeia genomas do hall e preserva geração.

## Perguntas em aberto (resolvidas)
- E se o hall tiver <10 entradas na extinção? Re-semeia repetindo/round-robin as que houver; completa
  com genoma zero se o hall estiver totalmente vazio.
- Persistir o hall em disco (sobreviver a restart do backend)? **Fora de escopo** — mapeado como futuro.
