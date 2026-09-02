"""EOIP forecasting package."""

from eoip.forecasting.backtesting import (
    BacktestFoldResult,
    expanding_window_backtest,
)
from eoip.forecasting.comparison import (
    ForecastBaselineComparison,
    ModelEvaluationSummary,
    aggregate_backtest_metrics,
    calculate_error_improvement,
    compare_model_summaries,
    evaluate_backtest_fold,
    rank_model_summaries,
)
from eoip.forecasting.database_store import DatabaseForecastStore
from eoip.forecasting.dataset import (
    ForecastDataset,
    ForecastTarget,
    build_forecast_dataset,
)
from eoip.forecasting.evaluation import (
    ForecastMetrics,
    calculate_forecast_bias,
    calculate_mae,
    calculate_mape,
    calculate_prediction_interval_coverage,
    calculate_rmse,
    calculate_smape,
    calculate_wape,
    evaluate_forecast,
)
from eoip.forecasting.features import (
    add_lag_features,
    add_rolling_features,
    add_time_features,
    select_forecast_features,
)
from eoip.forecasting.models import (
    ForecastModel,
    ForecastPoint,
    ForecastResult,
    NaiveForecastModel,
    ProphetForecastModel,
    SeasonalNaiveForecastModel,
)
from eoip.forecasting.service import ForecastService
from eoip.forecasting.storage import (
    ForecastStore,
    StoredForecast,
    validate_forecast_for_storage,
)
from eoip.forecasting.training import (
    TrainingResult,
    train_forecast_model,
)

__all__ = [
    "BacktestFoldResult",
    "DatabaseForecastStore",
    "ForecastDataset",
    "ForecastBaselineComparison",
    "ForecastMetrics",
    "ForecastModel",
    "ForecastPoint",
    "ForecastResult",
    "ForecastService",
    "ForecastStore",
    "ForecastTarget",
    "ModelEvaluationSummary",
    "NaiveForecastModel",
    "ProphetForecastModel",
    "SeasonalNaiveForecastModel",
    "StoredForecast",
    "TrainingResult",
    "add_lag_features",
    "add_rolling_features",
    "add_time_features",
    "aggregate_backtest_metrics",
    "build_forecast_dataset",
    "calculate_mae",
    "calculate_error_improvement",
    "calculate_forecast_bias",
    "calculate_mape",
    "calculate_prediction_interval_coverage",
    "calculate_rmse",
    "calculate_smape",
    "calculate_wape",
    "compare_model_summaries",
    "evaluate_backtest_fold",
    "evaluate_forecast",
    "expanding_window_backtest",
    "rank_model_summaries",
    "select_forecast_features",
    "train_forecast_model",
    "validate_forecast_for_storage",
]
