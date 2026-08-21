"""Unit tests for EOIP forecasting training pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from eoip.forecasting.training import (
    TrainingResult,
    train_forecast_model,
)


def _training_frame() -> pd.DataFrame:
    """Return a valid forecasting training frame."""
    return pd.DataFrame(
        {
            "timestamp": pd.date_range(
                start="2026-08-17T10:00:00Z",
                periods=4,
                freq="15min",
            ),
            "active_power_kw": [
                400.0,
                500.0,
                600.0,
                700.0,
            ],
        }
    )


class TestTrainingResult:
    """Tests for training metadata."""

    def test_accepts_valid_result(self) -> None:
        result = TrainingResult(
            model_name="Naive",
            target_column="active_power_kw",
            row_count=4,
            timestamp_column="timestamp",
        )

        assert result.model_name == "Naive"
        assert result.target_column == "active_power_kw"
        assert result.row_count == 4
        assert result.timestamp_column == "timestamp"

    def test_rejects_empty_model_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="model_name must not be empty.",
        ):
            TrainingResult(
                model_name=" ",
                target_column="active_power_kw",
                row_count=4,
                timestamp_column="timestamp",
            )

    def test_rejects_empty_target_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="target_column must not be empty.",
        ):
            TrainingResult(
                model_name="Naive",
                target_column=" ",
                row_count=4,
                timestamp_column="timestamp",
            )

    def test_rejects_empty_timestamp_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="timestamp_column must not be empty.",
        ):
            TrainingResult(
                model_name="Naive",
                target_column="active_power_kw",
                row_count=4,
                timestamp_column=" ",
            )

    @pytest.mark.parametrize(
        "row_count",
        [
            0,
            -1,
            -10,
        ],
    )
    def test_rejects_non_positive_row_count(
        self,
        row_count: int,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="row_count must be greater than zero.",
        ):
            TrainingResult(
                model_name="Naive",
                target_column="active_power_kw",
                row_count=row_count,
                timestamp_column="timestamp",
            )


class TestTrainForecastModel:
    """Tests for forecasting model training orchestration."""

    def test_trains_model(self) -> None:
        model = MagicMock()
        model.name = "Mock Forecast Model"

        result = train_forecast_model(
            model=model,
            frame=_training_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        model.fit.assert_called_once()

        assert result.model_name == "Mock Forecast Model"
        assert result.target_column == "active_power_kw"
        assert result.timestamp_column == "timestamp"
        assert result.row_count == 4

    def test_passes_expected_fit_arguments(self) -> None:
        model = MagicMock()
        model.name = "Mock Forecast Model"

        frame = _training_frame()

        train_forecast_model(
            model=model,
            frame=frame,
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        model.fit.assert_called_once_with(
            frame=frame,
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

    def test_rejects_empty_training_frame(self) -> None:
        model = MagicMock()
        model.name = "Mock Forecast Model"

        with pytest.raises(
            ValueError,
            match="Training frame must not be empty.",
        ):
            train_forecast_model(
                model=model,
                frame=pd.DataFrame(),
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )

        model.fit.assert_not_called()

    def test_rejects_missing_timestamp_column(self) -> None:
        model = MagicMock()
        model.name = "Mock Forecast Model"

        with pytest.raises(
            ValueError,
            match="Missing timestamp column: missing_timestamp",
        ):
            train_forecast_model(
                model=model,
                frame=_training_frame(),
                timestamp_column="missing_timestamp",
                target_column="active_power_kw",
            )

        model.fit.assert_not_called()

    def test_rejects_missing_target_column(self) -> None:
        model = MagicMock()
        model.name = "Mock Forecast Model"

        with pytest.raises(
            ValueError,
            match="Missing target column: missing_target",
        ):
            train_forecast_model(
                model=model,
                frame=_training_frame(),
                timestamp_column="timestamp",
                target_column="missing_target",
            )

        model.fit.assert_not_called()

    def test_propagates_model_fit_error(self) -> None:
        model = MagicMock()
        model.name = "Mock Forecast Model"
        model.fit.side_effect = ValueError("Model-specific fit failure.")

        with pytest.raises(
            ValueError,
            match="Model-specific fit failure.",
        ):
            train_forecast_model(
                model=model,
                frame=_training_frame(),
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )
