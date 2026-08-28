# Spec — BIT-33: Reprodução na Velhice (ELDER Fértil)

**Linear:** N/A
**Risco:** medium
**Camada(s):** Backend (Simulação)

---

## Demanda

Corrigir a **esterilidade não-intencional do estágio ELDER**. Hoje um bibite que passa de 30 s de idade
(ELDER) não consegue mais reproduzir: os quatro gates de reprodução (fertilidade, pool sexuado,
assexuado e percepção de parceiro) exigem `LifeStage.ADULT`, deixando a janela reprodutiva restrita a
~20 s. Isso é incoerente com a trilha evolutiva — o hall of fame (BIT-31) premia longevidade como proxy
de fitness, mas viver muito leva ao ELDER estéril, anulando o incentivo. A correção estende a
maturidade reprodutiva a **ADULT e ELDER** (idade > 10), mantendo JUVENILE impedido.

## Abordagem técnica

Trocar os quatro gates de `== LifeStage.ADULT` para `in (LifeStage.ADULT, LifeStage.ELDER)`:
fertilidade (`creature.py`), pool de acasalamento sexuado e loop assexuado (`engine.py`) e percepção de
parceiro (`sensors.py`). Sem penalidade de senescência (mesmas regras de custo/cooldown) — o
auto-limite é o metabolismo alto do ELDER (2.0 E/s), que encurta a vida e naturalmente reduz o número
de partos. **Sem mudança no I/O do NEAT nem no protocolo WebSocket.**

**Decisão de rumo (usuário pode vetar):** removemos o teto de esterilidade em vez de mantê-lo como
"menopausa" de rotatividade — a esterilidade aparenta ser default incidental do Épico 2, não regra
pensada, e alinhar longevidade↔descendência é mais coerente com o objetivo evolutivo. Penalidade de
senescência (fertilidade reduzida / custo maior no ELDER) fica mapeada como polimento futuro.

**Independência:** não depende de código do BIT-30/31/32, mas a métrica de geração do BIT-30 é o que
permitirá observar se linhagens velhas passam a dominar (e se então uma senescência é necessária).

## Arquivos a tocar

| Arquivo (path relativo à raiz) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/creature.py` | modificar | gate de fertilidade aceita ELDER (linha ~235) |
| `backend/simulation/engine.py` | modificar | pool sexuado (~174) e loop assexuado (~220) aceitam ELDER |
| `backend/simulation/sensors.py` | modificar | percepção de parceiro (~73-84) considera ELDER maduro |
| `backend/tests/test_elder_reproduction.py` | criar | cobre ELDER fértil, acasalando (sexuado) e clonando (assexuado) |

## Passos de implementação

1. **`creature.py` (gate de fertilidade, ~235):**
   ```python
   if (self.life_stage in (LifeStage.ADULT, LifeStage.ELDER) and self.has_eaten
           and self.energy >= FERTILITY_ENERGY_THRESHOLD):
       self.is_fertile = True
   ```

2. **`engine.py` (pool sexuado, ~173-174):** incluir ELDER no conjunto elegível:
   ```python
   alive_breeders = [c for c in self.creatures
                     if c.is_alive and c.life_stage in (LifeStage.ADULT, LifeStage.ELDER)]
   ```
   (Renomear `alive_adults` → `alive_breeders` para clareza; ajustar as referências `a`/`b` do laço que
   iteram sobre essa lista. Se preferir minimizar o diff, manter o nome e só trocar o filtro — a spec
   aceita as duas formas, desde que o filtro passe a incluir ELDER.)

3. **`engine.py` (loop assexuado, ~220):**
   ```python
   if creature.life_stage not in (LifeStage.ADULT, LifeStage.ELDER):
       continue
   ```

4. **`sensors.py` (percepção de parceiro, ~73-84):** trocar `is_adult` por `is_mature` cobrindo ELDER;
   o sinal de atração e a neutralização de repulsão passam a valer para ELDER também:
   ```python
   is_mature = creature.life_stage in (LifeStage.ADULT, LifeStage.ELDER)
   ...
   observer_ready_to_mate = (
       is_mature
       and energy_fraction >= MATE_ATTRACTION_ENERGY_FRACTION
       and creature.reproduction_cooldown <= 0.0
   )
   mate_signal = energy_fraction if is_mature else 0.0
   ```
   (Renomear a variável local; nenhum outro módulo a importa.)

5. **Testes (`backend/tests/test_elder_reproduction.py`)** — importar estágios/constantes dos módulos:
   - **ELDER vira fértil:** criatura `life_stage=ELDER`, `has_eaten=True`, energia ≥
     `FERTILITY_ENERGY_THRESHOLD`, após `update` → `is_fertile is True`.
   - **Acasalamento sexuado com ELDER:** dois bibites `ELDER` (ou um ELDER + um ADULT) férteis, com
     `action_mate`, dentro de `MATING_RADIUS`, energia ≥ `REPRODUCTION_ENERGY_COST`, fora de cooldown →
     `step()` gera um filho e aplica custo/cooldown a ambos (mesmo padrão de `test_sexual_reproduction.py`).
   - **Clonagem assexuada com ELDER:** ELDER com energia ≥ `MIN_ENERGY_TO_REPRODUCE_ASEXUALLY`,
     `action_mate`, sem parceiro → `step()` gera clone (padrão de `test_asexual_reproduction.py`).
   - **JUVENILE segue impedido:** `life_stage=JUVENILE` fértil-tentando → nenhum filho (guarda anti-regressão).
   - `python -c "import main"` OK e `pytest backend/tests/` verde (baseline + novos).

## Contratos técnicos

### Backend (Simulação)
- Elegibilidade reprodutiva passa de `== LifeStage.ADULT` para `in (LifeStage.ADULT, LifeStage.ELDER)`
  nos quatro pontos: fertilidade (`creature.py`), pool sexuado e loop assexuado (`engine.py`),
  percepção de parceiro (`sensors.py`).
- Nenhuma constante, assinatura pública, contrato de I/O do NEAT ou mensagem WebSocket é alterada.

## Critérios de aceite

- [ ] Um bibite ELDER com energia/histórico suficientes **vira fértil** e **reproduz** (sexuado e assexuado).
- [ ] ELDERs se percebem/atraem como parceiros (o `sensors` trata ELDER como maduro).
- [ ] JUVENILE continua **não** podendo reproduzir (sem regressão do "amadurecer antes").
- [ ] Custos/cooldowns de reprodução aplicam-se ao ELDER como ao ADULT (sem regra especial neste BIT).
- [ ] `pytest backend/tests/` verde (baseline + novos) e `python -c "import main"` OK.

## Rollback

Reverter a branch BIT-33: deletar `backend/tests/test_elder_reproduction.py`; restaurar os quatro
gates para `== LifeStage.ADULT` em `creature.py`, `engine.py` (duas ocorrências) e `sensors.py`.
