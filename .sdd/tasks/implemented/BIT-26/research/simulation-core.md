# Research — simulation-core (BIT-26: Painéis de métricas populacionais)

> Relatório do sub-agente Explore sobre `backend/simulation/` para a demanda de métricas populacionais.

## Arquivos relevantes
- `backend/simulation/engine.py` (linhas 45-333)
- `backend/simulation/creature.py` (linhas 111-265)
- `backend/simulation/oasis.py` (linhas 1-43)
- `backend/models.py` (linhas 6-15)
- `backend/main.py` (linhas 47, 81-109)

## Conteúdo relevante

**Estado mantido no engine:**
- `SimulationEngine.creatures`: list de objetos `Creature` (vivos apenas)
- `SimulationEngine.foods`: list de objetos `Food` (ativos apenas)
- `SimulationEngine.oases`: list de objetos `Oasis` (TTL > 0)
- `SimulationEngine.time_elapsed`: tempo total em segundos (acumula a cada `step(dt)`)
- `SimulationEngine.current_generation`: inteiro monotônico (sempre = 1 no código atual, nunca incrementa)
- `SimulationEngine._next_genome_id`: contador monotônico (incrementa em cada reprodução sexuada/assexuada)

**Contadores deriváveis já implementados em `to_dict()` na serialização de cada criatura** (creature.py:245-264):
- `id`: genome.key (único e monotônico)
- `age`: segundos de vida
- `life_stage`: LifeStage enum (EGG, JUVENILE, ADULT, ELDER)
- `energy`, `max_energy`: valores de energia correntes
- `reproduction_cooldown`: tempo até próxima reprodução permitida
- `vision[]`: array de 9 valores [0..1] (valores dos 9 setores visuais)
- `motor_forward`, `motor_torque`: outputs da rede neural
- `action_mate`, `action_grab_drop`: booleanos de ação

**Histórico de reprodução (rastreável mas não persistido):**
- Cada criatura tem `id == genome.key`, criado via `engine.next_genome_id()`
- `engine._next_genome_id` é incrementado a cada filho (sexual ou assexual) em `step()` (linhas 191, 223)
- Permite reconstruir "árvore genealógica" se IDs forem salvos ao longo do tempo
- Sem histórico de séries temporais implementado hoje — cada `step()` produz apenas snapshot via `engine.get_state()` (linhas 319-333)

**Dados de população vivos no `get_state()` (engine.py:319-333):**
```python
"creatures": [c.to_dict() for c in self.creatures],  # população total = len(creatures)
"foods": [f.to_dict() for f in self.foods],           # comida disponível
"oases": [o.to_dict() for o in self.oases],           # número e distribuição de oases
"time": self.time_elapsed,
"generation": self.current_generation,
"width", "height", "vision_radius", "vision_fov_degrees"
"params": get_params(self)  # todos os 20+ parâmetros tunáveis
```

**Métricas calculáveis online a partir do snapshot:**
1. População total: `len(engine.creatures)`
2. Distribuição por fase de vida: contagem de `c.life_stage == JUVENILE/ADULT/ELDER` (EGG implícito)
3. Energia média/total
4. Idade média/máxima/mínima
5. Taxa de morte: contagem de remoções em `step()` (linhas 279-286) — hoje apenas implícita
6. Taxa de nascimento: contagem de `sexual_children` + `asexual_children` criadas em `step()` (linhas 162-231)
7. Proporção sexual/assexual
8. Distribuição de comida: contagem e TTL médio de `Food`
9. Oasis ativos: `len(engine.oases)`
10. Eficiência metabólica (exige histórico)

**O que NÃO existe ainda:**
- Séries temporais (histórico de snapshots)
- Rastreamento de "espécies NEAT" (neat-python 0.92 oferece especiação via `DefaultSpeciesSet`, mas não é usado — rtNEAT orgânico sem PopulationManager)
- Contador de nascimentos/mortes incrementais
- Árvore genealógica ou ligação parent→offspring explícita
- Persistência em BD (models.py define `GenomeModel` com campos básicos mas não é usado no engine)

## O que precisa ser feito

1. **Criar `PopulationMetrics`** para capturar snapshot de métricas a cada tick:
   - Campos: `timestamp`, `time_elapsed`, `population_count`, `births_this_frame`, `deaths_this_frame`, `stage_distribution`, `energy_stats`, `age_stats`, etc.
   - Método `from_engine(engine)` para construir snapshot do estado corrente
2. **Estender `SimulationEngine`** com:
   - `_births_this_frame`, `_deaths_this_frame`: contadores por `step()`
   - `metrics_history`: deque de snapshots (ou integração com BD)
3. **Integrar captura de histórico** em `engine.step()`:
   - Antes de remover criaturas mortas, contar quantas serão removidas
   - Contar nascimentos (len(sexual_children) + len(asexual_children))
   - Criar snapshot ao final do step
4. **Expor métricas via `engine.get_state()`** ou novo endpoint `/metrics`:
   - Campo `metrics` com agregados; opcionalmente histórico resumido (últimas N) para gráficos
5. **Rastreamento de "geração"** (opcional): `creature.generation` = geração em que nasceu; `current_generation` hoje está preso em 1

## Perguntas em aberto
1. Como `current_generation` deveria avançar? (rtNEAT orgânico não tem gerações discretas)
2. Persistir histórico em SQLite (models.py) ou manter em memória (deque)?
3. Rastrear "espécies NEAT"? (exigiria `DefaultSpeciesSet` ou especiação customizada)

## Dependências
Sem bloqueadores mútuos com BIT-27/BIT-28. Nota do agente: um `SimulationRunner` (proposto no research do BIT-28) poderia ser reutilizado, mas as métricas podem viver no próprio engine sem depender dele.
