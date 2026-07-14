# Evidência — BIT-10: Visual de Ciclo de Vida

**Data de conclusão:** 2026-07-14

## Demanda atendida

Cada `Creature` agora expõe uma cor (`color`) e um raio (`radius`) derivados de `age`/`energy` no payload WebSocket, representando visualmente o ciclo de vida: azul (recém-nascido) → verde (maduro/pronto para reproduzir) → cinza → quase-preto conforme a energia se esgota na fase `ELDER` (não há teto de morte por idade, então o final do gradiente é guiado pela energia restante, ligando o visual à causa real da morte). O tamanho visual também varia: 0.7x (ovo) → 1.0x (adulto) → encolhe até 0.85x no fim da vida. No frontend, o sprite (`bibity.png`/`egg.png`) é tingido com essa cor via canvas offscreen (`source-atop` + alpha parcial), preservando o detalhe do sprite original em vez de virar uma silhueta sólida — decisão explícita do developer sobre a técnica visual.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/creature.py` | modificado | Constantes de cor/escala, `compute_life_color`, `compute_visual_scale`, `to_dict()` atualizado (`color`/`radius` derivados) |
| `frontend/src/components/SimulationCanvas.jsx` | modificado | `drawTintedSprite` (canvas offscreen 64x64 reutilizável) usado no branch de render por sprite |
| `backend/tests/test_creature_life_visuals.py` | criado | Testes unitários de `compute_life_color`/`compute_visual_scale` nos pontos-chave e transições |

`self.size` real e o raio de colisão Pymunk permanecem inalterados — a mudança é puramente cosmética no payload enviado ao frontend, sem efeito no balanceamento de energia/física existente.

## Resultados dos gates de qualidade

- `import main`: OK
- `pytest backend/tests/`: **70 passed**, 0 failed (65 anteriores + 5 novos de `test_creature_life_visuals.py`)
- `npm run build` (frontend): OK, sem erros/warnings de JSX
- Revisão independente: **APROVADO COM RESSALVAS** — nenhum bug encontrado; única ressalva é a verificação visual manual no navegador, feita separadamente pelo coordenador (ver seção abaixo)

## Validação funcional

Verificação visual manual pendente do critério de aceite "sprite muda de tom conforme a idade avança" — realizada pelo coordenador via `manager.py`/dev server antes do merge final (ver nota de fechamento).

## Como validar

1. `cd backend && venv\Scripts\python.exe -m pytest tests/test_creature_life_visuals.py -v` — confirma os testes específicos da feature.
2. `cd backend && venv\Scripts\python.exe -m pytest tests/ -v` — suíte completa, 70/70.
3. `cd frontend && npm run build` — build limpo.
4. Via `manager.py` → "Start Tudo" → abrir o frontend: observar uma criatura desde o nascimento (tom azulado) até a fase adulta (esverdeada) e, se sobreviver até `ELDER` com energia baixa, o escurecimento progressivo em direção ao preto.
