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
- **Milestone 4 (BIT-26 → BIT-29, jul/2026):** painéis de métricas populacionais
  (agregados no `state_update` + histórico no backend + sparklines no HUD), inspetor de
  rede neural (genoma serializado via `inspect_creature`/`creature_inspection` + grafo SVG
  no InspectorPanel), modo headless (`HeadlessRunner` + `backend/cli.py` com seed
  reprodutível) e Docker/CI (Dockerfiles + compose + GitHub Actions verde no primeiro run).

## 🔧 Em refinamento (specs prontas em `.sdd/tasks/refiner/`)

**Trilha evolutiva — fazer os bibites evoluírem por mais gerações.** Diagnóstico (jul/2026): os
seeds da Gen 0 já resolvem andar/comer/acasalar, então a evolução só *perde* comportamento; a
extinção re-semeia genomas zero e reseta o pool; mutação alta e ausência de gradiente de fitness
impedem o acúmulo. As duas specs abaixo atacam a base (medir + parar de resetar):

- **BIT-30 — Instrumentação de linhagem & hereditariedade:** geração/`food_eaten`/`children_count`
  por bibite + agregados `max_generation`, `avg_generation`, `extinctions_total`, `avg_lifespan`.
  Pré-requisito de medição. Depende do BIT-26.
- **BIT-31 — Hall of Fame contra reset evolutivo:** cache dos melhores genomas, preservado através
  de extinções; a re-semeadura clona+muta do hall preservando a geração. Maior alavanca. Depende do
  BIT-30.
- **BIT-32 — Carregar comida com efeito físico:** inventário de 1 slot para `Action_Grab_Drop`/
  `Load_Sensor` (hoje inertes) — pegar comida excedente e consumi-la na escassez. Primeiro **headroom
  acima dos seeds** (rumo B). Independente de código; melhor avaliado após BIT-30/31.
- **BIT-33 — Reprodução na velhice (ELDER fértil):** corrige a esterilidade não-intencional do estágio
  ELDER (hoje só ADULT reproduz), alinhando longevidade↔descendência com o incentivo do BIT-31.

**Rumo decidido (jul/2026): B** — manter os seeds da Gen 0 e criar tarefas com teto acima do que eles
resolvem (BIT-32 é a primeira). A alternativa A (enfraquecer os seeds para a inteligência emergir do
zero) fica arquivada como possível pivô futuro.

## 🔜 Próximos candidatos (sem spec)

**Trilha evolutiva (continuação — voltar depois do BIT-30/31, já com métricas em mãos):**

- **Recozimento da mutação orgânica:** `weight_mutate_rate=0.8` / `conn_add_prob=0.5` /
  `node_add_prob=0.2` quase randomizam cada filho numa população pequena. Reduzir para que bons
  genomas sejam *herdados* com pequenas perturbações — substrato da evolução cumulativa.
- **Gradiente de fitness reprodutivo:** hoje a reprodução é filtro binário (cruzou o limiar → ~1
  filho/cooldown). Fazer quem tem mais energia excedente reproduzir *mais* (cooldown menor / nº de
  filhos escalando com a sobra) — vira uma rampa que dá para escalar.
- **Alargar a janela de sobrevivência até a 1ª reprodução:** só o bastante para a taxa ficar acima
  da reposição (densidade/raio de visão, ou metabolismo juvenil menor) — linhagens encadeando em vez
  de morrerem na geração 1.
- **Senescência reprodutiva do ELDER:** se, com o ELDER fértil (BIT-33), linhagens velhas passarem a
  dominar, introduzir fertilidade reduzida / custo maior no estágio ELDER (polimento do BIT-33).
- **Tarefas com mais teto acima dos seeds (rumo B):** provisionar comida a ovo/parceiro, múltiplos
  slots de carga, cache espacial — extensões do BIT-32.
- **Persistir o Hall of Fame em disco** (sobreviver a restart do backend) e **disparar o Éden mais
  cedo/generoso** (reduzir extinções na raiz) — extensões do BIT-31.
- **Pivô A (arquivado):** enfraquecer os seeds da Gen 0 para a inteligência emergir do zero — só se o
  rumo B se mostrar insuficiente.

**Outros:**

- **Cap populacional configurável:** limite de população ajustável (hoje implícito),
  exposto como parâmetro.
- **Separar tick de física do brain tick:** física a 60 FPS e cognição a 10 FPS em loops
  distintos (hoje ambos convivem no mesmo loop `asyncio`).

## 🗺️ Longo prazo

**Milestone 4:** entregue (BIT-26 → BIT-29 na seção ✅).

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
