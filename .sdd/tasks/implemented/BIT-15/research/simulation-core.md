## Arquivos relevantes

- `backend/simulation/creature.py` — `compute_life_color()` (linhas 54-64), `_lerp_rgb`/`_rgb_to_hex` (helpers puros), `Creature.to_dict()` (usa `compute_life_color` para o campo `color`)
- `backend/tests/test_creature_life_visuals.py` — testes do BIT-10, incluindo `test_mature_plateau_stays_green_between_ten_and_thirty`, que **codifica o próprio bug reportado** como comportamento esperado

## Conteúdo relevante para a demanda

### Bug confirmado lendo o código atual

```python
def compute_life_color(age, energy, max_energy):
    """Azul (0-2) -> verde (2-10, flat 10-30) -> cinza/preto por energia (30+)."""
    if age <= 10:
        t = max(0.0, (age - 2) / 8.0) if age > 2 else 0.0
        rgb = _lerp_rgb(LIFE_COLOR_EGG, LIFE_COLOR_MATURE, t)
    elif age <= 30:
        rgb = LIFE_COLOR_MATURE          # <-- FLAT: verde puro fixo por 20 unidades de idade
    else:
        energy_fraction = max(0.0, min(1.0, energy / max_energy))
        rgb = _lerp_rgb(LIFE_COLOR_DEATH, LIFE_COLOR_ELDER_START, energy_fraction)
    return _rgb_to_hex(rgb)
}
```

A própria docstring já documentava o plateau ("flat 10-30") como decisão deliberada do BIT-10 original. `LifeStage.ADULT` cobre exatamente essa faixa (`age > 10` até `age > 30` vira `ELDER`), ou seja, a criatura passa toda a fase adulta — tipicamente a maior parte da vida observável, já que o metabolismo ADULT (0.8/s) é o dobro do JUVENILE — com a cor **idêntica**, pixel a pixel (`#22c55e`), sem nenhuma variação perceptível. Depois dos 30, a transição cinza→preto é conduzida só por `energy_fraction` (decisão original do BIT-10, para ligar o visual à causa real da morte) — mas se a criatura mantém energia alta durante o ELDER, também não há mudança perceptível de cor ali. Resultado combinado: o developer via a criatura "verde até morrer", exatamente o relato.

Validei numericamente (script Python real) que trocar o `elif age <= 30: rgb = LIFE_COLOR_MATURE` por uma interpolação contínua de `LIFE_COLOR_MATURE` até `LIFE_COLOR_ELDER_START` ao longo de `age` 10→30 produz uma sequência de hex distintos a cada passo, batendo exatamente com `LIFE_COLOR_ELDER_START` (`#6b7280`) em `age == 30` — mesmo valor que o ramo ELDER já produz quando `energy_fraction == 1.0`, então a transição fica contínua na fronteira (sem salto perceptível em `age == 30`).

### `compute_visual_scale` tem o mesmo padrão de plateau (fora de escopo)

`compute_visual_scale()` (linhas 67-78) tem exatamente a mesma estrutura de 3 zonas com plateau em `age <= 30 → VISUAL_SCALE_ADULT` fixo. O developer só reportou o problema de **cor**, não de tamanho — mantenho o scale intocado nesta task, mas registro a observação para uma possível task futura equivalente.

### Testes que codificam o bug (precisam mudar)

`test_creature_life_visuals.py::TestComputeLifeColor::test_mature_plateau_stays_green_between_ten_and_thirty` afirma explicitamente que idades 10, 15, 20, 25, 30 devem retornar o mesmo hex — esse teste será substituído por um que verifica variação monotônica/contínua na mesma faixa.

## O que precisa ser feito

1. Substituir o ramo `elif age <= 30: rgb = LIFE_COLOR_MATURE` por uma interpolação contínua `LIFE_COLOR_MATURE -> LIFE_COLOR_ELDER_START` ao longo de `age` 10-30 (mesmo padrão de `_lerp_rgb` já usado nos outros ramos).
2. Atualizar a docstring de `compute_life_color` (não é mais "flat 10-30").
3. Substituir `test_mature_plateau_stays_green_between_ten_and_thirty` por um teste que confirma variação contínua/monotônica na faixa 10-30, seguindo o padrão de `test_egg_to_mature_interpolates_between_two_and_ten` já existente no mesmo arquivo.
4. Confirmar que `test_age_ten_is_pure_green` (`age=10 → #22c55e`) continua válido (é o ponto de partida da nova interpolação, valor inalterado) e que a fronteira `age=30, energy=100` bate com `test_elder_start_full_energy_is_gray` (`#6b7280`) — já é o caso, validado numericamente.

## Perguntas em aberto

Nenhuma — fórmula de interpolação validada numericamente contra o código real; escopo confirmado como só a cor (não o tamanho).
