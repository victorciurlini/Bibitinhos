# Roadmap

Fonte prospectiva única do Bibitinhos: o que já foi entregue, o que está em refinamento,
o que vem a seguir e o que fica para o longo prazo. O README carrega só um espelho
compacto disto; o [`historico.md`](historico.md) registra o racional detalhado de cada
BIT já entregue.

## Legenda

| Símbolo | Significado |
|---|---|
| ✅ | Entregue (mergeado em `develop`) |
| 🔧 | Em refinamento — spec pronta em `.sdd/tasks/refiner/`, aguardando implementação |
| 🔜 | Próximo candidato — sem spec ainda |
| 🗺️ | Longo prazo — visão / débito técnico |

## ✅ Entregue (BIT-00 → BIT-25)

Resumo por fase. O racional e as evidências de cada BIT estão no
[`historico.md`](historico.md).

- **Épico 2 — Core (BIT-00 → BIT-07):** config do neat-python (16 in / 4 out), visão em
  cones, cérebro conectado ao motor, alimentação, reprodução sexuada, metabolismo por
  fase, oásis + Jardim do Éden e locomoção orientada a direção (sem ré, com grip lateral).
- **Ecossistema & feedback visual (BIT-08 → BIT-18):** comida com massa física, clonagem
  assexuada de emergência, visual de ciclo de vida, cones de visão no canvas, visão
  ponderada, cone frontal de 120°, gradiente de cor adulto, rebalanceamento reprodutivo,
  ambiente aquático (`damping` 0.35) e renovação de comida com TTL de apodrecimento.
- **Virada comportamental (BIT-20 → BIT-22):** pressão evolutiva para exploração (imposto
  de ociosidade por velocidade real, seed de locomoção, via sexuada destravada, Éden que
  não subsidia parado), ímpeto de busca de comida e acasalamento (food-taxis + ímpeto
  reprodutivo na Gen 0) e reprodução sexuada emergente (mundo 1400×1400, acasalamento por
  proximidade).
- **BIT-19 — Ovo sem visão:** EGG não roda visão nem `think()`; `to_dict()` envia
  `vision: []`.
- **BIT-24 — Controles interativos:** pausar/acelerar tempo (substeps de `dt` fixo),
  inspetor de bibite por clique, arrasto e menu HUD recolhível no canto superior esquerdo.
- **BIT-23 — Parâmetros editáveis em tempo real:** registry de 22 parâmetros tunáveis pela
  UI (seção no menu) e restyle visual "bioluminescente" de todo o HUD.
- **BIT-25 — Roadmap na documentação:** este documento como fonte prospectiva única;
  README e histórico viram ponteiros.

## 🔧 Em refinamento (specs prontas em `.sdd/tasks/refiner/`)

Nenhuma no momento — não há spec pendente aguardando implementação.

## 🔜 Próximos candidatos (sem spec)

- **Cap populacional configurável:** limite de população ajustável (hoje implícito),
  exposto como parâmetro.
- **Separar tick de física do brain tick:** física a 60 FPS e cognição a 10 FPS em loops
  distintos (hoje ambos convivem no mesmo loop `asyncio`).

## 🗺️ Longo prazo

**Milestone 4 (visão original, não iniciado):**

- Painéis de métricas populacionais.
- Inspetor de rede neural (visualizar o genoma/cérebro de um bibite).
- Modo headless (rodar a simulação sem frontend).
- Docker / CI.

**Débitos técnicos conhecidos:**

- `Hormonal_Level` / `Biological_Clock` são placeholders fixos em `0.0` (inputs 11 e 12 do
  NEAT).
- `Action_Grab_Drop` / `Load_Sensor` são lidos mas não têm efeito físico (sem inventário
  nem Weld Joint).
- Colisor da criatura é círculo, não cápsula.
- Loop `asyncio` único, sem multiprocessing.

## Como manter este roadmap

- **Ao criar uma task:** registre-a na seção 🔧 (spec em refinamento) ou 🔜 (candidato sem
  spec).
- **Ao fechar uma task** (merge em `develop`): mova-a para ✅, com o racional detalhado indo
  para o [`historico.md`](historico.md).
- **README é espelho compacto:** o bloco `## Roadmap` do `README.md` deve refletir este
  documento em versão resumida — atualize os dois no mesmo commit (ver
  [`desenvolvimento.md`](desenvolvimento.md)).
- Este é o único lugar com a lista prospectiva: não duplique tabelas de pendências no
  README nem no histórico.
