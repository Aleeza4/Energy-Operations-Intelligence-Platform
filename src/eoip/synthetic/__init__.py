"""Synthetic data generation package for EOIP Phase 2.

This package provides deterministic, physics-informed synthetic data generation
for utility-scale solar portfolios.
"""

from __future__ import annotations

from eoip.synthetic.config import (
    GenerationConfig,
    GenerationProfile,
)
from eoip.synthetic.generator import (
    SyntheticDataset,
    generate_dataset,
)

__all__ = [
    "GenerationConfig",
    "GenerationProfile",
    "SyntheticDataset",
    "generate_dataset",
]
