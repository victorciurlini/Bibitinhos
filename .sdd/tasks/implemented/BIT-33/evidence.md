# Evidência — BIT-33: Reprodução na Velhice (ELDER Fértil)

**Data de conclusão:** 2026-08-27

## Demanda atendida

Corrigida a esterilidade não-intencional do estágio ELDER: os quatro gates de reprodução (fertilidade, pool sexuado, loop assexuado e percepção de parceiro) foram estendidos de `== ADULT` para `in (ADULT, ELDER)`. ELDERs agora podem se reproduzir sexuadamente e assexuadamente com as mesmas regras de custo/cooldown dos ADULTs. JUVENILE continua impedido.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `backend/simulation/creature.py` | modificado | Gate de fertilidade aceita `ELDER` |
| `backend/simulation/engine.py` | modificado | Pool sexuado e loop assexuado aceitam `ELDER` |
| `backend/simulation/sensors.py` | modificado | `is_adult` → `is_mature` cobrindo `ADULT` e `ELDER` |
| `backend/tests/test_elder_reproduction.py` | criado | 12 testes: fertilidade ELDER, reprodução sexuada/assexuada, custo/cooldown, anti-regressão JUVENILE |

## Resultados dos gates de qualidade

- `import main`: OK
- `pytest tests/`: **224 passed**, 8 warnings (DeprecationWarning pré-existentes)
- `npm run test` / `npm run build`: N/A (frontend não tocado)

## Como validar

1. `manager.py` → Start Tudo → aguardar bibites chegarem a 30 s de idade (ELDER)
2. Observar no inspetor que ELDERs geram filhos (`children_count > 0`)
3. Confirmar que `max_generation` cresce mesmo com maioria da população em ELDER
