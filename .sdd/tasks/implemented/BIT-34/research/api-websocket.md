## Arquivos relevantes

- `backend/main.py` — WebSocket handler, broadcast loop
- `backend/simulation/engine.py` — lógica de remoção de criaturas mortas (linhas 302–311)
- `backend/simulation/creature.py` — `to_dict()` (linhas 249–271), `is_alive` property, `die()`

## Protocolo WebSocket de criaturas

### Payload `state_update` (broadcast 30 FPS)

```json
{
  "type": "state_update",
  "creatures": [
    {
      "id": 42,
      "x": 612.5,
      "y": 340.2,
      "rotation": 1.5707,
      "radius": 10.5,
      "color": "#22c55e",
      "energy": 65.3,
      "max_energy": 100.0,
      "age": 8.5,
      "diet": "herbivore",
      "life_stage": "ADULT",
      "reproduction_cooldown": 5.2,
      "vision": [0.2, -0.5, 0.8, 0.1, 0.0, -0.3, 0.4, 0.9, -0.1],
      "motor_forward": 0.7,
      "motor_torque": 0.2,
      "action_mate": false,
      "action_grab_drop": false,
      "generation": 2,
      "food_eaten": 3,
      "children_count": 1
    }
  ]
}
```

**Não há campo `alive`, `is_alive` ou `dead` no payload.** A criatura simplesmente some do array quando morre.

## Como a morte é representada

### Remoção em `engine.step()` (linhas 302–311)

```python
alive_creatures = []
for c in self.creatures:
    if c.is_alive:
        alive_creatures.append(c)
    else:
        self._lifespan_sum += c.age
        c.die()  # remove do Pymunk physics
        self.deaths_total += 1
self.creatures = alive_creatures  # lista atualizada para o próximo broadcast
```

**No mesmo frame em que a energia zera:** a criatura desaparece completamente do `state_update`. Não há buffer de "morte visível" — remoção é imediata.

### `to_dict()` — campos serializados

```python
def to_dict(self):
    return {
        "id": self.id,
        "x": self.body.position.x,
        "y": self.body.position.y,
        # ... 17+ campos
        # ← NÃO inclui "is_alive"
    }
```

## O que precisa ser feito no backend

**Nada.** A solução adotada para BIT-34 é 100% no frontend:
- O frontend preserva o último estado recebido quando a criatura desaparece da lista
- Não é necessário adicionar `is_alive` ao payload nem manter criaturas mortas na lista
- A ausência da criatura no próximo `state_update` é o sinal suficiente para o frontend marcar `isDead = true`

Mudanças de backend (adicionar `alive` ao payload, manter criaturas mortas por N frames) seriam válidas mas estão fora do escopo desta task — a abordagem frontend-only resolve o caso de uso de análise post-mortem sem alterar contratos públicos.

## Perguntas em aberto

- Nenhuma. Confirmado que nenhuma mudança de backend é necessária para BIT-34.
