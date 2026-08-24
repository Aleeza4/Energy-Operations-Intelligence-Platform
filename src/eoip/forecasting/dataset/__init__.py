"""EOIP forecasting dataset package."""

from eoip.forecasting.dataset.base import (
    ForecastDataset,
    ForecastTarget,
)
from eoip.forecasting.dataset.builder import build_forecast_dataset

__all__ = [
    "ForecastDataset",
    "ForecastTarget",
    "build_forecast_dataset",
]
