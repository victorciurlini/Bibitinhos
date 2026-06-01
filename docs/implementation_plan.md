# Planejamento: Refinamento Arquitetural "Bibitinhos Core"

## Objetivo
Implementar as regras ecológicas, cognitivas e de reprodução em tempo real. Descartar as posições estáticas atuais e introduzir uma física contínua rigorosa e inteligência artificial (rtNEAT) descentralizada. 

## Decisões Arquiteturais Consolidadas
1. **Física C-Binding:** A biblioteca `pymunk` assumirá a engine de colisão (roda exclusivamente em CPU).
2. **Desacoplamento Cognitivo:** A física fluirá a 60 FPS com `Variable Delta Time`, enquanto a avaliação do cérebro neural operará estritamente a 10 FPS (Brain Tick Rate).
3. **rtNEAT Orgânico:** A classe nativa de populações em loop do `neat-python` será descartada. O algoritmo genético será "hackeado", instanciando genomas e aplicando `crossover` e `mutate` estritamente durante o contato físico sexual.
4. **Otimização Visual:** Varredura em O(N) será evitada usando *Bounding Box Spatial Hashing* do Pymunk somado a trigonometria vetorizada via Numpy.

> [!WARNING]
> **Análise Crítica: Paralelização via GPU para NEAT**
> A ideia de usar a placa de vídeo (via PyTorch, CuPy ou JAX) para acelerar as redes neurais neste caso específico é um anti-padrão arquitetural. O algoritmo NEAT gera topologias heterogêneas e esparsas (cada "Bibite" tem uma rede neural de tamanho e formato diferentes). GPUs são eficientes apenas em multiplicações de matrizes densas e perfeitamente homogêneas em lote (batching).
> Tentar forçar redes mutáveis para a GPU causará "Divergência de Warp" e gargalo severo de barramento PCI-Express (enviando posições da RAM para a VRAM e buscando resultados a 10 FPS). 
> **Decisão Técnica:** O processamento numérico deve permanecer na CPU. Se houver gargalo matemático na propagação do sinal, utilizaremos compilação JIT (Just-In-Time via `Numba`) ou otimização vetorial profunda no `Numpy` (que já aproveita instruções AVX/SIMD do processador), mantendo o cache L1/L2 otimizado sem latência de VRAM.

## Proposed Changes

### [MODIFY] `backend/requirements.txt`
Adicionar as dependências críticas de performance aprovadas na arquitetura:
- `pymunk` (Para Motor Físico de Corpos Rígidos)
- `numpy` (Para cálculo vetorial rápido do cérebro)

### [NEW] `backend/simulation/physics.py`
Instancia o espaço `pymunk.Space()`, que assumirá a lógica primária de coordenadas, velocidade, massa, atrito e *joints*. Todas as classes interagirão com este Space. 

### [NEW] `backend/simulation/rtneat_wrapper.py`
Interface que carrega o modelo de rede neural do `neat-python` de forma "suja" (sob-demanda).
- **Função `create_genome()`:** Instancia um "Paciente Zero" base (Geração 0) com inputs mapeados para 0 e visão restrita.
- **Função `organic_crossover(g1, g2)`:** Executa os matemáticos do `DefaultReproduction.crossover()` no momento em que dois Bibitinhos adultos colidem.

### [MODIFY] `backend/simulation/engine.py`
- Refatoração do `step(dt)` para englobar `physics.space.step()`.
- Oásis Migratórios (Spawns Abundantes): Substituir as comidas aleatórias por "manchas" (clusters) de fertilidade temporária que dropam ovos de `Food`. Oásis murcham usando `Time To Live` (TTL).
- "Protocolo Jardim do Éden": Vigia global. Se `len(creatures) < MIN_POPULATION`, dropa um Oásis massivo em cima dos sobreviventes.

### [MODIFY] `backend/simulation/creature.py`
- Transformar a criatura em um `pymunk.Body` e `pymunk.Circle`/`Capsule`. 
- **Fases da Vida:** Enumerador (EGG, JUVENILE, ADULT, ELDER) alterando os modificadores de energia.
- **Cognição:** Criação do Array de 9 Posições para inputs Visuais. A cada Brain Tick (0.1s), usa o `Space.bb_query()` ao redor do `Body`, calcula o ângulo em arco-tangente e joga 1 (Se Oásis) e -1 (Se cegueira por mutação fraca) no Input Neural.
- **Ações Físicas:** A saída neural aplica um "Impulso/Força" e "Torque" (volante de arcade) ao `pymunk.Body`, substituindo a matemática de seno/cosseno básica que existe hoje.

## Verification Plan

### Testes a Executar
1. **Qualidade Física:** Injetar 1000 cápsulas `pymunk` na engine para verificar se o consumo global (Física + API WebSocket) atende os 60 TPS prometidos.
2. **Auditoria Neural:** O **Reviewer Worker** fará um pente fino no `rtneat_wrapper.py` garantindo que o Crossover ocorre sem vazamento de memória ou criação redundante de id_nodes do pacote externo.

> [!CAUTION]
> Ao mudar a arquitetura para Pymunk, a matemática no Frontend (Canvas) permanecerá inalterada, pois o WebSocket continuará enviando os JSON com `{x, y, radius}`, abstraindo as amarras e densidades dos objetos físicos em C. Isso garante escalabilidade perfeita.

## Review 
Aguardando o "De Acordo" do Usuário baseando-se no detalhamento acima.
