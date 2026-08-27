# Research — simulation-core (BIT-33: Reprodução na Velhice / ELDER Fértil)

> Relatório do orquestrador (arquivos lidos/validados diretamente na sessão, §84 do protocolo).

## Achado (originado por observação do usuário)

Um bibite que atinge **ELDER** (idade > 30, `creature.py:191`) fica **reprodutivamente estéril**. A
esterilidade é imposta em quatro pontos, todos gateando em `LifeStage.ADULT`:

1. **Fertilidade (`creature.py:235`):** `if (self.life_stage == LifeStage.ADULT and self.has_eaten and
   self.energy >= FERTILITY_ENERGY_THRESHOLD): self.is_fertile = True`. Um ELDER **nunca** vira fértil.
   (E se já era fértil como ADULT, ao mudar de estágio ele continua `is_fertile=True`, mas o gate do
   pool sexuado abaixo ainda o exclui.)
2. **Pool sexuado (`engine.py:174`):** `alive_adults = [c for c in self.creatures if c.is_alive and
   c.life_stage == LifeStage.ADULT]` — ELDER fora do acasalamento por proximidade.
3. **Assexuado (`engine.py:220`):** `if creature.life_stage != LifeStage.ADULT: continue` — ELDER não clona.
4. **Percepção de parceiro (`sensors.py:73`):** `is_adult = creature.life_stage == LifeStage.ADULT`;
   governa `mate_signal`/`creature_sign` — um ELDER não vê parceiros como atrativos nem é "cortejável".

Resultado: a janela reprodutiva é **só o estágio ADULT (idade 10–30, ~20 s)**. Como o ELDER queima
`2.0 E/s` (`creature.py:59`, o metabolismo mais alto), ele morre relativamente rápido — mas enquanto
vive, não contribui geneticamente.

## Bug ou intenção?

Nada na base documenta uma "menopausa" deliberada. Os comentários de metabolismo só falam de
`longevidade como métrica emergente (ELDER degrada mais rápido)` — pressão de sobrevivência, não
esterilidade. O gate `== ADULT` aparenta ser default incidental de quando a reprodução (Épico 2) foi
escrita, não uma regra de rotatividade geracional pensada. **Conclui-se: esterilidade não-intencional.**

Além disso, é **inconsistente com a trilha evolutiva**: o BIT-31 (hall of fame) premia longevidade
como proxy de fitness, mas a longevidade leva ao ELDER, que não gera descendência — os dois objetivos
se anulam. Deixar o ELDER fértil alinha "viver muito" com "deixar mais genes".

## Decisão de design (para a spec; usuário pode vetar)
- **Maturidade reprodutiva = idade > 10 (ADULT **ou** ELDER)**, sem teto de esterilidade. JUVENILE
  segue impedido (precisa amadurecer). Muda os quatro gates de `== ADULT` para `in (ADULT, ELDER)`.
- **Sem penalidade de senescência** neste BIT (mesmas regras de custo/cooldown para ADULT e ELDER). O
  auto-limite natural é o metabolismo 2.0/s do ELDER (vida curta ⇒ menos partos). Penalidade
  (fertilidade reduzida / custo maior no ELDER) fica mapeada como polimento futuro.

## Arquivos a tocar
- `backend/simulation/creature.py` (gate de fertilidade, linha 235)
- `backend/simulation/engine.py` (pool sexuado 174; assexuado 220)
- `backend/simulation/sensors.py` (percepção de parceiro 73-84)
- `backend/tests/test_elder_reproduction.py` (novo)

## Impacto em testes existentes
Os testes de reprodução setam `life_stage = LifeStage.ADULT` explicitamente e continuam válidos. Não
há teste que afirme "ELDER não reproduz" (grep confirmou), então não há regressão a acomodar — só
somar cobertura nova para o caso ELDER.

## Sem mudança de contrato
- I/O do NEAT inalterado; protocolo WebSocket inalterado. Muda só a elegibilidade por estágio.

## Perguntas em aberto (resolvidas)
- Rotatividade geracional some? Não: o metabolismo alto do ELDER já limita naturalmente; e a métrica
  de geração (BIT-30) permite observar se linhagens velhas dominam — se dominarem demais, aí sim entra
  uma penalidade de senescência (futuro).
