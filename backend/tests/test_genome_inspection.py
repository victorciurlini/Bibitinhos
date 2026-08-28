"""Testes do inspetor de rede neural (BIT-27): serializacao genome_to_dict e payload
da acao WebSocket inspect_creature. Importa constantes/estruturas dos modulos — nunca
hardcoda dimensoes do contrato NEAT (padrao do projeto).

Nota: a acao WebSocket e testada via main.build_creature_inspection (helper puro do
handler), porque o TestClient nao instancia neste venv (starlette 0.27 + httpx 0.28
nao convivem — mesmo desvio documentado no BIT-26 / test_metrics.py).
"""
import json

import pytest

from simulation.engine import SimulationEngine
from simulation.creature import Creature
from simulation.rtneat_wrapper import (
    INPUT_LABELS,
    OUTPUT_LABELS,
    create_zero_genome,
    genome_to_dict,
    load_neat_config,
)


@pytest.fixture
def config():
    return load_neat_config()


@pytest.fixture
def genome(config):
    return create_zero_genome(1, config)


# --- 1. Serializacao do genoma zero (Gen 0) --------------------------------

def test_labels_match_contract_dimensions(config):
    gc = config.genome_config
    assert len(INPUT_LABELS) == len(gc.input_keys)
    assert len(OUTPUT_LABELS) == len(gc.output_keys)


def test_genome_to_dict_zero_genome_node_counts(genome, config):
    gc = config.genome_config
    d = genome_to_dict(genome, config)
    types = [n["type"] for n in d["nodes"].values()]
    assert types.count("input") == len(gc.input_keys)
    assert types.count("output") == len(gc.output_keys)
    assert types.count("hidden") == gc.num_hidden
    assert len(d["nodes"]) == len(gc.input_keys) + len(gc.output_keys) + gc.num_hidden


def test_genome_to_dict_input_nodes_come_from_config(genome, config):
    # Inputs nao existem em genome.nodes no NEAT 0.92; devem vir de input_keys,
    # com o label na ordem do contrato (INPUT_LABELS[i] <-> key -(i+1)).
    gc = config.genome_config
    d = genome_to_dict(genome, config)
    for i, key in enumerate(gc.input_keys):
        entry = d["nodes"][str(key)]
        assert entry["key"] == key
        assert entry["type"] == "input"
        assert entry["label"] == INPUT_LABELS[i]


def test_genome_to_dict_output_nodes_have_labels_bias_activation(genome, config):
    gc = config.genome_config
    d = genome_to_dict(genome, config)
    for i, key in enumerate(gc.output_keys):
        entry = d["nodes"][str(key)]
        assert entry["type"] == "output"
        assert entry["label"] == OUTPUT_LABELS[i]
        assert entry["bias"] == genome.nodes[key].bias
        assert entry["activation"] == genome.nodes[key].activation


def test_genome_to_dict_connections_mirror_genome(genome, config):
    d = genome_to_dict(genome, config)
    assert len(d["connections"]) == len(genome.connections)
    for entry in d["connections"]:
        conn = genome.connections[(entry["from"], entry["to"])]
        assert entry["weight"] == conn.weight
        assert entry["enabled"] == bool(conn.enabled)


def test_genome_to_dict_key_and_json_safe(genome, config):
    d = genome_to_dict(genome, config)
    assert d["key"] == genome.key
    json.dumps(d)  # nao pode levantar TypeError


# --- 2. Genoma com no hidden ----------------------------------------------

def test_genome_to_dict_hidden_node(genome, config):
    # mutate_add_node divide uma conexao existente e cria um no intermediario;
    # com num_hidden=2, o genoma zero ja tem 2 hidden — apos a mutacao fica com 3.
    genome.mutate_add_node(config.genome_config)
    d = genome_to_dict(genome, config)
    hidden = [n for n in d["nodes"].values() if n["type"] == "hidden"]
    assert len(hidden) == config.genome_config.num_hidden + 1
    for entry in hidden:
        assert "label" not in entry  # hidden nao tem label do contrato
        assert entry["bias"] == genome.nodes[entry["key"]].bias
    json.dumps(d)


# --- 3. Payload da acao WebSocket inspect_creature -------------------------

def test_build_creature_inspection_valid_id():
    import main

    engine = SimulationEngine()
    creature = Creature(engine)
    engine.add_creature(creature)

    payload = main.build_creature_inspection(engine, creature.id)

    assert payload["type"] == "creature_inspection"
    assert payload["creature_id"] == creature.id
    assert payload["genome"] is not None
    assert payload["genome"]["key"] == creature.genome.key
    json.dumps(payload)


def test_build_creature_inspection_missing_id_returns_null_genome():
    import main

    engine = SimulationEngine()
    creature = Creature(engine)
    engine.add_creature(creature)

    payload = main.build_creature_inspection(engine, creature.id + 999999)

    assert payload["type"] == "creature_inspection"
    assert payload["genome"] is None
    json.dumps(payload)
