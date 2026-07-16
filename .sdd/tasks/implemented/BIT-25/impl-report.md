# BIT-25 — Roadmap na Documentação — Relatório de Implementação

## Status
CONCLUÍDO

## Arquivos criados/modificados
- **`docs/roadmap.md`** (CRIADO): fonte prospectiva única, com legenda (✅/🔧/🔜/🗺️) e as
  4 seções de status — ✅ Entregue (BIT-00 → BIT-25, resumo por fase apontando para
  `historico.md`), 🔧 Em refinamento (declara explicitamente "nenhuma no momento"),
  🔜 Próximos candidatos (cap populacional; separar tick de física 60 FPS do brain tick
  10 FPS) e 🗺️ Longo prazo (Milestone 4 + débitos técnicos). Inclui a seção
  "Como manter este roadmap".
- **`README.md`** (MODIFICADO): (1) seção `## Estado atual` substituída por um bloco
  `## Roadmap` compacto que espelha o roadmap e linka `docs/roadmap.md`; (2) adicionada a
  linha `docs/roadmap.md` como primeira do corpo da tabela de documentos.
- **`docs/historico.md`** (MODIFICADO): removida a seção `## Em refinamento` (tabela de
  specs pendentes BIT-19/24/23) e colocado no lugar o ponteiro para o roadmap. Título e
  demais seções intactos, incluindo a linha "Não existe BIT-11".
- **`docs/desenvolvimento.md`** (MODIFICADO): na seção "Workflow de tasks", acrescentada a
  regra de manter o roadmap ao criar/fechar task (README + roadmap no mesmo commit).

## Decisões
- Conteúdo do roadmap tomado exatamente do ESTADO ATUAL fornecido pelo orquestrador
  (BIT-19/23/24 já entregues; nenhuma spec em refinamento), não da spec original.
- Links relativos entre docs da mesma pasta usam path simples (`roadmap.md`,
  `historico.md`, `desenvolvimento.md`); README usa `docs/roadmap.md`. Todos os alvos
  verificados como existentes.
- Título do `historico.md` mantido como estava ("BIT-00 → BIT-22") por estar fora do
  escopo autorizado de edição (a spec só pede remover a tabela e inserir o ponteiro,
  "resto intacto").

## Checagem dos critérios de aceite
- [x] `docs/roadmap.md` com as 4 seções de status + legenda + "Como manter".
- [x] README sem `## Estado atual`; com `## Roadmap` compacto linkando `docs/roadmap.md`.
- [x] Tabela de docs do README inclui a linha do roadmap (primeira do corpo).
- [x] `historico.md` sem a tabela `## Em refinamento`; ponteiro no lugar; resto intacto
      (linha "Não existe BIT-11" preservada).
- [x] `desenvolvimento.md` com a regra de manutenção do roadmap.
- [x] Nenhuma lista de tasks pendentes duplicada entre README e histórico (ambos agora só
      apontam para o roadmap).
- [x] Links relativos resolvem (arquivos alvo confirmados no disco).

## Gates
Mudança DOCS-ONLY — sem código ou testes tocados, gate de import/pytest não se aplica.
