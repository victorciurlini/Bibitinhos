# Pesquisa: Simulação — ciclo de vida da criatura (BIT-10)

## Arquivos relevantes

- `backend\simulation\creature.py` — classe `Creature`, enum `LifeStage`, `METABOLISM_RATE_BY_STAGE`, `update()`, `to_dict()`.
- `backend\simulation\engine.py` — `MIN_ENERGY_TO_MATE = 50.0`, lógica de reprodução (`mate_cooldown`, elegibilidade).

## Conteúdo relevante para a demanda

```python
class LifeStage(Enum):
    EGG = 0
    JUVENILE = 1
    ADULT = 2
    ELDER = 3

METABOLISM_RATE_BY_STAGE = {
    LifeStage.EGG: 0.0,
    LifeStage.JUVENILE: 0.3,
    LifeStage.ADULT: 0.8,
    LifeStage.ELDER: 2.0,
}
```

Transição de estágio em `Creature.update()` (idade em segundos de simulação):

```python
if self.age > 30:
    self.life_stage = LifeStage.ELDER
elif self.age > 10:
    self.life_stage = LifeStage.ADULT
elif self.age > 2:
    self.life_stage = LifeStage.JUVENILE
```

Morte: só ocorre por `self.energy <= 0` (`update()`), **não existe teto de morte por idade**. Uma criatura pode permanecer ELDER indefinidamente se conseguir se alimentar.

`self.size = 10.0` é fixo no `__init__` e nunca reatribuído — usado tanto no `to_dict()` (`"radius": self.size`) quanto no cálculo de `motor_cost` (`abs(self.motor_torque) * self.size * 0.05`). O raio de colisão físico (`pymunk.Circle(self.body, 10.0)`) já é uma constante **separada e fixa**, dissociada de `self.size` — ou seja, alterar `self.size` (ou o valor enviado como `radius`) não afeta a física de colisão hoje.

`self.energy` / `self.max_energy = 100.0` já existem como atributos, mas `max_energy` não é exposto no `to_dict()`.

Reprodução (`engine.py`): `MIN_ENERGY_TO_MATE = 50.0`; uma criatura só acasala se `life_stage` permitir, `mate_cooldown <= 0` e `energy >= MIN_ENERGY_TO_MATE`. Não existe um `LifeStage` dedicado para "pronto para reproduzir" — é uma condição derivada de ADULT + energia + cooldown.

## O que precisa ser feito

1. Adicionar em `creature.py` constantes de cor RGB para os 4 pontos-chave do gradiente de vida (novo/azul, maduro/verde, início da velhice/cinza, próximo da morte/quase-preto) e constantes de escala visual (ovo menor, adulto tamanho cheio, idoso levemente encolhido).
2. Adicionar funções puras `compute_life_color(age, energy, max_energy)` e `compute_visual_scale(age, energy, max_energy)` — usam os mesmos limiares de idade já existentes (2, 10, 30) para não duplicar/discordar da lógica de `life_stage`.
3. Como não há teto de morte por idade, a fase ELDER (idade > 30) usa a **fração de energia restante** (`energy / max_energy`) para interpolar cinza → quase-preto — isso conecta o visual diretamente à causa real da morte (energia chegando a zero), em vez de inventar um teto de idade artificial.
4. Modificar `to_dict()` para usar essas funções em `color` e `radius`. Não alterar `self.size` em si (evita side-effect no cálculo de `motor_cost`/balanceamento) — a escala é aplicada apenas no valor enviado ao frontend.
5. Repurposar o campo `color` (hoje `"#00ff00"`/`"#ff0000"` por diet) — nenhum teste em `backend/tests` depende do valor atual, e o campo nunca é visualmente usado no caminho de renderização principal do frontend (ver `research/frontend.md`), então não há regressão de comportamento observável.

## Perguntas em aberto

Nenhuma — decisões de design resolvidas nesta pesquisa (thresholds reaproveitados de `life_stage`, ELDER ligado à energia, tamanho dissociado da física).
