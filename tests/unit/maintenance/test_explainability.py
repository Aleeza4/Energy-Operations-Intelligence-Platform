"""Unit tests for EOIP predictive-maintenance SHAP explainability."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from eoip.maintenance.explainability import (
    ShapExplanationResult,
    explain_failure_predictions,
)
from eoip.maintenance.models.failure import (
    RandomForestFailurePredictor,
)


def _features() -> pd.DataFrame:
    """Return deterministic maintenance features."""
    return pd.DataFrame(
        {
            "active_power_kw": [
                500.0,
                490.0,
                480.0,
                300.0,
                280.0,
                260.0,
                520.0,
                510.0,
            ],
            "temperature_c": [
                40.0,
                41.0,
                42.0,
                70.0,
                75.0,
                80.0,
                39.0,
                40.0,
            ],
            "alarm_count": [
                0.0,
                0.0,
                1.0,
                6.0,
                8.0,
                10.0,
                0.0,
                1.0,
            ],
        }
    )


def _target() -> pd.Series:
    """Return deterministic failure labels."""
    return pd.Series(
        [
            0,
            0,
            0,
            1,
            1,
            1,
            0,
            0,
        ],
        name="failure_within_window",
    )


def _predictor() -> RandomForestFailurePredictor:
    """Return a fitted deterministic failure predictor."""
    predictor = RandomForestFailurePredictor(
        n_estimators=50,
        max_depth=4,
        random_state=42,
    )

    predictor.fit(
        _features(),
        _target(),
    )

    return predictor


class TestShapExplanationResult:
    """Tests for SHAP explanation result validation."""

    def test_accepts_valid_result(self) -> None:
        values = pd.DataFrame(
            {
                "feature_a": [
                    0.1,
                    -0.2,
                ],
                "feature_b": [
                    0.3,
                    0.4,
                ],
            }
        )

        result = ShapExplanationResult(
            values=values,
            base_value=0.25,
            feature_columns=(
                "feature_a",
                "feature_b",
            ),
        )

        assert result.row_count == 2
        assert result.base_value == pytest.approx(0.25)

    def test_rejects_empty_values(self) -> None:
        with pytest.raises(
            ValueError,
            match="SHAP values must not be empty.",
        ):
            ShapExplanationResult(
                values=pd.DataFrame(),
                base_value=0.5,
                feature_columns=("feature_a",),
            )

    def test_rejects_empty_feature_columns(self) -> None:
        with pytest.raises(
            ValueError,
            match="feature_columns must not be empty.",
        ):
            ShapExplanationResult(
                values=pd.DataFrame(
                    {
                        "feature_a": [0.1],
                    }
                ),
                base_value=0.5,
                feature_columns=(),
            )

    def test_rejects_column_mismatch(self) -> None:
        with pytest.raises(
            ValueError,
            match=("SHAP value columns must match feature_columns."),
        ):
            ShapExplanationResult(
                values=pd.DataFrame(
                    {
                        "feature_a": [0.1],
                    }
                ),
                base_value=0.5,
                feature_columns=("different_feature",),
            )

    def test_rejects_non_finite_values(self) -> None:
        with pytest.raises(
            ValueError,
            match=("SHAP values must contain only finite values."),
        ):
            ShapExplanationResult(
                values=pd.DataFrame(
                    {
                        "feature_a": [np.inf],
                    }
                ),
                base_value=0.5,
                feature_columns=("feature_a",),
            )

    def test_rejects_non_finite_base_value(self) -> None:
        with pytest.raises(
            ValueError,
            match="base_value must be finite.",
        ):
            ShapExplanationResult(
                values=pd.DataFrame(
                    {
                        "feature_a": [0.1],
                    }
                ),
                base_value=np.nan,
                feature_columns=("feature_a",),
            )

    def test_mean_absolute_importance(self) -> None:
        result = ShapExplanationResult(
            values=pd.DataFrame(
                {
                    "feature_a": [
                        -1.0,
                        1.0,
                    ],
                    "feature_b": [
                        3.0,
                        -3.0,
                    ],
                }
            ),
            base_value=0.5,
            feature_columns=(
                "feature_a",
                "feature_b",
            ),
        )

        importance = result.mean_absolute_importance()

        assert importance.index.tolist() == [
            "feature_b",
            "feature_a",
        ]

        assert importance["feature_b"] == pytest.approx(3.0)
        assert importance["feature_a"] == pytest.approx(1.0)


class TestExplainFailurePredictions:
    """Tests for Random Forest SHAP explanations."""

    def test_returns_shap_result(self) -> None:
        result = explain_failure_predictions(
            predictor=_predictor(),
            features=_features(),
        )

        assert isinstance(
            result,
            ShapExplanationResult,
        )

    def test_returns_one_row_per_observation(self) -> None:
        features = _features()

        result = explain_failure_predictions(
            predictor=_predictor(),
            features=features,
        )

        assert result.row_count == len(features)

    def test_preserves_feature_columns(self) -> None:
        features = _features()

        result = explain_failure_predictions(
            predictor=_predictor(),
            features=features,
        )

        assert result.feature_columns == tuple(features.columns)

        assert tuple(result.values.columns) == tuple(features.columns)

    def test_preserves_input_index(self) -> None:
        features = _features()

        features.index = [
            10,
            20,
            30,
            40,
            50,
            60,
            70,
            80,
        ]

        predictor = RandomForestFailurePredictor(
            n_estimators=50,
            random_state=42,
        )

        predictor.fit(
            features,
            _target(),
        )

        result = explain_failure_predictions(
            predictor=predictor,
            features=features,
        )

        assert result.values.index.tolist() == (features.index.tolist())

    def test_shap_values_are_finite(self) -> None:
        result = explain_failure_predictions(
            predictor=_predictor(),
            features=_features(),
        )

        assert np.isfinite(result.values.to_numpy(dtype=float)).all()

    def test_base_value_is_finite(self) -> None:
        result = explain_failure_predictions(
            predictor=_predictor(),
            features=_features(),
        )

        assert np.isfinite(result.base_value)

    def test_mean_absolute_importance_contains_all_features(
        self,
    ) -> None:
        features = _features()

        result = explain_failure_predictions(
            predictor=_predictor(),
            features=features,
        )

        importance = result.mean_absolute_importance()

        assert set(importance.index) == set(features.columns)

    def test_explanations_are_deterministic(self) -> None:
        first_predictor = _predictor()
        second_predictor = _predictor()

        first = explain_failure_predictions(
            predictor=first_predictor,
            features=_features(),
        )

        second = explain_failure_predictions(
            predictor=second_predictor,
            features=_features(),
        )

        np.testing.assert_allclose(
            first.values.to_numpy(),
            second.values.to_numpy(),
        )

        assert first.base_value == pytest.approx(second.base_value)

    def test_rejects_unfitted_predictor(self) -> None:
        predictor = RandomForestFailurePredictor()

        with pytest.raises(
            RuntimeError,
            match=("Failure predictor must be fitted before explanation."),
        ):
            explain_failure_predictions(
                predictor=predictor,
                features=_features(),
            )

    def test_rejects_empty_features(self) -> None:
        with pytest.raises(
            ValueError,
            match="Explanation features must not be empty.",
        ):
            explain_failure_predictions(
                predictor=_predictor(),
                features=pd.DataFrame(),
            )

    def test_rejects_feature_schema_mismatch(self) -> None:
        features = _features()[
            [
                "temperature_c",
                "active_power_kw",
                "alarm_count",
            ]
        ]

        with pytest.raises(
            ValueError,
            match=("Explanation feature columns must match " "training features."),
        ):
            explain_failure_predictions(
                predictor=_predictor(),
                features=features,
            )

    def test_rejects_missing_values(self) -> None:
        features = _features()

        features.loc[
            0,
            "active_power_kw",
        ] = np.nan

        with pytest.raises(
            ValueError,
            match=("Explanation features must not contain " "missing values."),
        ):
            explain_failure_predictions(
                predictor=_predictor(),
                features=features,
            )

    def test_rejects_non_numeric_features(self) -> None:
        predictor = _predictor()

        features = _features()
        features["status"] = "normal"

        predictor_columns = list(predictor.feature_columns)

        features = features[predictor_columns[:-1] + ["status"]]

        with pytest.raises(
            ValueError,
            match=("Explanation feature columns must match " "training features."),
        ):
            explain_failure_predictions(
                predictor=predictor,
                features=features,
            )

    def test_rejects_non_finite_features(self) -> None:
        features = _features()

        features.loc[
            0,
            "active_power_kw",
        ] = np.inf

        with pytest.raises(
            ValueError,
            match=("Explanation features must contain only " "finite values."),
        ):
            explain_failure_predictions(
                predictor=_predictor(),
                features=features,
            )
