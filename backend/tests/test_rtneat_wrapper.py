import neat
import pytest

from simulation.rtneat_wrapper import (
    create_zero_genome,
    load_neat_config,
    mutate_genome,
    organic_crossover,
)


def test_load_neat_config_parses_topology():
    config = load_neat_config()
    assert config.genome_config.num_inputs == 16
    assert config.genome_config.num_outputs == 4
    assert config.genome_config.input_keys == [-(i + 1) for i in range(16)]
    assert config.genome_config.output_keys == [0, 1, 2, 3]


def test_load_neat_config_is_cached():
    assert load_neat_config() is load_neat_config()


def test_create_zero_genome_is_fully_connected():
    config = load_neat_config()
    genome = create_zero_genome(1, config)
    assert len(genome.connections) == 64
    assert len(genome.nodes) == 4


def test_network_activates_with_16_inputs_returns_4_outputs():
    config = load_neat_config()
    genome = create_zero_genome(1, config)
    net = neat.nn.FeedForwardNetwork.create(genome, config)
    outputs = net.activate([0.0] * 16)
    assert len(outputs) == 4


def test_network_activate_wrong_input_size_raises():
    config = load_neat_config()
    genome = create_zero_genome(1, config)
    net = neat.nn.FeedForwardNetwork.create(genome, config)
    with pytest.raises(RuntimeError):
        net.activate([0.0] * 5)


def test_organic_crossover_with_no_fitness_does_not_raise():
    config = load_neat_config()
    parent1 = create_zero_genome(1, config)
    parent2 = create_zero_genome(2, config)
    assert parent1.fitness is None
    assert parent2.fitness is None
    child = organic_crossover(parent1, parent2, 3, config)
    assert child is not None


def test_mutate_genome_runs_without_error():
    config = load_neat_config()
    parent1 = create_zero_genome(1, config)
    parent2 = create_zero_genome(2, config)
    child = organic_crossover(parent1, parent2, 3, config)
    mutate_genome(child, config)
