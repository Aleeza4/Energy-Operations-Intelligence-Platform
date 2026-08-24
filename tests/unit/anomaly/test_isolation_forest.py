"""Unit tests for EOIP Isolation Forest anomaly detection."""

from __future__ import annotations

import pandas as pd
import pytest

from eoip.anomaly.dataset import AnomalyDataset
from eoip.anomaly.isolation_forest import (
    IsolationForestAnomalyDetector,
    IsolationForestResult,
)


def _dataset() -> AnomalyDataset:
    """Return a deterministic anomaly dataset."""
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range(
                start="2026-08-18T10:00:00Z",
                periods=20,
                freq="15min",
            ),
            "active_power_kw": [
                100.0,
                102.0,
                99.0,
                101.0,
                100.0,
                98.0,
                103.0,
                99.0,
                101.0,
                100.0,
                102.0,
                100.0,
                99.0,
                101.0,
                100.0,
                98.0,
                102.0,
                100.0,
                99.0,
                500.0,
            ],
            "ghi_wm2": [
                500.0,
                505.0,
                498.0,
                502.0,
                500.0,
                497.0,
                506.0,
                499.0,
                501.0,
                500.0,
                504.0,
                500.0,
                498.0,
                502.0,
                500.0,
                497.0,
                505.0,
                500.0,
                499.0,
                900.0,
            ],
        }
    )

    return AnomalyDataset(
        data=frame,
        timestamp_column="timestamp",
        target_column="active_power_kw",
    )


class TestIsolationForestAnomalyDetectorConstruction:
    """Tests for Isolation Forest detector construction."""

    def test_default_configuration(self) -> None:
        detector = IsolationForestAnomalyDetector()

        assert detector.contamination == "auto"
        assert detector.random_state == 42
        assert detector.n_estimators == 100
        assert detector.feature_columns is None

    def test_custom_configuration(self) -> None:
        detector = IsolationForestAnomalyDetector(
            contamination=0.1,
            random_state=7,
            n_estimators=200,
        )

        assert detector.contamination == pytest.approx(0.1)
        assert detector.random_state == 7
        assert detector.n_estimators == 200

    @pytest.mark.parametrize(
        "contamination",
        [
            0.0,
            -0.1,
            0.6,
            1.0,
        ],
    )
    def test_rejects_invalid_float_contamination(
        self,
        contamination: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="contamination must be in the interval",
        ):
            IsolationForestAnomalyDetector(
                contamination=contamination,
            )

    def test_rejects_invalid_string_contamination(self) -> None:
        with pytest.raises(
            ValueError,
            match="contamination must be a float or 'auto'.",
        ):
            IsolationForestAnomalyDetector(
                contamination="invalid",
            )

    @pytest.mark.parametrize(
        "n_estimators",
        [
            0,
            -1,
            -10,
        ],
    )
    def test_rejects_non_positive_n_estimators(
        self,
        n_estimators: int,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="n_estimators must be greater than zero.",
        ):
            IsolationForestAnomalyDetector(
                n_estimators=n_estimators,
            )


class TestIsolationForestAnomalyDetectorFitDetect:
    """Tests for Isolation Forest detection."""

    def test_returns_isolation_forest_result(self) -> None:
        detector = IsolationForestAnomalyDetector(
            contamination=0.05,
        )

        result = detector.fit_detect(
            dataset=_dataset(),
        )

        assert isinstance(
            result,
            IsolationForestResult,
        )

    def test_uses_target_column_by_default(self) -> None:
        detector = IsolationForestAnomalyDetector(
            contamination=0.05,
        )

        result = detector.fit_detect(
            dataset=_dataset(),
        )

        assert result.feature_columns == ("active_power_kw",)

        assert detector.feature_columns == ("active_power_kw",)

    def test_supports_multiple_features(self) -> None:
        detector = IsolationForestAnomalyDetector(
            contamination=0.05,
        )

        result = detector.fit_detect(
            dataset=_dataset(),
            feature_columns=[
                "active_power_kw",
                "ghi_wm2",
            ],
        )

        assert result.feature_columns == (
            "active_power_kw",
            "ghi_wm2",
        )

    def test_result_contains_anomaly_columns(self) -> None:
        detector = IsolationForestAnomalyDetector(
            contamination=0.05,
        )

        result = detector.fit_detect(
            dataset=_dataset(),
        )

        assert "anomaly_score" in result.data.columns
        assert "is_anomaly" in result.data.columns

    def test_detects_expected_outlier(self) -> None:
        detector = IsolationForestAnomalyDetector(
            contamination=0.05,
            random_state=42,
        )

        result = detector.fit_detect(
            dataset=_dataset(),
        )

        assert result.data.iloc[-1]["active_power_kw"] == 500.0
        assert bool(result.data.iloc[-1]["is_anomaly"])

    def test_result_metadata(self) -> None:
        detector = IsolationForestAnomalyDetector(
            contamination=0.1,
            random_state=9,
        )

        result = detector.fit_detect(
            dataset=_dataset(),
        )

        assert result.contamination == pytest.approx(0.1)
        assert result.random_state == 9
        assert result.row_count == 20

    def test_anomaly_count_matches_flags(self) -> None:
        detector = IsolationForestAnomalyDetector(
            contamination=0.1,
        )

        result = detector.fit_detect(
            dataset=_dataset(),
        )

        assert result.anomaly_count == int(result.data["is_anomaly"].sum())

    def test_anomaly_rate(self) -> None:
        detector = IsolationForestAnomalyDetector(
            contamination=0.1,
        )

        result = detector.fit_detect(
            dataset=_dataset(),
        )

        assert result.anomaly_rate == pytest.approx(
            result.anomaly_count / result.row_count
        )

    def test_anomalies_returns_flagged_rows(self) -> None:
        detector = IsolationForestAnomalyDetector(
            contamination=0.1,
        )

        result = detector.fit_detect(
            dataset=_dataset(),
        )

        anomalies = result.anomalies()

        assert len(anomalies) == result.anomaly_count
        assert anomalies["is_anomaly"].all()

    def test_anomalies_returns_independent_dataframe(self) -> None:
        detector = IsolationForestAnomalyDetector(
            contamination=0.1,
        )

        result = detector.fit_detect(
            dataset=_dataset(),
        )

        anomalies = result.anomalies()

        if not anomalies.empty:
            index = anomalies.index[0]

            anomalies.loc[
                index,
                "active_power_kw",
            ] = 9999.0

            assert 9999.0 not in result.data["active_power_kw"].tolist()

    def test_does_not_mutate_source_dataset(self) -> None:
        dataset = _dataset()

        detector = IsolationForestAnomalyDetector(
            contamination=0.1,
        )

        detector.fit_detect(
            dataset=dataset,
        )

        assert "anomaly_score" not in dataset.data.columns
        assert "is_anomaly" not in dataset.data.columns

    def test_rejects_empty_feature_list(self) -> None:
        detector = IsolationForestAnomalyDetector()

        with pytest.raises(
            ValueError,
            match="At least one feature column is required.",
        ):
            detector.fit_detect(
                dataset=_dataset(),
                feature_columns=[],
            )

    def test_rejects_missing_feature_column(self) -> None:
        detector = IsolationForestAnomalyDetector()

        with pytest.raises(
            ValueError,
            match="Anomaly feature columns are missing",
        ):
            detector.fit_detect(
                dataset=_dataset(),
                feature_columns=[
                    "missing_feature",
                ],
            )

    def test_rejects_non_numeric_feature(self) -> None:
        dataset = _dataset()

        frame = dataset.copy_frame()

        frame["equipment_status"] = ["normal" for _ in range(len(frame))]

        dataset_with_text = AnomalyDataset(
            data=frame,
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        detector = IsolationForestAnomalyDetector()

        with pytest.raises(
            TypeError,
            match=("Feature column must be numeric: equipment_status"),
        ):
            detector.fit_detect(
                dataset=dataset_with_text,
                feature_columns=[
                    "active_power_kw",
                    "equipment_status",
                ],
            )

    def test_rejects_missing_feature_values(self) -> None:
        dataset = _dataset()

        frame = dataset.copy_frame()

        frame.loc[
            1,
            "ghi_wm2",
        ] = float("nan")

        dataset_with_missing_feature = AnomalyDataset(
            data=frame,
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        detector = IsolationForestAnomalyDetector()

        with pytest.raises(
            ValueError,
            match=("Anomaly feature columns must not contain " "missing values."),
        ):
            detector.fit_detect(
                dataset=dataset_with_missing_feature,
                feature_columns=[
                    "active_power_kw",
                    "ghi_wm2",
                ],
            )

    def test_rejects_non_finite_feature_values(self) -> None:
        dataset = _dataset()

        frame = dataset.copy_frame()

        frame.loc[
            1,
            "ghi_wm2",
        ] = float("inf")

        dataset_with_non_finite_feature = AnomalyDataset(
            data=frame,
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        detector = IsolationForestAnomalyDetector()

        with pytest.raises(
            ValueError,
            match="Anomaly feature values must be finite.",
        ):
            detector.fit_detect(
                dataset=dataset_with_non_finite_feature,
                feature_columns=[
                    "active_power_kw",
                    "ghi_wm2",
                ],
            )
