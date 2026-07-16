# Pesquisa — Estado atual da documentação (BIT-25)

Investigação feita direto pelo orquestrador (a documentação foi reorganizada e commitada
nesta mesma sessão — commits `83c60aa` docs + `29b743c` specs; estado validado no disco).

## Arquivos relevantes

- `README.md` (raiz)
- `docs/arquitetura.md`
- `docs/simulacao.md`
- `docs/historico.md`
- `docs/desenvolvimento.md`
- `.sdd/tasks/refiner/{BIT-19,BIT-23,BIT-24}/` (specs prontas, aguardando implementação)

## Conteúdo relevante para a demanda

### Onde a informação de "estado" vive hoje (fragmentada)

| Fonte | O que cobre | Natureza |
|---|---|---|
| `README.md` → seção `## Estado atual (2026-07-16)` | mergeado em develop, em refinamento, "ainda não existe" | snapshot, tende a defasar |
| `docs/historico.md` | linha do tempo BIT-00 → BIT-22 (tabelas por fase) + seção `## Em refinamento` (BIT-19/24/23) | razão histórico do que foi feito |
| `docs/historico.md` → `## Divergências conhecidas` | débitos (hormonal, grab/carry, círculo vs cápsula, Milestone 4 não iniciado) | débitos/limitações |

**Problema central:** não existe um documento **prospectivo consolidado**. O "o que falta"
está espalhado — parte como "ainda não existe" no README, parte como "Em refinamento" no
historico, parte como "Divergências conhecidas". E há **duplicação**: a lista de specs em
refinamento aparece tanto no README quanto no historico, o que já causou defasagem nesta
sessão (o historico chegou a marcar "BIT-21 em implementação" depois do BIT-22 mergeado).

### Estrutura atual do README (para o implementer localizar os pontos de edição)

Ordem das seções: título+badges → intro → `## Stack` → `## Como rodar` → `### Testes` →
`## Como funciona (resumo)` → tabela de docs (arquitetura/simulacao/historico/desenvolvimento)
→ `## Estado atual (2026-07-16)` → `## Estrutura do repositório`.

A seção `## Estado atual` é o ponto natural a virar um bloco compacto de **Roadmap** com link.
A tabela de docs precisa ganhar uma linha para `docs/roadmap.md`.

### Estrutura atual do historico.md

Título `BIT-00 → BIT-22` → `## Fundação` → `## Épico 2` (tabela) → `## Refinamentos de
ecossistema e feedback visual` (tabela) → `## A virada comportamental` (tabela BIT-20/21/22) →
`## Em refinamento` (tabela BIT-19/24/23) → `## Divergências conhecidas`.

A seção `## Em refinamento` é **forward-looking** e deve migrar para o roadmap (deixando o
historico como razão puro do que já foi entregue). As "Divergências conhecidas" (débitos) também
alimentam a seção de longo prazo do roadmap — podem ser referenciadas de lá, mas o historico
pode mantê-las como nota de rodapé da implementação real.

### Itens de futuro já conhecidos (para popular o roadmap)

- **Specs prontas (refiner/):** BIT-19 (ovo sem visão), BIT-24 (controles interativos),
  BIT-23 (parâmetros editáveis, depende de BIT-24).
- **Próximos candidatos sem spec** (citados em memória/desenvolvimento.md como débitos):
  cap populacional configurável; separar tick de física (alvo 60 FPS) do brain tick (10 FPS).
- **Milestone 4 (visão original, README/historico):** painéis de métricas, inspetor de rede
  neural, modo headless, Docker/CI.
- **Débitos técnicos:** `Hormonal_Level`/`Biological_Clock` fixos em 0.0; `Action_Grab_Drop`/
  `Load_Sensor`/Weld Joint lidos mas sem efeito; colisor círculo (não cápsula); sem multiprocessing.

## O que precisa ser feito

1. **Criar** `docs/roadmap.md` — fonte prospectiva única: ✅ Entregue (resumo por fase, com link
   ao historico para o detalhe) · 🔧 Em refinamento · 🔜 Próximos candidatos · 🗺️ Longo prazo
   (Milestone 4 + débitos) · seção "Como manter" para não defasar de novo.
2. **README:** trocar `## Estado atual` por `## Roadmap` compacto (3-4 bullets) + link para
   `docs/roadmap.md`; adicionar linha de `roadmap.md` na tabela de docs.
3. **historico.md:** remover a seção `## Em refinamento` (migrada para o roadmap), substituindo
   por um ponteiro de uma linha para `docs/roadmap.md`. Manter o resto como ledger.
4. **desenvolvimento.md:** adicionar ao workflow de tasks a regra de **atualizar o roadmap** ao
   fechar/criar uma task (raiz da defasagem observada nesta sessão).

## Perguntas em aberto

Resolvidas com o developer:
- **Local:** `docs/roadmap.md` + resumo compacto no README (não só no README, não só no doc).
- **Horizonte:** inclui BITs + Milestones de produto + débitos técnicos.

Sem perguntas remanescentes — task é de documentação, risco baixo, camada única.
