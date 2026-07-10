# Evidência — BIT-07: Locomoção Orientada a Direção

**Data de conclusão:** 2026-07-10

## Demanda atendida

As criaturas deixaram de deslizar de lado ou receber propulsão deliberada pra trás. `motor_forward` negativo (saída da rede) não gera mais impulso reverso, e um "grip lateral" amortece o componente de velocidade perpendicular ao heading a cada frame de física, preservando o componente de avanço — resultado: locomoção "sempre pra frente, fazendo curvas", com física real (colisões) preservada.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/creature.py` | modificado | `LATERAL_GRIP_RATE=20.0`; `update()`: `forward_thrust = max(0.0, motor_forward)` usado no impulso e no custo de energia; bloco de grip lateral decompõe/recompõe `body.velocity` via `Vec2d.rotated()` |
| `backend/tests/test_locomotion.py` | criado | 5 testes: sem propulsão pra trás, amortecimento lateral monotônico, preservação da velocidade de frente, EGG sem lógica de movimento/grip, smoke test |

## Resultados dos gates de qualidade

- Implementação direta (task pequena/isolada, sem sub-agente implementador — conforme orientação do `implementer.md` atualizado): `pytest backend/tests/` → 53/53 passed (48 pré-existentes + 5 novos), sem regressão
- Sub-agente revisor independente: validou empiricamente a matemática de rotação com `pymunk` real (`body.angle=0.7`, não-trivial) contra matrizes de rotação manuais — sem descasamento de convenção; rodou `test_locomotion.py` 10x sem flakiness; smoke test próprio de 90 steps com torque constante confirmou componente de frente crescendo (1.67→87.3) enquanto o lateral ficou sempre `<0.1` — **veredito APROVADO, 0 bugs**
- `import main`: OK

## Como validar

```powershell
cd C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos
backend\venv\Scripts\python.exe -m pytest backend/tests/ -v
```

Manualmente (validação visual, não-automatizável): `manager.py` → Start Tudo → abrir frontend, observar por 1-2 minutos — as criaturas devem visivelmente fazer curvas suaves em vez de deslizar de lado/ré. Pendente de confirmação visual pelo developer.
