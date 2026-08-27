# Spec — BIT-09: Reprodução Assexuada

**Linear:** N/A
**Risco:** medium
**Camada(s):** Backend (Simulação)

---

## Demanda

Hoje a única forma de uma `Creature` gerar descendência é colidir com outra `Creature` ADULT que também tenha `Action_Mate` ativo (BIT-04). Isso significa que uma criatura sozinha — mesmo acumulando energia de sobra por ter aprendido a buscar comida — não tem nenhuma via de reprodução caso não encontre parceiro. O developer quer uma segunda via, **assexuada**, condicionada a idade (`life_stage == ADULT`) e nível de energia, como mecanismo complementar de pressão reprodutiva (a reprodução sexuada continua intocada e será revisitada em task futura).

## Abordagem técnica

Reaproveitar o output `Action_Mate` (já existente no contrato de I/O do NEAT) como um sinal geral de "quero reproduzir", em vez de criar uma 5ª saída na rede — evita tocar `neat_config.ini`/o contrato documentado em `rtneat_wrapper.py`, mantendo o risco em `medium` em vez de `high`. Uma criatura `ADULT` com `Action_Mate` ativo reproduz **sexuadamente** se colidir com um parceiro elegível (comportamento atual do BIT-04, intocado); se não colidiu com ninguém neste frame mas tem energia acima de um limiar mais alto que o da via sexuada, reproduz **assexuadamente**: clona o próprio genoma (`copy.deepcopy` + novo id, validado ao vivo contra a `neat-python` real instalada no projeto) e aplica a mesma `mutate_genome()` já usada na via sexuada. Um único cooldown (renomeado de `mate_cooldown` para `reproduction_cooldown`) é compartilhado pelas duas vias, o que automaticamente impede que uma criatura reproduza duas vezes no mesmo frame (o handler de colisão sexual roda dentro de `physics.step()`, antes do novo laço assexuado em `step()` — se ele já disparou, o cooldown recém-setado bloqueia o laço assexuado no mesmo frame).

## Arquivos a tocar

| Arquivo (path relativo à raiz do projeto) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/rtneat_wrapper.py` | modificar | Nova função `clone_genome(genome, genome_id, config)` |
| `backend/simulation/creature.py` | modificar | Renomear `mate_cooldown` → `reproduction_cooldown` |
| `backend/simulation/engine.py` | modificar | Renomear usos de `mate_cooldown`; novo laço de reprodução assexuada em `step()`; novas constantes |
| `backend/tests/test_reproduction.py` | modificar | Atualizar referências de `mate_cooldown` → `reproduction_cooldown` (comportamento sexuado não muda) |
| `backend/tests/test_asexual_reproduction.py` | criar | Testes da via assexuada nova |

## Passos de implementação

1. **`rtneat_wrapper.py`** — adicionar `import copy` no topo e, junto de `organic_crossover`/`mutate_genome`:
   ```python
   def clone_genome(genome, genome_id, config):
       """
       Cria uma copia independente de um genoma (reproducao assexuada: um unico pai).
       Deepcopy garante que conexoes/nos do clone nao compartilhem referencia com o
       original antes da mutacao subsequente.
       """
       clone = copy.deepcopy(genome)
       clone.key = genome_id
       return clone
   ```
   Não mexer na docstring do contrato de I/O (inputs/outputs da rede) — esta mudança não altera topologia nem sensores/atuadores.

2. **`creature.py`** — renomear atributo em todo o arquivo:
   - `self.mate_cooldown = 0.0` → `self.reproduction_cooldown = 0.0` (em `__init__`)
   - `self.mate_cooldown = max(0.0, self.mate_cooldown - dt)` → `self.reproduction_cooldown = max(0.0, self.reproduction_cooldown - dt)` (em `update()`)

3. **`engine.py`** — renomear `c1.mate_cooldown`/`c2.mate_cooldown` para `reproduction_cooldown` nas 4 ocorrências dentro de `_on_creature_creature_collision` (leitura e escrita). Importar `clone_genome` junto de `organic_crossover, mutate_genome`. Adicionar as novas constantes junto das existentes:
   ```python
   MIN_ENERGY_TO_REPRODUCE_ASEXUALLY = 70.0
   ASEXUAL_REPRODUCTION_ENERGY_COST = 50.0
   ASEXUAL_REPRODUCTION_COOLDOWN = 20.0  # 2x o cooldown sexuado: via solo nao deve dominar sobre achar parceiro
   ```
   Inserir um novo passo em `SimulationEngine.step()`, logo após `self.physics.step(dt)` (que já resolveu qualquer reprodução sexuada deste frame via collision handler) e antes do ciclo de vida dos oásis:
   ```python
   # 1.5. Reproducao assexuada: Action_Mate reaproveitado como sinal geral de
   # "quero reproduzir" — se a criatura nao encontrou parceiro (colisao) neste
   # frame mas tem energia de sobra, clona o proprio genoma. Custo e cooldown
   # mais altos que o sexuado: via de emergencia, nao deve ser dominante.
   asexual_children = []
   for creature in self.creatures:
       if not creature.is_alive:
           continue
       if creature.life_stage != LifeStage.ADULT:
           continue
       if creature.reproduction_cooldown > 0:
           continue
       if not creature.action_mate:
           continue
       if creature.energy < MIN_ENERGY_TO_REPRODUCE_ASEXUALLY:
           continue

       creature.energy -= ASEXUAL_REPRODUCTION_ENERGY_COST
       creature.reproduction_cooldown = ASEXUAL_REPRODUCTION_COOLDOWN

       child_id = self.next_genome_id()
       child_genome = clone_genome(creature.genome, child_id, creature.config)
       mutate_genome(child_genome, creature.config)
       asexual_children.append(
           Creature(self, creature.body.position.x, creature.body.position.y, genome=child_genome)
       )

   for child in asexual_children:
       self.add_creature(child)
   ```
   Nota: construir a lista `asexual_children` e só adicionar ao `self.creatures` (via `add_creature`) depois do laço — mutar `self.creatures` durante a própria iteração é inseguro e faria o filho recém-nascido (`EGG`, `reproduction_cooldown == 0`) ser reavaliado no mesmo laço.

4. **`test_reproduction.py`** — trocar todas as ocorrências de `c1.mate_cooldown`/`c2.mate_cooldown` por `reproduction_cooldown` (só rename; nenhuma asserção de comportamento muda).

5. **`test_asexual_reproduction.py`** (criar) — seguir o padrão de fixtures/stubs de `test_reproduction.py` (`think()` stubado para isolar de aleatoriedade da rede, `DT = 1/30.0`, import de `METABOLISM_RATE_BY_STAGE` para calcular energia esperada). Cobrir:
   - Criatura `ADULT` sozinha (sem nenhuma outra criatura no engine), `action_mate=True`, energia acima do limiar → nasce um filho `EGG` clonado+mutado; energia debitada em `ASEXUAL_REPRODUCTION_ENERGY_COST`; `reproduction_cooldown` setado.
   - Energia abaixo de `MIN_ENERGY_TO_REPRODUCE_ASEXUALLY` → não reproduz.
   - `action_mate=False` → não reproduz.
   - `life_stage != ADULT` (JUVENILE) → não reproduz.
   - `reproduction_cooldown > 0` → não reproduz.
   - **Prioridade sexual sobre assexual no mesmo frame:** dois `ADULT` colidindo, ambos com `action_mate=True` e energia suficiente para os dois caminhos → nasce exatamente 1 filho (o sexuado), não 2 (o cooldown setado pelo handler de colisão bloqueia o laço assexuado no mesmo `step()`).
   - Genoma do filho é clone+mutação do genoma do único pai (spy em `clone_genome`/`mutate_genome`, mesmo padrão de `test_child_genome_comes_from_crossover_and_mutation_not_zero_genome`).
   - Smoke test: várias criaturas isoladas (sem colisão entre si) com energia alta e `action_mate=True`, população cresce de forma limitada pelo cooldown (`< 200`, mesmo teto usado no smoke test sexuado).

6. Rodar a suíte completa (`backend\venv\Scripts\python.exe -m pytest backend/tests/ -v`) e confirmar 100% verde (57 testes atuais + novos).

## Contratos técnicos

### Backend (Simulação)
- `clone_genome(genome, genome_id, config) -> DefaultGenome` — nova função pura em `rtneat_wrapper.py`.
- `Creature.reproduction_cooldown: float` — substitui `Creature.mate_cooldown` (mesmo tipo, mesmo default `0.0`, mesma decrementação por `dt` em `update()`).
- Novas constantes em `engine.py`: `MIN_ENERGY_TO_REPRODUCE_ASEXUALLY: float = 70.0`, `ASEXUAL_REPRODUCTION_ENERGY_COST: float = 50.0`, `ASEXUAL_REPRODUCTION_COOLDOWN: float = 20.0`.
- **Nenhuma mudança no contrato de I/O do NEAT** (`rtneat_wrapper.py` docstring, `neat_config.ini`, `Creature.think()`) — `Action_Mate` continua sendo o output de índice 3, sem novo output.
- **Nenhuma mudança de protocolo WebSocket/`to_dict()`** — `reproduction_cooldown` é estado interno, não exposto ao frontend (assim como `mate_cooldown` já não era).

## Critérios de aceite

- [ ] Criatura `ADULT` sozinha (sem colisão), `action_mate=True`, energia `>= MIN_ENERGY_TO_REPRODUCE_ASEXUALLY` e `reproduction_cooldown <= 0` gera um filho `EGG` clonado+mutado do próprio genoma.
- [ ] Energia debitada = `ASEXUAL_REPRODUCTION_ENERGY_COST`; `reproduction_cooldown` setado para `ASEXUAL_REPRODUCTION_COOLDOWN`.
- [ ] `JUVENILE`/`ELDER`/`EGG` não disparam reprodução assexuada.
- [ ] `action_mate=False` ou energia abaixo do limiar não disparam.
- [ ] Criatura que reproduziu sexuadamente em um frame não também reproduz assexuadamente no mesmo frame (cooldown compartilhado).
- [ ] Reprodução sexuada existente (BIT-04) permanece 100% funcional — `test_reproduction.py` continua verde após o rename.
- [ ] `pytest backend/tests/test_asexual_reproduction.py` 100% verde.
- [ ] Nenhuma regressão: suíte completa (`pytest backend/tests/`) 100% verde.

## Rollback

Reverter `engine.py` (remover laço de reprodução assexuada e as 3 novas constantes; desfazer rename `reproduction_cooldown` → `mate_cooldown`); reverter `creature.py` (desfazer rename); reverter `test_reproduction.py` (desfazer rename); remover `clone_genome` de `rtneat_wrapper.py`; deletar `backend/tests/test_asexual_reproduction.py`.
