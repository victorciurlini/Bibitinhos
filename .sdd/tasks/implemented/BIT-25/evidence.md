# Evidência — BIT-25: Roadmap na Documentação

**Data de conclusão:** 2026-07-16

## Demanda atendida

Criado `docs/roadmap.md` como **fonte prospectiva única** (Entregue / Em refinamento / Próximos /
Longo prazo), eliminando a duplicação que existia entre a seção `## Estado atual` do README e a
`## Em refinamento` do `historico.md`. O README passou a carregar só um espelho compacto com link;
o `historico.md` voltou a ser razão histórico puro (aponta para o roadmap); e o `desenvolvimento.md`
ganhou a regra de manter o roadmap ao criar/fechar tasks.

> **Nota:** esta task foi **re-implementada sobre o `develop` atual**. Uma sessão anterior a havia
> implementado numa branch `BIT-25` que forkou antes do BIT-23/24 e cujo roadmap listava BIT-23/24
> como "em refinamento" (defasado). O conteúdo foi refeito com o estado correto — BIT-23/24 (e o
> próprio BIT-19/BIT-25) já entregues — e a branch obsoleta descartada.

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `docs/roadmap.md` | criado | Fonte prospectiva: legenda ✅/🔧/🔜/🗺️, 4 seções de status (Entregue BIT-00→25; Em refinamento = nenhuma; Próximos; Longo prazo) e "Como manter" |
| `README.md` | modificado | `## Estado atual` → `## Roadmap` compacto com link para `docs/roadmap.md`; linha do roadmap adicionada à tabela de docs |
| `docs/historico.md` | modificado | Tabela `## Em refinamento` removida; ponteiro para o roadmap no lugar; resto intacto (inclusive "Não existe BIT-11") |
| `docs/desenvolvimento.md` | modificado | Regra de manutenção do roadmap (README + roadmap no mesmo commit) |

## Resultados dos gates de qualidade

- Docs-only: sem código, sem testes. `pytest` não se aplica.
- Links relativos verificados (`roadmap.md` ↔ `historico.md`/`desenvolvimento.md` na mesma pasta; README usa `docs/roadmap.md`).
- Sem lista de pendências duplicada entre README e histórico.

## Follow-up conhecido (não-bloqueante)

O `historico.md` detalha entradas até BIT-22; BIT-19/23/24/25 ainda não têm linha detalhada lá
(só o resumo no roadmap). A regra "Como manter" cobre isso daqui pra frente; backfill das entradas
detalhadas fica como tarefa de documentação futura.

## Como validar

Abrir `docs/roadmap.md` e confirmar as 4 seções + legenda + "Como manter"; conferir que o README
tem `## Roadmap` (não mais `## Estado atual`) linkando o roadmap, e que o `historico.md` aponta
para o roadmap em vez de listar specs pendentes.
