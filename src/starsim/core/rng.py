import random

def get_seeded_rng(seed: int) -> random.Random:
    """Returns a new random.Random instance seeded with the given integer."""
    return random.Random(seed)