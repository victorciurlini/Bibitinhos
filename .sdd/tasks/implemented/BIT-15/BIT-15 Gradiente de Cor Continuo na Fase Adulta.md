# Spec — BIT-15: Gradiente de Cor Contínuo na Fase Adulta

**Linear:** N/A
**Risco:** low
**Camada(s):** Backend (Simulação)

---

## Demanda

A cor da criatura (introduzida no BIT-10) deveria mudar gradativamente ao longo do tempo, mas na prática os bibites ficam verdes (`#22c55e`, cor fixa) do início ao fim da fase `ADULT` (idade 10 a 30 — a maior parte da vida observável), só voltando a mudar perto da morte (fase `ELDER`, e mesmo assim apenas se a energia cair). Não dá para perceber o tempo passando olhando a cor.

## Abordagem técnica

`compute_life_color()` em `creature.py` tem um `elif age <= 30: rgb = LIFE_COLOR_MATURE` — um valor fixo, sem interpolação, cobrindo 20 unidades de idade. A correção troca esse trecho por uma interpolação contínua de `LIFE_COLOR_MATURE` até `LIFE_COLOR_ELDER_START` ao longo dessa mesma faixa (10→30), usando o `_lerp_rgb` já existente no arquivo — mesmo padrão já usado no ramo `EGG→MATURE` (idade 2-10). Validado numericamente que a transição fica contínua na fronteira `age == 30`: o novo ramo termina exatamente em `LIFE_COLOR_ELDER_START`, o mesmo valor que o ramo `ELDER` já produz quando `energy_fraction == 1.0` — sem salto perceptível de cor ao cruzar de `ADULT` para `ELDER` com energia cheia. A transição cinza→quase-preto por energia (fase `ELDER`, decisão original do BIT-10) não muda.

Fora de escopo: `compute_visual_scale()` tem o mesmo padrão de plateau fixo em `age <= 30`, mas o developer só reportou o problema de cor — tamanho fica para uma task futura se for pedido.

## Arquivos a tocar

| Arquivo (path relativo à raiz do projeto) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/creature.py` | modificar | `compute_life_color()`: plateau fixo vira interpolação contínua |
| `backend/tests/test_creature_life_visuals.py` | modificar | Substituir teste que valida o plateau (o bug) por teste de variação contínua |

## Passos de implementação

1. **`creature.py`** — em `compute_life_color()`, trocar:
   ```python
   elif age <= 30:
       rgb = LIFE_COLOR_MATURE
   ```
   por:
   ```python
   elif age <= 30:
       t = (age - 10) / 20.0
       rgb = _lerp_rgb(LIFE_COLOR_MATURE, LIFE_COLOR_ELDER_START, t)
   ```
   Atualizar a docstring da função (linha 1: `"""Azul (0-2) -> verde (2-10, flat 10-30) -> cinza/preto por energia (30+)."""`) para remover a menção a "flat 10-30", já que deixa de ser plateau:
   ```python
   """Azul (0-2) -> verde (2-10) -> verde->cinza continuo (10-30) -> cinza/preto por energia (30+)."""
   ```

2. **`test_creature_life_visuals.py`** — remover `test_mature_plateau_stays_green_between_ten_and_thirty` (codifica o bug) e adicionar em seu lugar:
   ```python
   def test_mature_to_elder_color_changes_continuously_between_ten_and_thirty(self):
       samples = [compute_life_color(age=age, energy=100, max_energy=100) for age in (10, 15, 20, 25, 30)]
       assert len(set(samples)) == len(samples)  # nenhum valor repetido: sempre mudando
       assert samples[0] == '#22c55e'  # ponto de partida inalterado
       assert samples[-1] == '#6b7280'  # termina exatamente onde o ramo ELDER (energia cheia) comeca
   ```
   `test_age_ten_is_pure_green` e `test_elder_start_full_energy_is_gray` continuam válidos sem alteração (pontos de fronteira inalterados).

3. Rodar a suíte completa (`backend\venv\Scripts\python.exe -m pytest backend/tests/ -v`) e confirmar 100% verde.

## Contratos técnicos

### Backend (Simulação)
- `compute_life_color(age: float, energy: float, max_energy: float) -> str` — mesma assinatura e tipo de retorno (hex string), só a lógica interna do ramo `10 < age <= 30` muda de constante fixa para interpolação.
- Nenhuma mudança de contrato WebSocket/`to_dict()` — o campo `color` continua sendo uma hex string, só os valores intermediários passam a variar de fato.

## Critérios de aceite

- [ ] `compute_life_color(age=10, ...)` continua `#22c55e` (ponto de partida inalterado).
- [ ] `compute_life_color(age=30, energy=100, max_energy=100)` é `#6b7280` (mesmo valor do ramo `ELDER` com energia cheia — sem salto na fronteira).
- [ ] Amostras de cor em idades 10, 15, 20, 25, 30 (energia cheia) são todas distintas entre si — nenhum plateau.
- [ ] `pytest backend/tests/test_creature_life_visuals.py` 100% verde.
- [ ] Nenhuma regressão: suíte completa (`pytest backend/tests/`) 100% verde.
- [ ] Validação visual manual (via `manager.py` → frontend): observar uma criatura por alguns minutos e confirmar que a cor deriva perceptivelmente de verde para acinzentado ao longo da fase adulta, não só perto da morte.

## Rollback

Reverter `compute_life_color()` para `elif age <= 30: rgb = LIFE_COLOR_MATURE`; reverter a docstring; restaurar `test_mature_plateau_stays_green_between_ten_and_thirty` em `test_creature_life_visuals.py`.
