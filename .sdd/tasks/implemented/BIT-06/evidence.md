# Evidência — BIT-06: Oásis Migratórios com TTL + Jardim do Éden Real

**Data de conclusão:** 2026-07-10

## Demanda atendida

O spawn de comida deixou de ser aleatório em qualquer ponto do mapa e passou a nascer só dentro de "oásis" — zonas lógicas (sem corpo Pymunk, invisíveis conforme README §5.1) com TTL, que expiram e forçam as criaturas a migrar atrás do próximo. O "Jardim do Éden" (README §5.2) passou a seguir a regra real: população `< 10` (com sobreviventes) gera um oásis denso na posição de cada um, em vez de criar criaturas novas do zero. O fallback de população `== 0` (não coberto pelo README, mas necessário como piso de segurança) foi preservado.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/oasis.py` | criado | Classe `Oasis` (dado puro, sem física) + constantes (`MAX_ACTIVE_OASES`, TTL min/max, raio, caps de comida, threshold do Jardim do Éden) |
| `backend/simulation/engine.py` | modificado | `self.oases`/`self._eden_active`; bloco de spawn de comida reescrito (ciclo de vida do oásis + spawn restrito ao raio); bloco "Jardim do Éden" reescrito (histerese, oásis nos sobreviventes); `get_state()` ganha campo `"oases"` |
| `backend/tests/test_oasis.py` | criado | 9 testes: expiração por TTL, spawn restrito ao raio, ausência de spawn sem oásis, cap por oásis respeitado, trigger do Jardim do Éden (uma vez por queda de população), histerese (não retrigger a cada frame), retrigger após recuperação populacional, fallback de população zero preservado, campo `oases` no `get_state()` |

## Resultados dos gates de qualidade

- `import main`: OK
- `pytest backend/tests/` → **41/41 passed** (32 pré-existentes + 9 novos), sem regressão
- Smoke test de 600 steps (20s simulados a 30 FPS, 10 criaturas): sem exceção; ao final, 23 foods espalhados em 2 oásis ativos com TTLs distintos (comportamento migratório observável)
- `get_state()` serializa em JSON sem erro, incluindo o novo campo `oases`
- Servidor real (`uvicorn main:app`) subiu e rodou 6s sem traceback no log

## Como validar

```powershell
cd C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos
backend\venv\Scripts\python.exe -m pytest backend/tests/ -v
```

Manualmente: `manager.py` → Start Tudo → abrir frontend, deixar rodar por 1-2 minutos — comida deve aparecer em "manchas" (dentro dos oásis) que somem e reaparecem em outro lugar ao longo do tempo, em vez de espalhada uniformemente pelo mapa o tempo todo. O frontend ainda não renderiza os oásis em si (só a comida gerada por eles) — visualização da zona fica para uma task futura.
