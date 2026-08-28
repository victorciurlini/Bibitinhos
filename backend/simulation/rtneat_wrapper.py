"""Wrapper puro sobre neat-python 0.92 para o rtNEAT "organico" do Bibitinhos.

Nao usamos neat.Population.run() (evolucao geracional). Genomas nascem, sao
mutados e cruzados manualmente, disparados por eventos da simulacao (colisao
fisica entre criaturas ADULT com Action_Mate ativo).

Contrato de I/O da rede (net.activate(inputs) -> outputs), estavel para os
sensores/atuadores da Creature:

Inputs (indice -> sensor, inputs[i] mapeia para node key -(i+1)):
    0-8   Visual_Sectors   (9 cones cobrindo um leque frontal de 120 graus, setor 4 =
                           eixo central "para frente", 0/8 = bordas do cone; nada atras
                           ou fora do leque ativa qualquer setor. Sinal em [-1,1]:
                           positivo=comida (mag=fome), negativo=outra criatura
                           (mag=energia, so se ADULT), 0=vazio/fora do cone)
    9     Energy_Level     (0.0-1.0)
    10    Age_Degradation  (0.0-1.0)
    11    Hormonal_Level   (0.0-1.0)
    12    Biological_Clock (-1.0-1.0)
    13    Load_Sensor      (0.0/0.5/1.0)
    14-15 Kinetic_Feedback (2 canais: velocidade linear/angular local)
    16-19 Wall_Proximity   (4 canais: Norte, Sul, Oeste, Leste; [0,1], 0=perto da parede,
                           1=parede oposta — BIT-38)

Outputs (indice -> acao, output_keys 0..3):
    0  Motor_Forward     (continuo +-, tanh)
    1  Motor_Torque      (continuo +-, tanh)
    2  Action_Grab_Drop  (binario via threshold)
    3  Action_Mate       (binario via threshold)

Seed de locomocao (BIT-20): genomas da Geracao 0 nascem com vies positivo em Motor_Forward.
Ver MOTOR_FORWARD_SEED_BIAS_* abaixo. Nao altera o contrato de I/O acima.

Seeds de impeto (BIT-21), tambem so na Gen 0 (nao alteram o contrato de I/O acima):
    - Food-taxis: os 9 pesos visao[i]->Motor_Torque nascem em FOOD_TAXIS_STEER_GAIN*(i-4),
      fazendo a criatura virar em direcao a comida fora do centro.
    - Impeto reprodutivo: o bias de Action_Mate nasce em U(ACTION_MATE_SEED_BIAS_MIN,
      ACTION_MATE_SEED_BIAS_MAX), fazendo adultos saciados quererem acasalar por padrao.
"""

import copy
import os
import random

import neat

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "neat_config.ini")

# Seed de locomocao (BIT-20): com bias_init_mean=0.0 no neat_config.ini, 48% dos genomas da Gen 0
# nascem com Motor_Forward <= 0 — e como creature.py faz forward_thrust = max(0.0, motor_forward),
# essas criaturas sao fisicamente incapazes de andar, para sempre. Enviesar o bias do node de output
# 0 faz 100% da Gen 0 nascer se movendo, preservando variedade genetica (thrust resultante ~0.64 a
# ~0.99, medido). E um SEED, nao um hardcode: a mutacao pode levar o bias para onde a evolucao quiser,
# e filhos (crossover/clone) nao passam por aqui.
MOTOR_FORWARD_NODE_KEY = 0
MOTOR_FORWARD_SEED_BIAS_MIN = 0.3
MOTOR_FORWARD_SEED_BIAS_MAX = 1.0

# Seed de food-taxis (BIT-21/BIT-37): a Gen-0 nasce virando em direcao a comida que enxerga.
# Com STEER_GAIN=1.0 (BIT-21), 97% da Gen-0 virava para a comida — pouco espaco para evolucao.
# Reduzido para 0.5 (BIT-37): aprox 65-70% viram para a comida, mantendo pressao seletiva real.
# Os pesos visao[i]->Motor_Torque nascem em STEER_GAIN*(i-4): setor central (i=4) recebe 0
# (segue reto) e bordas recebem torque proporcional ao desvio, na direcao correta (torque + = CCW).
# SEED, nao hardcode: mutacao/crossover podem ajustar; filhos nao passam por aqui.
MOTOR_TORQUE_NODE_KEY = 1
FOOD_TAXIS_STEER_GAIN = 0.5

# Seed de impeto reprodutivo (BIT-21/BIT-37): adultos saciados nascem inclinados a acasalar.
# Com U(1.5,2.5) (BIT-21), 93-99% dos adultos saciados ativavam mate — pouco espaco para evolucao.
# Reduzido para U(0.8,1.5) (BIT-37): aprox 60-75% dos adultos saciados querem acasalar.
# Com inputs zerados tanh(bias) > 0 para todo bias > 0, entao qualquer valor no range ativa mate
# em cenario de inputs nulos. Em presenca de sinais negativos (fome, repulsao), a selecao natural
# pode suprimir ou fortalecer o impeto. SEED evolutivel.
ACTION_MATE_NODE_KEY = 3
ACTION_MATE_SEED_BIAS_MIN = 0.8
ACTION_MATE_SEED_BIAS_MAX = 1.5

# Labels legiveis do contrato de I/O (BIT-27), espelhando a docstring do modulo acima.
# INPUT_LABELS[i] casa com o node key -(i+1) (mesma ordem de config.genome_config.input_keys);
# OUTPUT_LABELS[i] casa com o node key i (output_keys 0..3). Usados pelo inspetor de rede
# neural do HUD — a ordem e parte do contrato estavel, nao reordene.
INPUT_LABELS = [
    "Visual_Sector_0", "Visual_Sector_1", "Visual_Sector_2", "Visual_Sector_3",
    "Visual_Sector_4", "Visual_Sector_5", "Visual_Sector_6", "Visual_Sector_7",
    "Visual_Sector_8", "Energy_Level", "Age_Degradation", "Hormonal_Level",
    "Biological_Clock", "Load_Sensor", "Kinetic_Linear", "Kinetic_Angular",
    "Wall_North", "Wall_South", "Wall_West", "Wall_East",  # BIT-38
]
OUTPUT_LABELS = ["Motor_Forward", "Motor_Torque", "Action_Grab_Drop", "Action_Mate"]

_config_cache = {}


def load_neat_config(config_path=None):
    """Carrega (e cacheia por path) a Config do NEAT 0.92 a partir de um .ini."""
    path = config_path or DEFAULT_CONFIG_PATH
    if path not in _config_cache:
        _config_cache[path] = neat.Config(
            neat.DefaultGenome,
            neat.DefaultReproduction,
            neat.DefaultSpeciesSet,
            neat.DefaultStagnation,
            path,
        )
    return _config_cache[path]


def create_zero_genome(genome_id, config):
    """
    Creates a new empty genome with basic structure based on the provided configuration.
    This acts as a pure function abstraction.
    """
    genome = config.genome_type(genome_id)
    genome.configure_new(config.genome_config)

    # Com num_hidden > 0, as conexoes hidden->output nascem com pesos aleatorios N(0,1) e podem
    # cancelar o bias seedado de Motor_Forward. Zerar esses pesos deixa as hidden nodes dormentes
    # na Gen-0: o comportamento inicial e determinado apenas pelos seeds diretos abaixo, e as
    # hidden nodes evoluem naturalmente pelas geracoes seguintes.
    gc = config.genome_config
    for (from_key, _), conn in genome.connections.items():
        if from_key not in gc.input_keys and from_key not in gc.output_keys:
            conn.weight = 0.0

    # Vies inicial positivo em Motor_Forward: a Gen 0 (e os respawns do Eden) ja nasce andando.
    if MOTOR_FORWARD_NODE_KEY in genome.nodes:
        genome.nodes[MOTOR_FORWARD_NODE_KEY].bias = random.uniform(
            MOTOR_FORWARD_SEED_BIAS_MIN, MOTOR_FORWARD_SEED_BIAS_MAX
        )

    # Food-taxis: vira em direcao a comida fora do centro (BIT-21).
    # Bias zerado (BIT-37): sem bias neutro, o food-taxis seed domina o torque inicial;
    # com STEER_GAIN=0.5 o bias aleatorio N(0,1) do neat poderia cancelar o sinal direcional.
    if MOTOR_TORQUE_NODE_KEY in genome.nodes:
        genome.nodes[MOTOR_TORQUE_NODE_KEY].bias = 0.0
    for i in range(9):  # 9 setores visuais; input node key = -(i+1)
        conn_key = (-(i + 1), MOTOR_TORQUE_NODE_KEY)
        if conn_key in genome.connections:
            genome.connections[conn_key].weight = FOOD_TAXIS_STEER_GAIN * (i - 4)

    # Impeto reprodutivo: adultos saciados nascem inclinados a acasalar (BIT-21).
    if ACTION_MATE_NODE_KEY in genome.nodes:
        genome.nodes[ACTION_MATE_NODE_KEY].bias = random.uniform(
            ACTION_MATE_SEED_BIAS_MIN, ACTION_MATE_SEED_BIAS_MAX
        )
    return genome

def organic_crossover(genome1, genome2, genome_id, config):
    """
    Performs crossover between two parent genomes to produce a child genome.
    This acts as a pure function abstraction.
    """
    # A 0.92 exige fitness numerico nos pais (assert em configure_crossover).
    # O rtNEAT organico nao usa fitness — dominancia parental vem de
    # energia/idade em outro passo. Default 0.0 evita o AssertionError.
    if genome1.fitness is None:
        genome1.fitness = 0.0
    if genome2.fitness is None:
        genome2.fitness = 0.0
    child = config.genome_type(genome_id)
    child.configure_crossover(genome1, genome2, config.genome_config)
    return child

def mutate_genome(genome, config):
    """
    Applies mutation to the genome based on config probabilities.
    """
    genome.mutate(config.genome_config)
    return genome

def clone_genome(genome, genome_id, config):
    """
    Cria uma copia independente de um genoma (reproducao assexuada: um unico pai).
    Deepcopy garante que conexoes/nos do clone nao compartilhem referencia com o
    original antes da mutacao subsequente.
    """
    clone = copy.deepcopy(genome)
    clone.key = genome_id
    return clone


def genome_to_dict(genome, config):
    """Serializa a topologia do genoma em dict JSON-safe para o inspetor (BIT-27).

    Os nodes de INPUT nao existem em genome.nodes no NEAT 0.92 (sao implicitos);
    vem de config.genome_config.input_keys (-1..-20, na ordem do contrato).
    genome.nodes contem apenas outputs (0..3) e hidden (>= 4).
    """
    gc = config.genome_config
    nodes = {}
    for i, key in enumerate(gc.input_keys):
        nodes[str(key)] = {"key": key, "type": "input", "label": INPUT_LABELS[i]}
    for key, node in genome.nodes.items():
        entry = {
            "key": key,
            "type": "output" if key in gc.output_keys else "hidden",
            "bias": node.bias,
            "activation": node.activation,
        }
        if key in gc.output_keys:
            entry["label"] = OUTPUT_LABELS[gc.output_keys.index(key)]
        nodes[str(key)] = entry
    connections = [
        {"from": in_key, "to": out_key, "weight": conn.weight, "enabled": bool(conn.enabled)}
        for (in_key, out_key), conn in genome.connections.items()
    ]
    return {"key": genome.key, "nodes": nodes, "connections": connections}
