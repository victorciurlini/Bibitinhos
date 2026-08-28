# Spec — BIT-36: Camadas Ocultas na Rede Neural

**Linear:** N/A
**Risco:** low
**Camada(s):** Backend (Simulação)

---

## Demanda

A rede neural atual tem topologia flat: 16 inputs → 4 outputs sem camadas intermediárias (`num_hidden=0`). Uma rede sem nós ocultos é uma função linear dos inputs — não consegue aprender representações internas nem estratégias condicionais complexas (ex: "girar quando comida está nas bordas E velocidade é baixa"). Adicionar 2 nós ocultos na Gen-0 permite que a evolução construa circuitos mais ricos ao longo das gerações, sem alterar o contrato de I/O.

## Abordagem técnica

Alterar `neat_config.ini` para `num_hidden = 2`, mantendo `initial_connection = full_direct`. Com essa combinação, o neat-python 0.92 gera na Gen-0: 16×6=96 conexões input→{output,hidden} + 2×4=8 conexões hidden→output = 104 conexões totais, com os nós ocultos nas chaves 4 e 5. Atualizar o teste `test_create_zero_genome_is_fully_connected` para refletir as novas contagens (104 conexões, 6 nós). Nenhuma outra alteração é necessária — `rtneat_wrapper.py`, `sensors.py` e `creature.py` permanecem intocados.

## Arquivos a tocar

| Arquivo | Alteração | Descrição |
|---|---|---|
| `backend/simulation/neat_config.ini` | Editar | `num_hidden`: 0 → 2 |
| `backend/tests/test_rtneat_wrapper.py` | Editar | Atualizar contagens hardcoded em `test_create_zero_genome_is_fully_connected` |

## Passos de implementação

1. **Editar `backend/simulation/neat_config.ini`** — alterar a linha `num_hidden`:

   ```ini
   # antes:
   num_hidden               = 0

   # depois:
   num_hidden               = 2
   ```

   Deixar `initial_connection = full_direct` inalterado. O comentário na linha acima também deve ser atualizado:

   ```ini
   # antes:
   # full_direct + num_hidden=0 => Geracao 0 com conexoes diretas input->output (16x4=64)

   # depois:
   # full_direct + num_hidden=2 => Geracao 0: 16x6=96 conex input->{output,hidden} + 2x4=8 hidden->output = 104 total
   ```

2. **Editar `backend/tests/test_rtneat_wrapper.py`** — atualizar `test_create_zero_genome_is_fully_connected`:

   ```python
   # antes:
   def test_create_zero_genome_is_fully_connected():
       config = load_neat_config()
       genome = create_zero_genome(1, config)
       assert len(genome.connections) == 64
       assert len(genome.nodes) == 4

   # depois:
   def test_create_zero_genome_is_fully_connected():
       config = load_neat_config()
       genome = create_zero_genome(1, config)
       # num_hidden=2, full_direct: 16x6 input->{output,hidden} + 2x4 hidden->output = 104
       assert len(genome.connections) == 104
       # 4 outputs + 2 hidden = 6 (inputs sao implicitos no neat-python 0.92)
       assert len(genome.nodes) == 6
   ```

3. **Invalidar o cache de config** — `load_neat_config()` usa `_config_cache` indexado por path. Em testes, como cada sessão pytest parte de um processo limpo, o cache não acumula estado entre runs. Nenhuma ação adicional necessária.

4. **Rodar o gate de qualidade** após as edições:

   ```powershell
   cd backend
   venv\Scripts\python.exe -c "from main import app; print('import ok')"
   venv\Scripts\pytest.exe tests/ -x -q
   ```

   Todos os 7 testes de `test_rtneat_wrapper.py` devem passar. O restante da suite não é afetado pela mudança.

## Contratos técnicos

### Backend (Simulação)

**Configs alteradas:**

| Parâmetro | Valor antigo | Valor novo |
|---|---|---|
| `num_hidden` | `0` | `2` |
| `initial_connection` | `full_direct` | `full_direct` (inalterado) |

**Impacto na estrutura de genomas da Gen-0:**

| Propriedade | Antes | Depois |
|---|---|---|
| `len(genome.nodes)` | 4 | 6 |
| `len(genome.connections)` | 64 | 104 |
| Chaves de nós ocultos | — | 4, 5 |
| Conexões input→output | 64 | 64 (preservadas) |
| Conexões input→hidden | 0 | 32 (16×2) |
| Conexões hidden→output | 0 | 8 (2×4) |

**Contrato de I/O da rede (inalterado):**
- `net.activate(inputs)` recebe lista de 16 floats, retorna lista de 4 floats
- Seeds BIT-20 (Motor_Forward bias) e BIT-21 (food-taxis, Action_Mate bias) continuam operando nas mesmas chaves de nós (0, 1, 3) e nas mesmas chaves de conexão `(-(i+1), 1)` — não afetados

**`genome_to_dict()`:** já serializa nós ocultos corretamente (campo `"type": "hidden"`). Nenhuma alteração.

## Critérios de aceite

- [ ] `neat_config.ini` contém `num_hidden = 2`
- [ ] `neat_config.ini` mantém `initial_connection = full_direct`
- [ ] Um genoma da Gen-0 tem exatamente 6 nós (`genome.nodes`) e 104 conexões (`genome.connections`)
- [ ] `net.activate([0.0] * 16)` retorna lista de 4 floats (contrato de I/O preservado)
- [ ] `genome_to_dict()` retorna 2 entradas com `"type": "hidden"` para um genoma da Gen-0
- [ ] `pytest tests/ -x -q` passa com 0 falhas (incluindo o teste atualizado)
- [ ] `from main import app` não levanta exceção

## Rollback

Reverter as duas edições:
1. Em `neat_config.ini`: `num_hidden = 2` → `num_hidden = 0` e restaurar o comentário original
2. Em `test_rtneat_wrapper.py`: `len(connections) == 104` → `== 64` e `len(nodes) == 6` → `== 4`

Nenhum dado persistido depende da topologia de genoma (simulação sempre recria Gen-0 do zero), portanto o rollback é imediato e sem efeitos colaterais.
