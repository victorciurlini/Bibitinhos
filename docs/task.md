# Tarefas de Execução: Épico 2 - Bibitinhos Core (Física e rtNEAT)

## Configuração Base
- `[x]` Atualizar dependências: Inserir `pymunk` e `numpy` no `backend/requirements.txt`.
- `[x]` Executar instalação das dependências.

## Módulo de Física (`physics.py`)
- `[x]` Criar `backend/simulation/physics.py`.
- `[x]` Instanciar `pymunk.Space()` sem gravidade (`gravity = (0, 0)`).
- `[x]` Configurar paredes (bordas do mundo 2000x2000) e propriedades de elasticidade.
- `[x]` Criar constantes de colisão (ex: COLLISION_CREATURE, COLLISION_FOOD).

## Wrapper Cognitivo (`rtneat_wrapper.py`)
- `[x]` Criar `backend/simulation/rtneat_wrapper.py`.
- `[x]` Implementar método de carregamento da configuração (usando o `config-feedforward` do neat-python).
- `[x]` Função `create_genome()`: instanciar e retornar um genoma padrão minimamente conectado para a Geração 0.
- `[x]` Função `organic_crossover(g1, g2)`: extrair e acoplar a matemática do `DefaultReproduction.crossover()` + `mutate()`.

## Oásis e Ecossistema (`engine.py` e `food.py`)
- `[x]` Criar arquivo `backend/simulation/food.py` como `pymunk.Body(body_type=KINEMATIC)`.
- `[x]` Refatorar `engine.py` padronizando dimensões do mundo para 2000x2000.
- `[x]` Integrar a chamada de `space.step(dt)` no loop principal do Engine.
- `[x]` Implementar geração temporal de Oásis migratórios (conjuntos de comida que nascem e tem TTL para sumir).
- `[x]` Inserir regra do "Jardim do Éden": se a população cair abaixo de N, gerar Oásis massivo no último sobrevivente.

## Refatoração Biológica (`creature.py`)
- `[x]` Modificar inicializador para englobar as Fases de Vida (EGG, JUVENILE, ADULT, ELDER) definindo multiplicadores de energia e reprodução.
- `[x]` Acoplar a classe à um `pymunk.Body(mass, moment)` com um shape `pymunk.Circle` (Boca/Corpo).
- `[x]` Implementar Visão (Sensor Tick a 10 FPS): rodar `space.bb_query()` ao redor, fazer arctan2 via `Numpy`, definindo quem preenche os 9 cones binários.
- `[x]` Modificar locomoção: O FeedForward do NEAT retornará impulsos/forças e torques ao invés de aplicar `x += cosseno`.

## Adaptação do Frontend
- `[x]` Modificar `frontend/src/components/SimulationCanvas.jsx`.
- `[x]` Calcular `scale` via `Math.min(canvas.width / 2000, canvas.height / 2000)` para o canvas englobar o mundo dinamicamente.
- `[x]` Alterar o renderizador para desenhar traços direcionais além de apenas círculos.
