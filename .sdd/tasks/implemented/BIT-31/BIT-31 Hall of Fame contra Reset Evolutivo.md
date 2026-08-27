# Spec — BIT-31: Hall of Fame contra Reset Evolutivo

**Linear:** N/A
**Risco:** medium
**Camada(s):** Backend (Simulação)

---

## Demanda

Impedir que a extinção total apague o pool genético. Hoje, quando a população zera, o Jardim do Éden
re-semeia **10 genomas zero** (`engine.py:293-296`) — reconstruindo a Geração 0 e descartando todo o
aprendizado evolutivo acumulado. Como extinções acontecem com frequência (~6 em 5 min pela memória do
projeto), a profundidade de linhagem nunca cresce: o sistema oscila em torno da Gen 0. Esta task
introduz um **Hall of Fame** — cache dos melhores genomas já vistos, preservado através de extinções —
e faz a re-semeadura clonar+mutar a partir dele, **preservando a geração da linhagem**. É a alavanca
de maior impacto para "evoluir por mais gerações".

## Abordagem técnica

Ao morrer, cada criatura recebe um **proxy de fitness** `score = age + W·children_count` (longevidade +
descendência). Se o score entra no top-N, um **deepcopy** do genoma é guardado no `hall_of_fame` do
engine junto com o score e a geração. Na extinção total, em vez de genomas zero, a re-semeadura
**clona+muta genomas do hall** (round-robin pelos melhores) e faz cada re-semeado nascer com a
**geração preservada** do genoma — a linhagem continua de onde parou, então `max_generation`
(BIT-30) deixa de resetar. Fallback ao genoma zero apenas se o hall estiver totalmente vazio.

**Dependência:** BIT-30 (usa `children_count` e `generation` por criatura). **Sem contrato novo** de
API/WebSocket nem alteração do I/O do NEAT — mudança interna ao engine.

**Fora de escopo:** persistir o hall em disco (sobreviver a restart do backend); disparar o Éden mais
cedo / mais generoso; expor o hall na UI — todos mapeados como refinamentos futuros.

## Arquivos a tocar

| Arquivo (path relativo à raiz) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/engine.py` | modificar | `hall_of_fame`, registro na morte, re-semeadura de extinção a partir do hall |
| `backend/simulation/rtneat_wrapper.py` | modificar (opcional) | reusar `clone_genome`/`mutate_genome` (já existentes) — sem nova função se não precisar |
| `backend/tests/test_hall_of_fame.py` | criar | testes do registro por score e da re-semeadura preservando geração |

## Passos de implementação

1. **Constantes (topo de `engine.py`, junto das demais):**
   ```python
   HALL_OF_FAME_SIZE = 12              # nº de genomas de elite preservados através de extinções
   HALL_OF_FAME_CHILDREN_WEIGHT = 20.0 # peso de cada filho no proxy de fitness (≈20 s de vida)
   ```

2. **`SimulationEngine.__init__`:** `self.hall_of_fame = []` — lista de dicts
   `{"score": float, "genome": DefaultGenome, "generation": int}`, mantida ordenada desc. por score,
   cap `HALL_OF_FAME_SIZE`.

3. **Método `_record_in_hall_of_fame(self, creature)`:**
   ```python
   def _record_in_hall_of_fame(self, creature):
       score = creature.age + HALL_OF_FAME_CHILDREN_WEIGHT * creature.children_count
       if len(self.hall_of_fame) < HALL_OF_FAME_SIZE or score > self.hall_of_fame[-1]["score"]:
           entry = {
               "score": score,
               "genome": clone_genome(creature.genome, creature.genome.key, creature.config),  # deepcopy
               "generation": creature.generation,
           }
           self.hall_of_fame.append(entry)
           self.hall_of_fame.sort(key=lambda e: e["score"], reverse=True)
           del self.hall_of_fame[HALL_OF_FAME_SIZE:]
   ```
   (Importar `clone_genome` — já importado no engine junto de `organic_crossover`/`mutate_genome`.)

4. **Chamar na morte (engine.py, laço de remoção ~279-286):** no ramo `else:` (criatura morta), antes
   de `c.die()`, `self._record_in_hall_of_fame(c)`. Combina com o `_lifespan_sum += c.age` do BIT-30
   no mesmo laço.

5. **Método `_spawn_from_hall_of_fame(self, count)`:** produz `count` criaturas novas clonando+mutando
   genomas do hall em round-robin, preservando a geração:
   ```python
   def _spawn_from_hall_of_fame(self, count):
       spawned = []
       for i in range(count):
           entry = self.hall_of_fame[i % len(self.hall_of_fame)]
           child_id = self.next_genome_id()
           genome = clone_genome(entry["genome"], child_id, self.config_ref())  # ver nota de config
           mutate_genome(genome, self.config_ref())
           spawned.append(Creature(self, genome=genome, generation=entry["generation"]))
       return spawned
   ```
   > **Config:** `Creature` carrega `self.config` (via `load_neat_config()`); o engine não guarda uma
   > config própria hoje. Resolver de forma simples: usar `load_neat_config()` diretamente
   > (`from simulation.rtneat_wrapper import load_neat_config`) — é cacheada por path, retorna a mesma
   > instância que as criaturas usam. Substituir `self.config_ref()` por `load_neat_config()` no código final.

6. **Re-semeadura de extinção (engine.py:293-296):** trocar por:
   ```python
   if len(self.creatures) == 0:
       self.extinctions_total += 1   # (BIT-30)
       if self.hall_of_fame:
           for child in self._spawn_from_hall_of_fame(10):
               self.add_creature(child)
       else:
           for _ in range(10):
               self.add_creature(Creature(self))   # fallback: sem histórico ainda → genoma zero
       self._eden_active = False
   ```
   > Se o BIT-30 já incrementa `extinctions_total` aqui, não duplicar — manter uma única linha.

7. **Testes (`backend/tests/test_hall_of_fame.py`)** (importar constantes dos módulos, nunca hardcodar):
   - `_record_in_hall_of_fame` insere e ordena por score desc.; respeita o cap `HALL_OF_FAME_SIZE`
     (inserir N+3 entradas com scores distintos → sobram as N maiores).
   - Score reflete `age + W·children_count` (criatura com filhos supera criatura só longeva equivalente).
   - Extinção com hall populado: esvaziar `engine.creatures`, popular o hall com um genoma de
     `generation = 5`, rodar `step()` → nascem 10 criaturas, **todas com `generation == 5`** (geração
     preservada) e `is_alive`; nenhuma é genoma zero (`generation != 0`).
   - Extinção com hall vazio: re-semeia 10 criaturas `generation == 0` (fallback).
   - Genoma no hall é cópia independente: mutar o genoma vivo depois de registrado não altera a entrada
     (deepcopy — comparar contagem de conexões/pesos antes e depois).
   - `python -c "import main"` OK e `pytest backend/tests/` verde.

## Contratos técnicos

### Backend (Simulação)
- Constantes: `HALL_OF_FAME_SIZE = 12`, `HALL_OF_FAME_CHILDREN_WEIGHT = 20.0`.
- `SimulationEngine.hall_of_fame: list[dict]` — `{"score": float, "genome": DefaultGenome, "generation": int}`, ordenada desc., cap N.
- `SimulationEngine._record_in_hall_of_fame(creature)` e `SimulationEngine._spawn_from_hall_of_fame(count) -> list[Creature]`.
- Re-semeadura de extinção passa a clonar+mutar do hall (fallback: genoma zero se vazio).

### API/WebSocket
- Nenhuma mudança de protocolo. (O hall é interno; expô-lo na UI é futuro.)

## Critérios de aceite

- [ ] Ao morrer, criaturas de maior `score` (idade + filhos) entram no hall; o hall respeita o cap `HALL_OF_FAME_SIZE`.
- [ ] Genomas no hall são cópias independentes (deepcopy) — não sofrem alias com criaturas vivas/removidas.
- [ ] Na extinção total com hall populado, as 10 novas criaturas nascem de genomas do hall e **preservam a geração** (não resetam para 0).
- [ ] Com hall vazio, mantém o fallback de 10 genomas zero (comportamento atual).
- [ ] `pytest backend/tests/` verde (baseline + novos) e `python -c "import main"` OK.

## Rollback

Reverter a branch BIT-31: deletar `backend/tests/test_hall_of_fame.py`; restaurar `engine.py`
(remover `hall_of_fame`, os dois métodos e as constantes; voltar a re-semeadura de extinção ao laço
de 10 `Creature(self)`). `rtneat_wrapper.py` não muda de contrato (só reusa funções existentes).
