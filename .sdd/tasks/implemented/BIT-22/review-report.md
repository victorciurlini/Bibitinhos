# Review Report — BIT-22: Reprodução Sexuada Emergente

## Veredito
APROVADO

## Resultado dos gates (rodados por mim)
- `import main`: OK
- `pytest tests/`: **127 passed, 6 warnings** (warnings = DeprecationWarning do neat-python, pré-existentes)
- `get_state().width/height` == 1400/1400: OK

### Validação funcional (engine real, 5 min simulados a 30 FPS, pop inicial 10, spies em organic_crossover/clone_genome)
| seed | sexual | asexual | pop_min | pop_max | pop_end |
|-----:|-------:|--------:|--------:|--------:|--------:|
| 1 | 1 | 2 | 1 | 12 | 10 |
| 2 | 2 | 3 | 1 | 14 | 3  |
| 3 | 2 | 8 | 1 | 13 | 5  |

Sexual > 0 e recorrente em TODOS os seeds; nenhuma extinção (pop_min ≥ 1); sem boom-bust (pop_max ~12-14).
Números batem com o relatório do implementer (reproduzi de forma independente).

## Achados

### [OK]
- **Scan sexual O(n²) (engine.py:99-136)**: gates conferem com a spec — ambos ADULT (lista `alive_adults`
  já filtra ADULT+is_alive) + `is_fertile` + `action_mate` + `reproduction_cooldown == 0` +
  `energy >= REPRODUCTION_ENERGY_COST` + distância² `<= radius_sq`. Ao cruzar: deduz custo, seta cooldown,
  zera `is_fertile` de ambos, `organic_crossover`+`mutate_genome`, filho no ponto médio, marca
  `sought_mate_this_frame` em ambos. O `break` fecha o par de 'a' corretamente; como o cooldown de 'a' e 'b'
  é setado no ato, nenhum dos dois reaparece como parceiro válido no restante do frame — sem duplo-acasalamento
  nem pares órfãos. O snapshot `alive_adults` é tirado antes de `update()`, então newborns do frame não entram
  no scan (correto).
- **Handler criatura×criatura REMOVIDO (engine.py:59-61)**: `_on_creature_creature_collision` e seu
  `on_collision(CREATURE, CREATURE, ...)` sumiram. `git grep` confirma: nenhuma referência de código a
  `collided_with_creature_this_frame` nem a `MIN_ENERGY_TO_MATE` sobrou (só menções em comentários/docstrings,
  aceitável). Colisão física entre criaturas segue por elasticidade dos shapes (sem callback).
- **Fertilidade + has_eaten (creature.py:232-237, engine.py:50)**: `has_eaten` setada só no handler de comida;
  `is_fertile` promovida em `update()` (ADULT + has_eaten + energy≥FERTILITY_ENERGY_THRESHOLD=60) e NUNCA
  zerada em `update()` (só no acasalamento). "Comer antes de acasalar" preservado — newborn com has_eaten=False
  não fica fértil mesmo com energia cheia (test_newborn_still_has_to_eat_before_mating cobre).
- **Supressão da assexuada (engine.py:148)**: gate trocado para `sought_mate_this_frame`; como essa flag só é
  marcada em acasalamento BEM-SUCEDIDO, quem só tentou (parceiro inviável) não é bloqueado — a assexuada segue
  como válvula quando sozinho, com energia ≥ MIN_ENERGY_TO_REPRODUCE_ASEXUALLY=100. Verificado nos testes
  test_asexual_suppressed_when_viable_partner_in_range e test_asexual_fires_when_alone_and_full_energy.
- **Mapa 1400 (physics.py:15-16)**: 1400×1400; get_state confirma. Frontend auto-escala (fora de escopo, OK).
- **Divergência (a) food.py energy_value=32.0**: a nota "era 25.0" da tabela da spec estava errada; o valor real
  em disco era 40.0 (BIT-20). O ALVO calibrado da spec é 32.0, aplicado corretamente. Coerente com a economia
  (STARTING_ENERGY 75, custo sexual 30, limiar fertilidade 60). Comentário reflete o valor real.
- **Divergência (b) MATING_RADIUS=150**: subiu de 120 pelo degrau 1 da escada de calibração (documentado na
  spec passo 9). Está na constante do módulo (engine.py:24) e os testes importam `MATING_RADIUS` — nenhum
  hardcode de 150 nos testes de reprodução (o único 150.0 em tests é OASIS_RADIUS, não relacionado).
- **Divergência (c) test_asexual_reproduction.py adaptado**: não estava na lista da spec mas dependia do handler
  removido. A adaptação NÃO enfraqueceu: test_no_asexual_when_viable_partner_is_in_range agora afirma +1 filho
  (sexual) e `not is_fertile` de ambos; test_sexual_reproduction_takes_priority_over_asexual_in_same_frame segue
  provando que só a via sexuada dispara. Ainda pegam regressão real da supressão.
- **Testes reais, não tautológicos**: test_sexual_reproduction.py importa MATING_RADIUS,
  FERTILITY_ENERGY_THRESHOLD, custos e cooldowns (nunca hardcoda). Os testes negativos usam
  `SUB_ASEXUAL_ENERGY = MIN_ENERGY_TO_REPRODUCE_ASEXUALLY - 5` para isolar o gate sexual de um clone assexuado
  mascarando a contagem — isolamento correto e necessário. Cobrem os 6 grupos da spec (has_eaten, persistência,
  proximidade dentro/fora do raio, ambos querem, supressão, piso de sobrevivência).
- **sensors.py**: só comentário obsoleto atualizado; `MATE_ATTRACTION_ENERGY_FRACTION=0.65` (percepção do BIT-21)
  intacto, sem import de constante removida. Contrato NEAT 16/4 inalterado.
- **test_feeding.py:40**: posição de comida realocada 1900→1300 para caber no mapa 1400 (a antiga cairia fora e
  o teste "far apart" ficaria degenerado). Correto.

### [MELHORIA]
- Nenhuma bloqueante nem relevante. (Observação menor, não acionável: a escolha de `has_eaten=False` nas cobaias
  de alguns testes para observar o efeito direto do acasalamento está bem documentada nos comentários dos testes
  e no impl-report; não é um enfraquecimento, pois a re-promoção natural é coberta pelos testes de fertilidade.)

## Resumo
Pode fechar a task. A implementação segue a spec fielmente, todas as 3 divergências do implementer são
justificáveis e verificadas, a suíte está 100% verde (127 passed) e a validação funcional que eu mesmo rodei
confirma reprodução sexuada > 0 e recorrente em todos os seeds, sem extinção nem boom-bust.
