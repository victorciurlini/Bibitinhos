# Spec — BIT-17: Ambiente Aquático

**Linear:** N/A
**Risco:** low
**Camada(s):** Múltiplas (Backend Simulação + Frontend)

---

## Demanda

O ambiente de simulação hoje se comporta e parece "flutuante": criaturas mantêm velocidade por muitos segundos após parar de empurrar (o `space.damping` atual de 0.9 corresponde a uma velocidade terminal teórica de ~475 u/s sob impulso contínuo, então o arrasto nunca é sentido em qualquer janela realista de simulação), e o fundo do canvas é uma imagem quase em branco sem nenhuma identidade visual. O developer pediu que o ambiente passe a se comportar e parecer como água: criaturas devem sentir arrasto real, precisando "se forçar" periodicamente para manter o movimento (em vez de deslizar indefinidamente após um único impulso), e o fundo visual deve ficar azulado.

Decisão explícita do developer: priorizar **arrasto tipo água** (não deslize tipo gelo/baixo-atrito) e um **fundo de cor/gradiente sólido azulado** (não um efeito animado de ondas).

## Abordagem técnica

Ajustar `space.damping` de 0.9 para 0.35 em `backend/simulation/physics.py` — validado empiricamente (rodando contra o Pymunk real do venv do projeto) que o Chipmunk aplica damping como `pow(damping, dt)` por `space.step`, ou seja, o valor já é "fração de velocidade retida por segundo real", independente da taxa de sub-passos (30 FPS atual). `LATERAL_GRIP_RATE` (creature.py) fica inalterado — é um mecanismo ortogonal (corrige derrapagem lateral por rotação, BIT-07) e tem piso numérico obrigatório em teste existente. No frontend, parar de desenhar `fundo.png` (opaco, encobre qualquer fill por baixo) e desenhar um gradiente azul diretamente no `fillRect` já usado pelo canvas, mantendo o fill externo/letterbox num tom azul mais escuro para preservar a fronteira visível do mapa.

## Arquivos a tocar

| Arquivo (path relativo à raiz do projeto) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/physics.py` | modificar | `space.damping`: 0.9 → 0.35 (linha 11) |
| `backend/simulation/creature.py` | modificar | comentário junto de `LATERAL_GRIP_RATE` (linha 14) documentando a decisão de não alterá-lo nesta task |
| `frontend/src/components/SimulationCanvas.jsx` | modificar | remover carregamento/desenho de `fundo.png` (linhas 43, 108-111); desenhar gradiente azul no mundo; trocar `#1e1e1e` → `#0a1e2e` no fill externo/letterbox (linhas 55, 92, 221) |

## Passos de implementação

1. Em `backend/simulation/physics.py:11`, trocar `space.damping = 0.9` por:
   ```python
   space.damping = 0.35  # arrasto tipo agua: retem ~35% da velocidade por segundo sem propulsao
                          # (era 0.9 = ~90%/s, quase sem arrasto perceptivel - sensacao "flutuante")
   ```

2. Em `backend/simulation/creature.py:14`, manter `LATERAL_GRIP_RATE = 20.0` e adicionar logo abaixo:
   ```python
   LATERAL_GRIP_RATE = 20.0  # taxa de amortecimento lateral (1/segundo), tunavel
   # Nota (BIT-17): mantido inalterado ao introduzir arrasto de agua - corrige derrapagem
   # lateral por rotacao (BIT-07), ortogonal ao arrasto longitudinal; reduzi-lo abaixo de
   # ~11.1 quebra test_locomotion.py::test_lateral_velocity_is_damped_towards_zero_over_frames.
   ```

3. Em `frontend/src/components/SimulationCanvas.jsx`:
   - Remover a linha 43: `images.current.fundo = loadImg('/sprites/fundo.png');`
   - Linha 55: `ctx.fillStyle = '#1e1e1e';` → `ctx.fillStyle = '#0a1e2e';`
   - Linha 92: `ctx.fillStyle = '#1e1e1e';` → `ctx.fillStyle = '#0a1e2e';`
   - Linhas 108-111, substituir:
     ```javascript
     if (images.current.fundo && images.current.fundo.complete) {
       ctx.drawImage(images.current.fundo, 0, 0, worldWidth, worldHeight);
     }
     ```
     por:
     ```javascript
     // Fundo aquatico do mundo: gradiente vertical (mais claro no topo, mais fundo embaixo)
     const worldGradient = ctx.createLinearGradient(0, 0, 0, worldHeight);
     worldGradient.addColorStop(0, '#1a5079');
     worldGradient.addColorStop(1, '#0d2c44');
     ctx.fillStyle = worldGradient;
     ctx.fillRect(0, 0, worldWidth, worldHeight);
     ```
   - Linha 221: `backgroundColor: '#1e1e1e'` → `backgroundColor: '#0a1e2e'`

   `frontend/public/sprites/fundo.png` fica intocado no disco (nenhum outro consumidor, remover apenas a referência é suficiente).

4. Rodar `pytest backend/tests/ -v` (100% verde esperado, nenhuma alteração necessária nos arquivos de teste) e `npm run build` no frontend.

5. Validação funcional via `manager.py`: iniciar a simulação e observar por alguns minutos que (a) uma criatura que para de empurrar perde velocidade visivelmente em menos de ~1s; (b) sob impulso contínuo a criatura ainda se move em ritmo perceptível (não fica travada); (c) o fundo do canvas aparece azulado dentro e fora da área do mundo, com a fronteira do mapa ainda distinguível do letterbox.

## Contratos técnicos

### Backend (Simulação)
- Constante alterada: `space.damping` em `create_space()` (`physics.py`), de `0.9` para `0.35`. Nenhuma assinatura de função muda. Efeito colateral aceito: `Food` (corpo Pymunk dinâmico, `FOOD_MASS = CREATURE_MASS * 0.01`) também recebe o novo damping — comida empurrada assenta mais rápido, coerente com o tema aquático. Paredes (`static_body`) e `Oasis` (sem corpo Pymunk) não são afetadas.

### Frontend
- `SimulationCanvas.jsx`: remove o consumo de `images.current.fundo`; nenhuma prop/estado novo — o gradiente é recalculado a cada frame a partir de `worldHeight`, já disponível no escopo do `renderLoop`.

## Critérios de aceite

- [ ] `space.damping == 0.35` em `physics.py`.
- [ ] `LATERAL_GRIP_RATE` permanece `20.0` em `creature.py`.
- [ ] `pytest backend/tests/ -v` 100% verde, sem alteração em nenhum arquivo de teste.
- [ ] `npm run build` sem erros no frontend.
- [ ] Validação manual: criatura perde velocidade perceptivelmente (<1s) ao parar de empurrar; ainda se move sob impulso contínuo; fundo do canvas azulado (mundo + letterbox), fronteira do mapa distinguível.

## Rollback

Reverter `physics.py` (`space.damping = 0.9`); reverter o comentário adicionado em `creature.py` (cosmético, sem efeito funcional); reverter `SimulationCanvas.jsx` (restaurar `loadImg('/sprites/fundo.png')`, o bloco `drawImage` original, e `#1e1e1e` nos 3 call sites). Sem estado persistente ou migração envolvida em nenhum dos dois lados.
