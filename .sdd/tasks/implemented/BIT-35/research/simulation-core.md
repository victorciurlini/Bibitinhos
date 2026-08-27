# Research — BIT-35: Simulação Core (Evolução e Sobrevivência)

## Arquivos relevantes

- `backend/simulation/creature.py` — constantes de energia, metabolismo, ociosidade, ciclo de vida
- `backend/simulation/engine.py` — reprodução, Hall of Fame, Eden, pressão adaptativa
- `backend/simulation/oasis.py` — spawn de comida, TTL de oásis, caps globais
- `backend/simulation/params.py` — 22 parâmetros ajustáveis em runtime (UI)
- `backend/simulation/sensors.py` — percepção (apenas referência)

---

## Diagnóstico das Extinções Frequentes

### Balanço energético desfavorável

| Custo | Valor atual |
|---|---|
| Metabolismo ADULT | 0.8 E/s |
| Metabolismo ELDER | 2.0 E/s |
| Penalidade de ociosidade | 1.2 E/s (quando parada) |
| Propulsão a full thrust | 0.6 E/s |
| Energia inicial | 75.0 (75% do max) |
| Energia de comida | 32.0 E/item |

Com metabolismo 0.8 E/s + ociosidade 1.2 E/s, uma criatura parada queima 2.0 E/s.
Sem comida, sobrevive ~37s do nascimento (75 / 2.0). Com comida a cada ~15s, sobrevive.
O problema: oásis têm TTL de 15-40s e a busca exige exploração.

### Reprodução sexuada rara

Barreiras simultâneas:
1. `MATING_RADIUS = 150px` em mapa 1400×1400 (densidade baixa)
2. Ambos ADULT/ELDER + férteis + `action_mate=True` + cooldown=0 + energia ≥ 30
3. Cooldown de 10s após cada acasalamento
4. Fertilidade requer: ter comido + energia ≥ 60 (com metabolismo alto, cai rapidamente)

### Eden ativa tarde demais

`EDEN_POPULATION_THRESHOLD = 10`: com 11 criaturas, sem segurança.
Quando chega em 10, já pode ser tarde para evitar extinção em cascata.

### Hall of Fame pequeno

`HALL_OF_FAME_SIZE = 12`: genomas bons se perdem em extinções rápidas.
Score atual = age + 20 × children (não considera habilidade de caçar comida).

---

## Diagnóstico da Evolução Lenta

### Seeds de Gen-0 muito fortes

Em `rtneat_wrapper.py.create_zero_genome()`:
- `MOTOR_FORWARD_SEED_BIAS`: 0.3-1.0 → 100% nasce andando
- `FOOD_TAXIS_STEER_GAIN`: 1.0 → 97% vira para comida
- `ACTION_MATE_SEED_BIAS`: 1.5-2.5 → 93-99% adultos acasalam

Com seeds tão fortes, criaturas Gen-0 já funcionam bem. A seleção não tem o que melhorar
porque os nasce "quase ótimas" do ponto de vista de sobrevivência básica.

### Sem pressão de seleção direcional

rtNEAT orgânico não usa `neat.Population.run()` — evolução ocorre apenas por
crossover nos eventos de reprodução. Sem fitness explícito, qualquer par de adultos férteis
se reproduz com igual probabilidade, independente de quão bom é o genoma.

### Mutação sem direção

`weight_mutate_rate = 0.8` (80%) é alto para o modelo orgânico: em pop pequena (<20),
cada geração sofre grande drift genético sem pressão para convergir em direção a comportamentos
melhores.

---

## Mecanismo Proposto: Pressão Adaptativa de População

Implementar multiplier de spawn de comida baseado na população atual:

```python
# Zonas de pressão (constantes em engine.py):
LOW_POP_THRESHOLD = 15   # abaixo → comida abundante (suporte à recuperação)
HIGH_POP_THRESHOLD = 50  # acima → comida escassa (pressão de seleção)

def _food_multiplier(population: int) -> float:
    if population < LOW_POP_THRESHOLD:
        return 1.5   # 50% mais comida → recuperação rápida
    elif population > HIGH_POP_THRESHOLD:
        return 0.75  # 25% menos comida → seleção mais intensa
    return 1.0
```

Este mecanismo cria homeostase ecológica real: população baixa → mais comida → recuperação;
população alta → menos comida → seleção dos mais aptos.

---

## Parâmetros de params.py Relevantes (valores atuais)

### Energia
- `idle_penalty_rate`: 1.2
- `motor_forward_cost`: 0.6
- `spin_cost`: 1.0
- `metabolism_adult`: 0.8
- `metabolism_elder`: 2.0

### Reprodução
- `fertility_energy_threshold`: 60.0
- `mating_radius`: 150.0
- `reproduction_energy_cost`: 30.0
- `reproduction_cooldown`: 10.0
- `min_energy_asexual`: 100.0
- `asexual_energy_cost`: 95.0
- `asexual_cooldown`: 45.0

### Ecossistema
- `max_total_food`: 110
- `food_energy_value`: 32.0
- `oasis_spawn_chance`: 0.01
- `oasis_food_spawn_chance`: 0.18
- `max_active_oases`: 6
- `oasis_ttl_min`: 15.0
- `oasis_ttl_max`: 40.0

---

## Perguntas em Aberto

1. `creature.py` lê metabolismo do `METABOLISM_RATE_BY_STAGE` dict constante ou de `params.metabolism_adult`?
   → Verificar `creature.update()` — se usa o dict, mudar o dict E o default em params.py.

2. `oasis.py` lê `oasis_food_spawn_chance` de params em runtime ou como constante?
   → Verificar `maybe_spawn_food()` em oasis.py.

3. A mudança em seeds de Gen-0 (enfraquecer food-taxis) deve entrar em BIT-35 ou em BIT separado?
   → **Decisão: OUT do BIT-35** — risco de extinguir população durante a mudança da seed;
   endereçar em BIT posterior após estabilidade ecológica estar garantida.
