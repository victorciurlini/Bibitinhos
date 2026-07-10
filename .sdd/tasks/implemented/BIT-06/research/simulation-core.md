## Arquivos relevantes

- `backend/simulation/engine.py` — `SimulationEngine.step()`: spawn de comida hoje é aleatório global (5%/frame, cap 50 hardcoded); "Jardim do Éden" hoje só respawna 10 criaturas quando `len(self.creatures) == 0`
- `backend/simulation/food.py` — `Food(engine, x, y, energy_value=20.0)`, sem noção de "zona"/oásis
- `README.md` linhas 130-147 — especificação original do `OasisManager` e "Jardim do Éden" (seção 5, Ecologia e Ambiente)
- `docs/task.md` seção "Oásis e Ecossistema" — já marcada `[x]` mas não implementada de fato (mesmo padrão de divergência já mapeado nas outras tasks)

**Nota de coordenação:** havia uma colisão de numeração — outra sessão concorrente já reivindicou `BIT-05` para o tema "multiplicadores de energia por LifeStage" (o outro item pendente da lista de prioridades). Esta task ficou com `BIT-06`.

## Conteúdo relevante para a demanda

### README.md §5.1 — OasisManager (especificação original, nunca implementada)
```
O ecossistema incentiva nomadismo através de zonas dinâmicas:
- Áreas de Fertilidade Invisíveis: Governadas por Time to Live (TTL)
- Spawn Randomizado: Geração de Food dentro de limites de saturação
- Pressão de Seleção: Desaparecimento de oásis força movimento, punindo sedentarismo
- Taxa de Reprodução: Variável conforme densidade de recursos
```
"Invisíveis" confirma: oásis é uma zona **lógica** (sem corpo físico/shape no Pymunk), não um objeto renderizado — só delimita onde `Food` pode nascer. "Taxa de Reprodução variável conforme densidade de recursos" liga a taxa de reprodução (BIT-04, já implementada com custo/cooldown fixos) à densidade de comida — **fora de escopo desta task** (mexeria em BIT-04, não em spawn de comida); registrar como débito técnico futuro, não implementar aqui.

### README.md §5.2 — "Jardim do Éden" (especificação original, exata)
```
Acionamento: População total < 10 indivíduos
Resposta do Sistema:
- Gera oásis altamente densos nas coordenadas dos sobreviventes
- Garante tração inicial no desenvolvimento genético
- Previne extinção completa do modelo
```
Isso é **diferente** do que o código faz hoje (`engine.py`, bloco "5. Respawn"):
```python
if len(self.creatures) == 0:
    for _ in range(10):
        self.add_creature(Creature(self))
```
O trigger real é `< 10` (não `== 0`), e a resposta é **gerar oásis densos nas posições dos sobreviventes** (mais comida onde quem restou está, para eles se reproduzirem/prosperarem) — não criar criaturas novas do zero. O caso `população == 0` (sem sobreviventes) não está coberto pela spec do README (não há "coordenadas dos sobreviventes" se não sobrou ninguém) — precisa manter um fallback duro separado para esse caso extremo (ver decisão abaixo).

### `engine.py` — spawn de comida atual (a ser substituído)
```python
# 1. Spawn aleatório de comida
if len(self.foods) < 50:
    if random.random() < 0.05: # 5% chance por frame
        x = random.uniform(0, self.width)
        y = random.uniform(0, self.height)
        self.add_food(Food(self, x, y))
```
Spawn uniforme no mapa inteiro, sem qualquer noção de zona — precisa virar spawn só dentro do raio de um oásis ativo.

### `Food.__init__(engine, x, y, energy_value=20.0)`
Sem mudança necessária — `Oasis` só decide `x, y` antes de instanciar `Food`, não precisa alterar a classe `Food`.

### Interseção com BIT-05 (LifeStage/metabolismo, em paralelo)
BIT-05 está mexendo no custo de energia dentro de `Creature.update()` (adicionando metabolismo passivo por `LifeStage`). Esta task (BIT-06) não toca `creature.py` em nenhum ponto — só `engine.py` (spawn de comida + Jardim do Éden) e um `oasis.py` novo. Não há sobreposição de arquivos entre as duas tasks, mas ambas tocam `engine.py`? Não — BIT-05, pela pesquisa dela, diz explicitamente "Nenhuma mudança em engine.py" (item 4 do "O que precisa ser feito" dela). Logo, **sem conflito de arquivo entre BIT-05 e BIT-06** — podem ser implementadas em paralelo sem colidir.

## O que precisa ser feito

1. Criar `backend/simulation/oasis.py`: classe `Oasis` (dado puro, sem Pymunk — `x`, `y`, `radius`, `ttl`, `food_cap`), sem física/shape (zona "invisível" conforme README).
2. `SimulationEngine` ganha `self.oases: list[Oasis]`.
3. Em `step(dt)`, substituir o bloco de spawn aleatório por: (a) decrementar TTL de cada oásis e remover os expirados; (b) chance de nascer um oásis novo (respeitando um cap de oásis simultâneos); (c) para cada oásis ativo, chance de spawnar uma `Food` dentro do seu raio (respeitando cap de comida por oásis e o cap global já existente, hoje hardcoded como `50`).
4. Reescrever o bloco "Jardim do Éden": manter o fallback duro pra população `== 0` (sem sobreviventes, precisa de alguma semente ou o mundo morre para sempre — não coberto pelo README, mas necessário como piso de segurança), e adicionar o comportamento real do README para `0 < população < 10` — gerar um oásis denso na posição de cada sobrevivente. Usar uma flag de histerese (`self._eden_active`) pra não repetir o trigger a cada frame enquanto a população continuar abaixo de 10 (senão empilharia um oásis novo por frame).
5. Expor `self.oases` em `get_state()` (campo novo `"oases"`, aditivo — não quebra consumidores atuais do WebSocket/frontend). Renderização no frontend fica fora de escopo (só o dado fica disponível para uma task futura consumir).

## Perguntas em aberto

- Valores exatos de raio/TTL/cap de comida por oásis não estão no README (só a mecânica, não os números) — proponho valores de partida razoáveis e tunáveis, documentados como tal (não bloqueante).
- "Taxa de Reprodução variável conforme densidade de recursos" (README §5.1) não é implementada aqui — é uma mudança em BIT-04 (custo/cooldown de reprodução), não em spawn de comida; registrar como próxima task candidata, não fazer aqui para não misturar escopo.
- Frontend não vai renderizar os oásis nesta task (só o dado sai no WebSocket) — se o usuário quiser visualização, é uma task de Frontend separada depois.
