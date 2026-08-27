# Evidência — BIT-17: Ambiente Aquático

**Data de conclusão:** 2026-07-14

## Demanda atendida

O ambiente de simulação agora se comporta e parece aquático: `space.damping` reduzido de 0.9 para 0.35 faz as criaturas perderem velocidade perceptivelmente (~65%/s) ao parar de empurrar, exigindo impulsos periódicos para manter o movimento, em vez de deslizar indefinidamente como antes. O fundo do canvas deixou de usar o sprite `fundo.png` (opaco, que hoje encobria qualquer cor de fundo) e passou a exibir um gradiente azul-aquático, com o letterbox externo em tom azul-marinho escuro.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/physics.py` | modificado | `space.damping`: 0.9 → 0.35 |
| `backend/simulation/creature.py` | modificado | Comentário junto de `LATERAL_GRIP_RATE` documentando a decisão de mantê-lo inalterado |
| `frontend/src/components/SimulationCanvas.jsx` | modificado | Removido carregamento/desenho de `fundo.png`; adicionado gradiente azul (`#1a5079`→`#0d2c44`) no mundo; `#1e1e1e` → `#0a1e2e` no fill externo/letterbox e no `backgroundColor` inline do `<canvas>` |

## Resultados dos gates de qualidade

- `import main`: OK
- `pytest backend/tests/`: **85 passed**, 0 failed (rodado 2x — uma vez pelo implementador, outra de forma independente pelo revisor)
- `npm run build`: OK, sem erros
- `npm run lint`: 2 erros pré-existentes (`'React' is defined but never used` em `App.jsx` e `SimulationCanvas.jsx`), confirmados via `git show develop:...` como já presentes antes desta task — fora de escopo, não introduzidos por esta mudança
- Revisão independente (sub-agente): **APROVADO**, incluindo validação empírica própria contra o Pymunk real do venv (script comparando `damping=0.9` vs `0.35` sob impulso contínuo e intermitente) — relatório completo em `review-report.md` nesta mesma pasta

## Validação funcional

Backend e frontend já estavam em execução via uma instância de `manager.py` de outra sessão de trabalho ativa no mesmo repositório (portas 8001/5173 ocupadas quando tentei subir minha própria instância — documentado para transparência). Como `uvicorn --reload`/Vite observam o estado real dos arquivos em disco (não branches git), e não há git worktree separado neste repositório, essa instância já compartilhada refletia o conteúdo atual da branch `BIT-17` no momento da checagem. Validação feita via Chrome (`http://localhost:5173`):
- Fundo do canvas exibe o gradiente azul-aquático esperado, com letterbox externo em tom mais escuro — fronteira do mapa continua visualmente distinguível.
- Criaturas visivelmente em movimento/rotação entre dois screenshots espaçados por alguns segundos, sem travar.
- Console do navegador sem erros da aplicação (só ruído padrão de extensão do Chrome, não relacionado).

O comportamento fino de arrasto ("precisa se forçar periodicamente para andar") foi confirmado de forma mais rigorosa pela validação empírica do revisor (script Python usando as classes reais do projeto), não apenas por observação visual de poucos segundos — ver `review-report.md`.

## Como validar

1. `cd backend && venv\Scripts\python.exe -m pytest tests/ -v` — 85 testes verdes.
2. Via `manager.py` → Start Tudo → abrir `http://localhost:5173`: observar o fundo azulado e uma criatura perdendo velocidade visivelmente (~1s) ao parar de empurrar, mas ainda conseguindo se mover sob impulso contínuo.
