import neat

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
    child = config.genome_type(genome_id)
    child.configure_crossover(genome1, genome2, config.genome_config)
    return child

def mutate_genome(genome, config):
    """
    Applies mutation to the genome based on config probabilities.
    """
    genome.mutate(config.genome_config)
    return genome
