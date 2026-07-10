"""Wrapper puro sobre neat-python 0.92 para o rtNEAT "organico" do Bibitinhos.

Nao usamos neat.Population.run() (evolucao geracional). Genomas nascem, sao
mutados e cruzados manualmente, disparados por eventos da simulacao (colisao
fisica entre criaturas ADULT com Action_Mate ativo).

Contrato de I/O da rede (net.activate(inputs) -> outputs), estavel para os
sensores/atuadores da Creature:

Inputs (indice -> sensor, inputs[i] mapeia para node key -(i+1)):
    0-8   Visual_Sectors   (9 cones de visao; Gen 0: 3 ativos, resto -1.0)
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
"""

import os

import neat

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "neat_config.ini")

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
