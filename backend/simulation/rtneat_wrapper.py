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

# Seed de food-taxis (BIT-21): a Gen-0 nasce virando em direcao a comida que enxerga.
# Com weight_init_mean=0.0, os 9 pesos visao[i]->Motor_Torque nascem aleatorios N(0,1) e so 47,5%
# das criaturas viram para o lado certo da comida (medido). Semeando peso = STEER_GAIN*(i-4), o setor
# central (i=4) recebe 0 (segue reto) e as bordas recebem torque proporcional ao desvio, na direcao
# correta (torque + = CCW = setores i>4). Medido: 97% da Gen-0 vira para a comida com STEER_GAIN=1.0.
# SEED, nao hardcode: mutacao/crossover podem ajustar; filhos nao passam por aqui.
MOTOR_TORQUE_NODE_KEY = 1
FOOD_TAXIS_STEER_GAIN = 1.0

# Seed de impeto reprodutivo (BIT-21): adultos saciados nascem QUERENDO acasalar (Action_Mate=node 3).
# Com bias 0.0 so 56% dos adultos saciados disparam mate; com U(1.5,2.5) sobe para ~93-99% (medido),
# fazendo com que dois adultos prontos que se cruzam efetivamente acasalem. SEED evolutivel.
ACTION_MATE_NODE_KEY = 3
ACTION_MATE_SEED_BIAS_MIN = 1.5
ACTION_MATE_SEED_BIAS_MAX = 2.5

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
    # Vies inicial positivo em Motor_Forward: a Gen 0 (e os respawns do Eden) ja nasce andando.
    if MOTOR_FORWARD_NODE_KEY in genome.nodes:
        genome.nodes[MOTOR_FORWARD_NODE_KEY].bias = random.uniform(
            MOTOR_FORWARD_SEED_BIAS_MIN, MOTOR_FORWARD_SEED_BIAS_MAX
        )

    # Food-taxis: vira em direcao a comida fora do centro (BIT-21).
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
