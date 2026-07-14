# Spec — BIT-16: Rebalanceamento Energético da Reprodução

**Linear:** N/A
**Risco:** low
**Camada(s):** Backend (Simulação)

---

## Demanda

Criaturas nascem com energia cheia (100%) e só precisam de 50% de energia para acasalar (custando apenas 30%) — ou seja, conseguem se reproduzir sem nunca ter comido, e com sobra. Isso explica o aglomerado de criaturas acasalando sem esforço observado pelo developer, e a ausência de pressão evolutiva real contra comportamentos degenerados (ficar parado, andar em linha reta até bater na parede): sob essas condições, essas estratégias já são "boas o suficiente" para reproduzir. O developer quer o desenho original: nascer com 75% de energia, precisar de 100% para acasalar, custando 50% no processo — forçando a criatura a efetivamente aprender a buscar comida antes de conseguir se multiplicar.

## Abordagem técnica

Endurecer três constantes (energia inicial, limiar e custo da reprodução sexuada) para os valores especificados pelo developer. Como isso torna a via sexuada tão ou mais exigente que a assexuada (BIT-09, desenhada deliberadamente como via "mais difícil, não deve ser dominante"), ajusta-se também `MIN_ENERGY_TO_REPRODUCE_ASEXUALLY`/`ASEXUAL_REPRODUCTION_ENERGY_COST` proporcionalmente, preservando a relação original (limiar igualado ao teto de 100%, já que não dá pra exigir mais que isso; custo mantém o mesmo delta de +20 acima da via sexuada que já existia). Mudança puramente de constantes — nenhuma lógica nova, nenhum contrato de I/O do NEAT ou WebSocket tocado. Validado por grep que nenhum teste fora dos arquivos de reprodução depende do valor de energia inicial atual (100.0); os testes de reprodução importam as constantes em vez de hardcodar valores, então se adaptam automaticamente.

## Arquivos a tocar

| Arquivo (path relativo à raiz do projeto) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/creature.py` | modificar | Nova constante `STARTING_ENERGY = 75.0`; `__init__` usa em vez de `100.0` hardcoded |
| `backend/simulation/engine.py` | modificar | `MIN_ENERGY_TO_MATE` 50→100, `REPRODUCTION_ENERGY_COST` 30→50, `MIN_ENERGY_TO_REPRODUCE_ASEXUALLY` 70→100, `ASEXUAL_REPRODUCTION_ENERGY_COST` 50→70 |

## Passos de implementação

1. **`creature.py`** — junto das outras constantes de módulo (ao lado de `CREATURE_MASS`):
   ```python
   STARTING_ENERGY = 75.0  # 75% de max_energy: crias precisam comer antes de poder se reproduzir
   ```
   No `__init__`, trocar:
   ```python
   self.energy = 100.0
   ```
   por:
   ```python
   self.energy = STARTING_ENERGY
   ```
   `self.max_energy` continua `100.0` (teto inalterado — só o valor inicial muda).

2. **`engine.py`** — atualizar as constantes existentes:
   ```python
   REPRODUCTION_ENERGY_COST = 50.0   # era 30.0
   REPRODUCTION_COOLDOWN = 10.0      # inalterado
   MIN_ENERGY_TO_MATE = 100.0        # era 50.0
   MIN_ENERGY_TO_REPRODUCE_ASEXUALLY = 100.0   # era 70.0 — teto de max_energy, nao da pra exigir mais que a sexuada
   ASEXUAL_REPRODUCTION_ENERGY_COST = 70.0     # era 50.0 — mantem o delta de +20 sobre a sexuada (50+20)
   ASEXUAL_REPRODUCTION_COOLDOWN = 20.0        # inalterado
   ```

3. Rodar a suíte completa (`backend\venv\Scripts\python.exe -m pytest backend/tests/ -v`) e confirmar 100% verde. Por análise estática (grep dos usos de `.energy`/`100.0` em `backend/tests/`), nenhum teste deveria quebrar — mas isso precisa ser confirmado rodando de verdade, não só assumido.

## Contratos técnicos

### Backend (Simulação)
- `Creature.STARTING_ENERGY: float = 75.0` (nova constante de módulo em `creature.py`).
- `Creature.energy` ao nascer passa de `100.0` para `75.0` — afeta uniformemente Gen 0, filhos de reprodução sexuada/assexuada e respawns do Jardim do Éden (mesma lógica de construção em todos os casos, sem caso especial).
- `engine.MIN_ENERGY_TO_MATE: float = 100.0` (era 50.0).
- `engine.REPRODUCTION_ENERGY_COST: float = 50.0` (era 30.0).
- `engine.MIN_ENERGY_TO_REPRODUCE_ASEXUALLY: float = 100.0` (era 70.0).
- `engine.ASEXUAL_REPRODUCTION_ENERGY_COST: float = 70.0` (era 50.0).
- Nenhuma mudança de assinatura de função, nenhuma mudança de protocolo WebSocket, nenhuma mudança no contrato de I/O do NEAT.

## Critérios de aceite

- [ ] Criatura recém-criada (`Creature(engine, ...)`) nasce com `energy == 75.0` (75% de `max_energy`).
- [ ] Reprodução sexuada só ocorre com ambas as criaturas em `energy >= 100.0` (energia cheia).
- [ ] Reprodução sexuada debita `50.0` de energia de cada participante.
- [ ] Reprodução assexuada só ocorre com `energy >= 100.0`.
- [ ] Reprodução assexuada debita `70.0` de energia (mais cara que a sexuada, preservando a via como "mais difícil").
- [ ] `pytest backend/tests/` 100% verde, sem nenhuma alteração necessária nos arquivos de teste (constantes são importadas, não hardcoded).
- [ ] Validação funcional: rodar a simulação por alguns minutos via `manager.py` e observar que criaturas não se reproduzem imediatamente ao nascer — precisam efetivamente ganhar energia (comer) antes de conseguir acasalar ou clonar.

## Rollback

Reverter `creature.py` (`self.energy = 100.0` direto, remover `STARTING_ENERGY`); reverter as 4 constantes em `engine.py` para os valores anteriores (`MIN_ENERGY_TO_MATE=50.0`, `REPRODUCTION_ENERGY_COST=30.0`, `MIN_ENERGY_TO_REPRODUCE_ASEXUALLY=70.0`, `ASEXUAL_REPRODUCTION_ENERGY_COST=50.0`).
