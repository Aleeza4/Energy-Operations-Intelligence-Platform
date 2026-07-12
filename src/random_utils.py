import random

import numpy as np


def set_random_seed(seed: int) -> None:
    """Set reproducible random seeds for Python and NumPy."""

    if seed < 0:
        raise ValueError("Random seed must be non-negative.")

    random.seed(seed)
    np.random.seed(seed)
