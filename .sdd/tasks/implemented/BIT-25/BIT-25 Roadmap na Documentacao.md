# Spec — BIT-25: Roadmap na Documentação

**Linear:** N/A
**Risco:** low
**Camada(s):** Documentação (README + `docs/`)

---

## Demanda

Falta um **roadmap consolidado**: hoje "o que foi feito, o que está em andamento e o que falta"
está espalhado entre a seção `## Estado atual` do README, a seção `## Em refinamento` do
`historico.md` e as `## Divergências conhecidas` — com duplicação (a lista de specs em
refinamento aparece em dois lugares e já defasou nesta sessão). O developer quer enxergar, num
lugar só, para onde o projeto caminha.

## Abordagem técnica

Criar `docs/roadmap.md` como **fonte prospectiva única** (Entregue / Em refinamento / Próximos /
Longo prazo), e reduzir os outros documentos a ponteiros para ele — evitando duplicação. O
`historico.md` volta a ser um **razão histórico puro** (só o que já foi entregue) e o README
ganha um bloco **Roadmap** compacto com link. Uma seção "Como manter" no roadmap + uma regra no
`desenvolvimento.md` combatem a defasagem na raiz. Sem código, sem testes — camada única de docs.

## Arquivos a tocar

| Arquivo (path relativo à raiz do projeto) | Alteração | Descrição |
|---|---|---|
| `docs/roadmap.md` | criar | Roadmap prospectivo consolidado (fonte única) |
| `README.md` | modificar | Trocar `## Estado atual` por `## Roadmap` compacto + link; add linha na tabela de docs |
| `docs/historico.md` | modificar | Remover `## Em refinamento` (migra p/ roadmap), deixar ponteiro |
| `docs/desenvolvimento.md` | modificar | Regra de manter o roadmap ao criar/fechar task |

## Passos de implementação

> Passos independentes entre si, exceto que o passo 1 (criar roadmap) deve existir antes de
> os demais linkarem para ele. Recomendado nesta ordem.

### Passo 1 — Criar `docs/roadmap.md`

Conteúdo-base (o implementer pode ajustar redação, mas deve preservar as 4 seções de status, a
legenda e a seção "Como manter"; os dados de BITs/débitos abaixo são a verdade atual e não devem
ser inventados):

```markdown
# Roadmap

Visão prospectiva do Bibitinhos: o que já foi entregue, o que está em preparação e para onde o
projeto caminha. O detalhamento BIT-a-BIT do que já foi feito vive em
[`historico.md`](historico.md) (razão histórico); **aqui** ficam o estado consolidado e o futuro.

Legenda: ✅ entregue (em `develop`) · 🔧 spec pronta (aguardando implementação) ·
🔜 próximo candidato (sem spec) · 🗺️ visão de longo prazo

## ✅ Entregue — BIT-00 → BIT-22 (em `develop`)

Resumo por fase; detalhes em [`historico.md`](historico.md):

- **Épico 2 — Core (BIT-00 → 07):** física Pymunk + cérebro rtNEAT, visão em cones,
  alimentação, reprodução sexuada, metabolismo por fase, oásis/Jardim do Éden, locomoção
  orientada à direção.
- **Ecossistema & feedback visual (BIT-08 → 18):** comida com massa física, clonagem assexuada
  de emergência, cor/tamanho por ciclo de vida, cones desenhados, visão ponderada e frontal
  (120°), ambiente aquático, renovação de comida por TTL.
- **Virada comportamental (BIT-20 → 22):** pressão pró-exploração (imposto de ociosidade por
  velocidade real), food-taxis e ímpeto reprodutivo nos seeds da Gen 0, reprodução sexuada
  emergente por proximidade (mapa 1400).

## 🔧 Em refinamento — specs prontas em `.sdd/tasks/refiner/`

| BIT | Entrega | Depende de |
|---|---|---|
| BIT-19 | Ovo sem visão (EGG não roda visão nem `think()`) | — |
| BIT-24 | Controles interativos (pausar/acelerar tempo, inspecionar, arrastar bibite) | — |
| BIT-23 | Parâmetros de balanceamento editáveis em tempo real pela UI | BIT-24 |

## 🔜 Próximos candidatos (ainda sem spec)

- Cap populacional configurável — hoje a reprodução pode crescer sem teto.
- Separar o tick de física (alvo 60 FPS) do brain tick (10 FPS) em loops distintos (o brain tick
  já é dissociado por acumulador dentro de `engine.step()`, mas a física roda em tick único).

## 🗺️ Visão de longo prazo

**Milestone 4 — ferramentas de observação (visão original, não iniciado):**
- Painéis de métricas (população, energia média, nascimentos/mortes ao longo do tempo).
- Inspetor da rede neural do bibite selecionado (sinergia com BIT-24, que introduz a seleção).
- Modo headless (rodar a simulação sem frontend, para experimentos longos).
- Docker + CI.

**Débitos técnicos conhecidos:**
- `Hormonal_Level` / `Biological_Clock` (inputs 11-12 do NEAT) são placeholders fixos em `0.0`.
- `Action_Grab_Drop` / `Load_Sensor` / Weld Joint (inventário físico): lidos mas sem efeito.
- Colisor da criatura é círculo (não cápsula); simulação sem multiprocessing (loop asyncio único).

## Como manter este roadmap

- Ao **criar** uma spec (`/refiner`): adicionar a task em 🔧 Em refinamento (ou 🔜 Próximos).
- Ao **fechar** uma task (mover para `.sdd/tasks/implemented/`): remover a linha de 🔧 Em
  refinamento, refletir no resumo ✅ Entregue **e** registrar a linha detalhada em
  [`historico.md`](historico.md).
- O README traz só um espelho compacto deste arquivo — atualizar os dois no mesmo commit.
```

### Passo 2 — README: bloco Roadmap + linha na tabela de docs

**2a.** Substituir integralmente a seção `## Estado atual (2026-07-16)` (do cabeçalho até antes
de `## Estrutura do repositório`) por:

```markdown
## Roadmap

- ✅ **Entregue em `develop`:** BIT-00 → BIT-22 (core rtNEAT + física Pymunk, ecossistema e
  feedback visual, virada comportamental pró-exploração).
- 🔧 **Em refinamento** (specs prontas): BIT-19 (ovo sem visão), BIT-24 (controles interativos),
  BIT-23 (parâmetros editáveis em tempo real).
- 🗺️ **Longo prazo:** Milestone 4 (painéis de métricas, inspetor de rede neural, modo headless,
  Docker/CI) + débitos técnicos (sistema hormonal, grab/carry).

Roadmap completo e atualizado em **[`docs/roadmap.md`](docs/roadmap.md)**.
```

**2b.** Na tabela de documentos (a que lista `arquitetura.md`/`simulacao.md`/`historico.md`/
`desenvolvimento.md`), adicionar como **primeira** linha do corpo:

```markdown
| [`docs/roadmap.md`](docs/roadmap.md) | O que já foi entregue, o que está em refinamento e para onde o projeto caminha |
```

### Passo 3 — historico.md: remover `## Em refinamento`, deixar ponteiro

Remover a seção inteira `## Em refinamento (specs prontas em ...)` (a tabela BIT-19/24/23,
introduzida no commit `29b743c`) e substituí-la por:

```markdown
> **Em refinamento e planejado:** ver o [`roadmap.md`](roadmap.md) — este histórico registra
> apenas o que já foi entregue em `develop`.
```

Manter o restante do historico (Fundação, Épico 2, Refinamentos, A virada comportamental,
Divergências conhecidas) inalterado. A linha `> Não existe BIT-11 — a numeração pulou.` permanece.

### Passo 4 — desenvolvimento.md: regra de manutenção do roadmap

Na seção `## Workflow de tasks (.sdd/tasks/)`, após a lista de estágios das pastas, acrescentar:

```markdown
- **Manter o roadmap:** ao criar uma spec (`/refiner`) ou fechar uma task (mover para
  `implemented/`), atualizar [`docs/roadmap.md`](roadmap.md) — e, quando fechar, também a
  linha detalhada em [`docs/historico.md`](historico.md). README e roadmap se atualizam no
  mesmo commit (o README é só um espelho compacto).
```

## Contratos técnicos

Nenhum contrato de código. Contrato **documental**:

- **`docs/roadmap.md`** é a fonte única do futuro. `historico.md` = só entregue; README = espelho
  compacto + link. Nenhuma lista de tasks pendentes deve existir em dois lugares editáveis.
- Marcadores de status padronizados: ✅ entregue · 🔧 spec pronta · 🔜 próximo · 🗺️ longo prazo.

## Critérios de aceite

- [ ] `docs/roadmap.md` existe com as 4 seções de status (✅/🔧/🔜/🗺️), legenda e "Como manter".
- [ ] O roadmap lista corretamente: entregue BIT-00→BIT-22; em refinamento BIT-19/24/23 (com a
      dependência BIT-23→BIT-24); Milestone 4 e débitos no longo prazo.
- [ ] README não tem mais `## Estado atual`; tem `## Roadmap` compacto que **linka**
      `docs/roadmap.md`, e a tabela de docs inclui a linha de `roadmap.md`.
- [ ] `historico.md` não tem mais a tabela `## Em refinamento`; no lugar há o ponteiro para o
      roadmap. O resto do historico permanece.
- [ ] `desenvolvimento.md` documenta a regra de manter o roadmap ao criar/fechar tasks.
- [ ] Nenhuma lista de tasks pendentes duplicada entre README e historico (só o espelho compacto
      do README, que aponta para o roadmap).
- [ ] Todos os links relativos entre os docs resolvem (`docs/roadmap.md` ↔ `historico.md` na
      mesma pasta usam path relativo `roadmap.md`/`historico.md`; README usa `docs/roadmap.md`).

## Rollback

Deletar `docs/roadmap.md` e reverter (`git checkout -- README.md docs/historico.md
docs/desenvolvimento.md`) — ou `git revert` do commit da BIT-25. Nenhum efeito em runtime.
