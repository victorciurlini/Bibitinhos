# Spec — BIT-32: Carregar Comida com Efeito Físico

**Linear:** N/A
**Risco:** medium
**Camada(s):** Backend (Simulação) — payload aditivo opcional; sem novo endpoint/mensagem nem mudança no I/O do NEAT

---

## Demanda

Dar efeito real a `Action_Grab_Drop` (output 2) e `Load_Sensor` (input 13), hoje lidos mas inertes
(`is_holding` é placeholder fixo em `False`). Um bibite passa a poder **pegar** um item de comida,
**carregá-lo** e **consumi-lo depois** — um inventário de 1 slot. Fecha o débito técnico "grab/carry
sem efeito" e, sobretudo, cria o primeiro **headroom evolutivo acima dos seeds da Gen 0** (rumo **B**,
decidido nesta sessão): pegar comida excedente quando cheio e consumi-la na escassez é uma estratégia
que nenhum seed resolve — é o que queremos que a evolução descubra.

## Abordagem técnica

**Inventário lógico, não constraint física.** Pegar = remover o corpo da comida do `space` do Pymunk e
guardar a referência em `creature.held_food` (robusto, sem PivotJoint/Weld nem colisões-fantasma;
espelha `Food.consume()` e o reposicionamento do drag do BIT-24). A comida carregada continua em
`engine.foods` (logo é transmitida) e é reposicionada na "boca" da criatura a cada step, então
**renderiza acompanhando o bibite sem mudança no frontend**. Consumo da reserva é automático abaixo de
um limiar de fome (não há output livre para um "comer reserva"). **Sem seed** para `Action_Grab_Drop` —
é o comportamento-alvo a evoluir. **Sem mudança no contrato de I/O do NEAT nem no protocolo WebSocket.**

**Ordem recomendada:** independente de código, mas só avaliável com as métricas do **BIT-30** e sem o
reset do **BIT-31** — implementar depois dos dois.

**Fora de escopo:** custo físico/lentidão ao carregar; múltiplos slots; dar comida a ovo/parceiro
(provisionamento); estilização específica do item carregado no frontend — mapeados como futuro.

## Arquivos a tocar

| Arquivo (path relativo à raiz) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/creature.py` | modificar | `held_food`/`is_holding` real/`food_grabbed`; `grab_food`/`drop_food`; consumo+soltar em `update`; soltar em `die`; constante do limiar |
| `backend/simulation/food.py` | modificar | flag `is_held` (pausa TTL, protege de remoção); `to_dict()` ganha `held` (opcional, aditivo) |
| `backend/simulation/engine.py` | modificar | handler de colisão ramifica pegar × comer; TTL pula comida carregada; reposiciona comida carregada na boca a cada step |
| `backend/tests/test_carry_food.py` | criar | testes de pegar/carregar/consumir/soltar/morte |

## Passos de implementação

1. **Constante (topo de `creature.py`, junto das demais):**
   ```python
   HELD_FOOD_CONSUME_ENERGY_FRACTION = 0.5  # abaixo desta fração de energia, consome a comida carregada
   HELD_FOOD_MOUTH_OFFSET = 15.0            # px à frente do centro onde a comida carregada é fixada (~size + FOOD_RADIUS)
   ```

2. **`Creature.__init__` (creature.py, junto de `is_holding` ~163):**
   ```python
   self.is_holding = False   # agora REAL: True enquanto carrega comida (alimenta o Load_Sensor)
   self.held_food = None     # inventário de 1 slot
   self.food_grabbed = 0     # nº de itens pegos na vida (métrica; ver BIT-30)
   ```

3. **`Food.__init__` (food.py):** `self.is_held = False`. E em `Food.to_dict()` acrescentar
   `"held": self.is_held` (aditivo, opcional para o frontend estilizar).

4. **`Creature.grab_food(self, food)` (creature.py):**
   ```python
   def grab_food(self, food):
       """Pega um item: sai do space (vira inventário), TTL pausa, passa a seguir a boca."""
       space = self.engine.physics.space if getattr(self.engine, "physics", None) else None
       if space is not None and food.body in space.bodies:
           space.remove(food.body, food.shape)
       food.is_held = True
       self.held_food = food
       self.is_holding = True
       self.food_grabbed += 1
   ```

5. **`Creature.drop_food(self)` (creature.py):**
   ```python
   def drop_food(self):
       """Solta o item de volta ao mundo na posição atual da criatura; TTL volta a correr."""
       food = self.held_food
       if food is None:
           return
       food.is_held = False
       food.ttl = FOOD_TTL  # (importar de simulation.food) retoma o apodrecimento
       food.body.position = self.body.position
       food.body.velocity = (0, 0)
       space = self.engine.physics.space if getattr(self.engine, "physics", None) else None
       if space is not None and food.body not in space.bodies and food.is_active:
           space.add(food.body, food.shape)
       self.held_food = None
       self.is_holding = False
   ```

6. **`Creature.update` (creature.py):** ao final do método (depois do cálculo de energia/morte), tratar
   a reserva **na ordem: consumir-se-com-fome → soltar-por-sinal-baixo**:
   ```python
   if self.is_holding and self.held_food is not None:
       if self.energy < HELD_FOOD_CONSUME_ENERGY_FRACTION * self.max_energy:
           food = self.held_food
           self.energy = min(self.energy + food.energy_value, self.max_energy)
           self.has_eaten = True
           self.food_eaten += 1          # (BIT-30)
           self.held_food = None
           self.is_holding = False
           food.is_held = False
           food.consume()                # remove definitivamente (já saiu do space no grab)
       elif not self.action_grab_drop:
           self.drop_food()
   ```
   > Se a criatura morreu neste update (`energy <= 0`), o bloco não roda (já está `not is_alive` no topo
   > do próximo tick); a liberação na morte é tratada no passo 7.

7. **`Creature.die` (creature.py):** antes/depois de remover o corpo da criatura, soltar a comida para
   não a perder:
   ```python
   if self.held_food is not None:
       self.drop_food()
   ```
   (Chamar `drop_food()` antes de remover o corpo da criatura do space; a comida é re-adicionada ao space.)

8. **Handler de colisão (engine.py, `_on_creature_food_collision` 54-58):** ramificar pegar × comer:
   ```python
   if food.is_active and creature.is_alive and not food.is_held:
       if creature.action_grab_drop and not creature.is_holding:
           creature.grab_food(food)          # PEGA em vez de comer
       else:
           creature.energy = min(creature.energy + food.energy_value, creature.max_energy)
           creature.has_eaten = True
           creature.food_eaten += 1          # (BIT-30)
           food.consume()
   return True
   ```
   > `not food.is_held` é defensivo: comida carregada saiu do space e não deveria colidir, mas o guard
   > evita qualquer corrida. Preserva o comportamento atual (comer no contato) quando `action_grab_drop`
   > está baixo ou o bibite já carrega — não regride o balanceamento de BIT-20/21/22.

9. **TTL da comida (engine.py, laço 233-238):** não apodrecer a comida carregada:
   ```python
   for food in self.foods:
       if food.is_held:
           continue
       food.ttl -= dt
       if food.ttl <= 0 and food.is_active:
           food.consume()
   ```

10. **Reposicionar a comida carregada (engine.py, no `step`, após atualizar as criaturas ~277):** cada
    criatura viva que carrega fixa a comida na boca (para render e coerência espacial):
    ```python
    for creature in self.creatures:
        if creature.is_alive and creature.is_holding and creature.held_food is not None:
            mx = creature.body.position.x + HELD_FOOD_MOUTH_OFFSET * math.cos(creature.body.angle)
            my = creature.body.position.y + HELD_FOOD_MOUTH_OFFSET * math.sin(creature.body.angle)
            creature.held_food.body.position = (mx, my)
            creature.held_food.body.velocity = (0, 0)
    ```
    (`math` e `HELD_FOOD_MOUTH_OFFSET` já disponíveis; importar a constante de `simulation.creature`.)

11. **Testes (`backend/tests/test_carry_food.py`)** — importar constantes/estado dos módulos, nunca hardcodar:
    - **Pega em vez de comer:** criatura com `action_grab_drop=True`, energia cheia, colide com comida →
      `is_holding` True, `held_food` setado, comida fora de `space.bodies`, energia inalterada, `food_grabbed==1`.
    - **Come normal quando não pega:** `action_grab_drop=False` + contato → energia sobe, comida consumida,
      `is_holding` False (comportamento atual preservado).
    - **TTL pausa carregada:** rodar `step()` por > `FOOD_TTL` s com a comida carregada → comida segue ativa.
    - **Consome na fome:** carregando + energia abaixo de `HELD_FOOD_CONSUME_ENERGY_FRACTION*max` após
      `update` → energia sobe, `is_holding` False, `food_eaten` incrementa.
    - **Solta por sinal:** carregando + `action_grab_drop=False` + energia acima do limiar → `update`
      solta; comida volta ao `space` e `is_holding` False.
    - **Solta na morte:** carregando + energia zerada → após remoção, comida está ativa e de volta no mundo.
    - **Slot único:** já carregando, novo contato não troca o item (segue comendo/ignora, sem sobrescrever `held_food`).
    - `python -c "import main"` OK e `pytest backend/tests/` verde (baseline + novos).

## Contratos técnicos

### Backend (Simulação)
- `Creature`: atributos `is_holding: bool` (agora real), `held_food: Food | None`, `food_grabbed: int`;
  métodos `grab_food(food)`, `drop_food()`. Constantes `HELD_FOOD_CONSUME_ENERGY_FRACTION = 0.5`,
  `HELD_FOOD_MOUTH_OFFSET = 15.0`.
- `Food`: atributo `is_held: bool`; `to_dict()` ganha `"held"` (aditivo).
- `engine._on_creature_food_collision`: ramifica pegar × comer. `step()`: pula TTL de comida carregada
  e reposiciona a comida carregada na boca.
- **I/O do NEAT inalterado** (usa `Action_Grab_Drop`/`Load_Sensor` já existentes; sem seed).

### API/WebSocket
- Nenhuma mensagem/endpoint novo. `foods[]` de `state_update` ganha `held` (aditivo); comida carregada
  aparece na boca do bibite via a posição já reposicionada.

## Critérios de aceite

- [ ] Com `Action_Grab_Drop` ativo e slot livre, o contato com comida **pega** (não come): `is_holding` True, comida sai do space, energia inalterada.
- [ ] `Load_Sensor` reflete `is_holding` (o cérebro passa a receber 1.0 ao carregar).
- [ ] Comida carregada **não apodrece** (TTL pausa) e segue a boca do bibite (renderiza acompanhando).
- [ ] Abaixo do limiar de fome, a reserva é consumida (energia sobe, slot libera); `Action_Grab_Drop` baixo solta a comida no mundo.
- [ ] Bibite que morre carregando **solta** a comida de volta (não some).
- [ ] Comer-no-contato normal permanece intacto quando não se está pegando (sem regressão de balanceamento).
- [ ] `pytest backend/tests/` verde (baseline + novos) e `python -c "import main"` OK.

## Rollback

Reverter a branch BIT-32: deletar `backend/tests/test_carry_food.py`; restaurar `creature.py`
(remover inventário/métodos/constantes, voltar `is_holding` a placeholder), `food.py` (remover
`is_held`/`held`) e `engine.py` (voltar o handler ao comer-imediato, o laço de TTL e remover o
reposicionamento). Nenhum contrato de terceiros é removido (campos eram aditivos).
