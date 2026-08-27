# BIT-34 — Evidência de Implementação

**Data:** 2026-08-27

## Arquivos criados/modificados

| Arquivo | Operação |
|---|---|
| `frontend/src/components/SimulationCanvas.jsx` | Modificado (passos 1–4, 6) |
| `frontend/src/components/CreatureDetailPanel.jsx` | Criado (passo 5) |
| `frontend/src/components/ControlMenu.jsx` | Modificado (passo 7) |

## Resultado dos gates

### Backend

```
$ python -c "import main; print('OK - app importa')"
OK - app importa

$ python -m pytest tests/ -v
200 passed, 8 warnings in 5.76s
```

### Frontend

```
$ npm run test
✓ src/tests/App.test.jsx (1 test) 3ms
Test Files: 1 passed (1)
Tests:      1 passed (1)
Duration:   955ms

$ npm run build
✓ 42 modules transformed.
dist/index.html                   0.46 kB │ gzip:  0.29 kB
dist/assets/index-5QKg5ecK.css   2.05 kB │ gzip:  0.75 kB
dist/assets/index-BML1nzcn.js  168.64 kB │ gzip: 54.07 kB
✓ built in 1.21s
```

## Passos para validação manual

1. Inicie o backend: `cd backend && venv\Scripts\python.exe main.py`
2. Inicie o frontend: `cd frontend && npm run dev`
3. Abra `http://localhost:5173` no navegador

### Cenário 1 — Painel direito abre ao clicar em bibitinho
- Clique num bibitinho no canvas
- **Esperado:** Painel "Bibitinho" aparece à direita do canvas (overlay com mesma estética HUD)
- **Esperado:** Painel esquerdo (ControlMenu) NÃO mostra mais "Inspetor"

### Cenário 2 — Bibitinho morre com painel aberto
- Selecione um bibitinho com pouquíssima energia
- Aguarde a morte
- **Esperado:** Badge vermelho "Morto" aparece no header do painel direito
- **Esperado:** Conteúdo do painel fica com opacidade 65% e saturação reduzida (grayscale parcial)
- **Esperado:** Anel de seleção desaparece do canvas (criatura sumiu do state)
- **Esperado:** Painel NÃO fecha automaticamente

### Cenário 3 — Fechar painel
- Com painel aberto (vivo ou morto), clicar no botão "×" do painel direito
- **Esperado:** Painel fecha
- Clicar no canvas vazio
- **Esperado:** Se havia painel aberto, fecha (selectedIdRef volta a null)

### Cenário 4 — Trocar seleção
- Com bibitinho A selecionado (painel aberto), clicar em bibitinho B
- **Esperado:** Painel atualiza para B instantaneamente
- **Esperado:** Badge "Morto" desaparece (novo bibitinho está vivo)
