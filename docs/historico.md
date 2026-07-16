# Histórico de Evolução (BIT-00 → BIT-22)

Linha do tempo das tasks. Cada BIT tem spec e evidências completas em
`.sdd/tasks/implemented/BIT-XX/` (ou `implementer//refiner/` se ainda em andamento).

## Fundação (pré-BIT)

- Infraestrutura inicial: FastAPI + WebSocket, React/Vite, TUI `manager.py`.
- Migração para Pymunk, mundo 2000×2000, porta 8001, sprites.
- Decisão arquitetural: **GPU rejeitada** para o NEAT (topologias heterogêneas não
  batcham; ver `.sdd/` e `docs/arquitetura.md`).

## Épico 2 — Bibitinhos Core (física + rtNEAT)

| BIT | Entrega |
|---|---|
| BIT-00 | Config do neat-python (16 inputs / 4 outputs) + loader cacheado em `rtneat_wrapper.py` |
| BIT-01 | Visão: 9 cones binários via `space.bb_query()` + `arctan2`, no brain tick de 10 FPS |
| BIT-02 | Cérebro conectado: `FeedForwardNetwork` real decide os motores a cada brain tick |
| BIT-03 | Alimentação: collision handler criatura×comida transfere energia e consome o alimento |
| BIT-04 | Reprodução sexuada: colisão ADULT×ADULT com `Action_Mate` gera EGG via crossover + mutação |
| BIT-05 | Metabolismo passivo por fase de vida (comer passa a impactar longevidade) |
| BIT-06 | Oásis migratórios com TTL + regra real do Jardim do Éden |
| BIT-07 | Locomoção orientada a direção: sem ré, sem derrapagem lateral (grip), sempre para frente fazendo curvas |

## Refinamentos de ecossistema e feedback visual

| BIT | Entrega |
|---|---|
| BIT-08 | Comida com massa física dinâmica (1% da criatura): ação-reação real, comida empurrável |
| BIT-09 | Reprodução assexuada por clonagem (via de emergência para criatura sem parceiro) |
| BIT-10 | Visual de ciclo de vida: cor + tamanho por idade/energia |
| BIT-12 | Cones de visão desenhados no canvas |
| BIT-13 | Visão ponderada: comida = sinal positivo com magnitude de fome; criatura = negativo com magnitude de energia |
| BIT-14 | Cone de visão **frontal** de 120° (antes 360°): nada atrás da criatura ativa setores |
| BIT-15 | Gradiente de cor contínuo na fase adulta (verde→cinza sem degrau) |
| BIT-16 | Rebalanceamento energético da reprodução (encareceu reproduzir; parcialmente revisto no BIT-20) |
| BIT-17 | Ambiente aquático: `damping` 0.9 → 0.35 (arrasto de água) + fundo azulado no canvas |
| BIT-18 | Renovação de comida (TTL de apodrecimento, 30s) + visualização dos oásis com fade por TTL |

## A virada comportamental

| BIT | Estado | Entrega |
|---|---|---|
| BIT-20 | ✅ mergeado | **Pressão evolutiva para exploração.** O comportamento dominante era ficar parado girando — e o diagnóstico foi que a seleção natural estava *certa*: andar custava 4.5× mais que girar. Quatro frentes: (1) gradiente de energia invertido — imposto de ociosidade por **velocidade real** (imburlável) + propulsão barata; (2) seed genético: 100% da Gen 0 nasce capaz de andar (antes 48% nascia paralisada para sempre); (3) via sexuada destravada (limiar 100→65, custo 50→30) e assexuada encarecida (custo 85, cooldown 45s); (4) Éden para de subsidiar quem está parado — oásis de resgate nasce a 250–400px do sobrevivente. `IDLE_PENALTY_RATE` calibrado ao vivo de 2.0 → 1.2 (a 2.0 a população colapsava). |
| BIT-21 | ✅ mergeado | **Ímpeto de busca de comida e acasalamento.** Seeds adicionais da Gen 0: food-taxis (pesos visão→torque proporcionais ao desvio do setor — 97% da Gen 0 vira em direção à comida) e ímpeto reprodutivo (bias de `Action_Mate` positivo em adultos saciados). Na visão, adulto **pronto para acasalar** (energia ≥ 65%, sem cooldown) passa a perceber outras criaturas como sinal **atrativo** em vez de repulsivo. |
| BIT-22 | ✅ mergeado | **Reprodução sexuada emergente.** Mundo reduzido para 1400×1400 (encontros mais frequentes) e acasalamento passa a disparar por **proximidade** entre dois adultos aptos (`MATING_RADIUS`), não mais só na colisão física exata; limiar de fertilidade parametrizado (`FERTILITY_ENERGY_THRESHOLD`). |

> Não existe BIT-11 — a numeração pulou.

> **Em refinamento e planejado:** ver o [`roadmap.md`](roadmap.md) — este histórico registra apenas o que já foi entregue em `develop`.

## Divergências conhecidas da visão original (README histórico)

- Frontend é **React**, não Angular.
- Colisor da criatura é **círculo**, não cápsula.
- Sem multiprocessing — loop `asyncio` único.
- `Hormonal_Level` / `Biological_Clock` são placeholders fixos em 0.0.
- `Action_Grab_Drop` / `Load_Sensor` / Weld Joint (inventário físico): não implementados.
- Milestone 4 (métricas, inspetor neural, headless, Docker, CI): não iniciado.
