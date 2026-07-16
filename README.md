# Bibitinhos: Simulador de Vida Artificial Evolutiva

![Status](https://img.shields.io/badge/Status-BIT--22%20mergeado%20em%20develop-brightgreen)
![Version](https://img.shields.io/badge/Versão-0.3.x-blue)
![Backend](https://img.shields.io/badge/Backend-FastAPI%20%2B%20Pymunk%20%2B%20neat--python-blue)
![Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20Vite%20%2B%20Canvas%202D-blue)

Simulador de ecossistema 2D onde criaturas ("bibites") evoluem por **seleção natural pura**:
sem scripts de comportamento, sem função de fitness artificial. Cada criatura tem uma rede
neural própria (rtNEAT "orgânico" sobre `neat-python`), um corpo físico real (Pymunk) e uma
economia de energia que pune ociosidade e recompensa exploração, alimentação e reprodução.

## Stack

| Camada | Tecnologia |
|---|---|
| Motor de simulação | Python 3.10 · Pymunk (física 2D) · neat-python 0.92 · NumPy |
| API / Stream | FastAPI + WebSocket (`ws://localhost:8001/ws`), broadcast a 30 FPS |
| Cognição | Brain tick a 10 FPS, dissociado da física; saídas cacheadas entre ticks |
| Frontend | React + Vite (porta 5173), renderização em Canvas 2D com sprites |
| Gerenciador local | `manager.py` (TUI em `rich`/`questionary`) ou `manager.bat` |

## Como rodar

```bash
# Opção 1: TUI de gerenciamento (Windows)
manager.bat          # ou: python manager.py
# → "Start Tudo": sobe backend (uvicorn :8001) e frontend (Vite :5173)

# Opção 2: manual
cd backend && venv\Scripts\python.exe -m uvicorn main:app --port 8001 --reload
cd frontend && npm run dev
```

Abra `http://localhost:5173` para observar a simulação. O backend inicia 10 criaturas
Geração 0 automaticamente.

### Testes

```bash
backend\venv\Scripts\python.exe -m pytest backend/tests/ -v
```

Hoje são **127 testes** em 15 arquivos, cobrindo sensores, locomoção, metabolismo,
alimentação, reprodução (sexuada e assexuada), oásis, física da comida e a economia de
energia de exploração.

## Como funciona (resumo)

- **Mundo**: caixa 2000×2000 sem gravidade, com arrasto de água (`damping = 0.35`) e
  paredes elásticas. Frontend renderiza fundo aquático em gradiente.
- **Criaturas**: círculos Pymunk com propulsão só para frente + torque ("volante de
  arcade"), grip lateral contra derrapagem, e ciclo de vida por idade
  (EGG → JUVENILE → ADULT → ELDER) com metabolismo crescente.
- **Cérebro**: rede feedforward NEAT com contrato fixo de **16 inputs / 4 outputs**
  (9 cones de visão frontais de 120°, energia, idade, feedback cinético... →
  motor, torque, grab, mate). Genomas Gen 0 nascem com *seeds* evolutivos: viés de
  locomoção (BIT-20), food-taxis e ímpeto reprodutivo (BIT-21).
- **Evolução**: rtNEAT "orgânico" — nada de gerações em lote; crossover + mutação
  acontecem no momento da colisão física entre dois adultos com `Action_Mate` ativo.
  Clonagem assexuada existe só como via de emergência, deliberadamente cara.
- **Ecologia**: comida nasce apenas dentro de oásis migratórios com TTL (nomadismo
  forçado); comida apodrece; "Jardim do Éden" é o failsafe anti-extinção — e desde o
  BIT-20 o oásis de resgate nasce *longe* do sobrevivente, para não subsidiar quem
  ficou parado.

Detalhes completos em [`docs/`](docs/):

| Documento | Conteúdo |
|---|---|
| [`docs/arquitetura.md`](docs/arquitetura.md) | Loops (física/cérebro/broadcast), contrato WebSocket, módulos do backend, renderização |
| [`docs/simulacao.md`](docs/simulacao.md) | Regras vivas: economia de energia, visão, reprodução, oásis/Éden, ciclo de vida, contrato NEAT |
| [`docs/historico.md`](docs/historico.md) | Linha do tempo BIT-00 → BIT-22, com o racional de cada mudança |
| [`docs/desenvolvimento.md`](docs/desenvolvimento.md) | Workflow de tasks (`.sdd/`), fluxo git, como testar e validar |

## Estado atual (2026-07-16)

- **Mergeado em `develop`**: BIT-00 a BIT-22, incluindo a virada comportamental
  (BIT-20 economia de energia pró-exploração, BIT-21 ímpeto de busca de comida e
  acasalamento, BIT-22 reprodução sexuada emergente com acasalamento por proximidade).
- **Em refinamento** (specs prontas em `.sdd/tasks/refiner/`): **BIT-19** ovo sem visão;
  **BIT-24** controles interativos (pausar/acelerar tempo, inspecionar, arrastar bibite);
  **BIT-23** parâmetros editáveis em tempo real (depende do BIT-24).
- **Ainda não existe**: painéis de métricas, inspetor de rede neural, modo headless,
  Docker/CI (Milestone 4 da visão original), sistema hormonal e relógio biológico
  (inputs 11 e 12 do NEAT são placeholders fixos em `0.0`), mecânica de grab/carry
  (`Action_Grab_Drop` é lido mas não tem efeito físico).

## Estrutura do repositório

```
backend/
  main.py                 # FastAPI + WebSocket + loop asyncio a 30 FPS
  simulation/
    engine.py             # SimulationEngine: orquestra física, reprodução, oásis, Éden
    physics.py            # pymunk.Space (2000x2000, damping 0.35, paredes)
    creature.py           # Creature: corpo, ciclo de vida, economia de energia, atuadores
    sensors.py            # compute_vision: 9 cones frontais de 120°
    rtneat_wrapper.py     # rtNEAT orgânico: genoma zero + seeds, crossover, clone, mutação
    food.py               # Food: corpo dinâmico leve, TTL de apodrecimento
    oasis.py              # Oasis + constantes do Jardim do Éden
    neat_config.ini       # Config NEAT (16 inputs / 4 outputs)
  tests/                  # 127 testes (pytest)
frontend/
  src/components/SimulationCanvas.jsx   # Canvas 2D: sprites tintados, cones de visão, oásis
docs/                     # Documentação viva (ver tabela acima)
.sdd/tasks/               # Specs e evidências por BIT (refiner/ → implementer/ → implemented/)
manager.py                # TUI para subir/derrubar backend+frontend
```
