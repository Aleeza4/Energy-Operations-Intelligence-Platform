"""Unit tests for EOIP statistical anomaly detection."""

from __future__ import annotations

import pandas as pd
import pytest

from eoip.anomaly.dataset import AnomalyDataset
from eoip.anomaly.statistical import (
    StatisticalAnomalyResult,
    ZScoreAnomalyDetector,
)


def _dataset(
    values: list[float] | None = None,
) -> AnomalyDataset:
    """Return a valid anomaly dataset."""
    if values is None:
        values = [
            10.0,
            10.0,
            10.0,
            10.0,
            100.0,
        ]

    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range(
                start="2026-08-18T10:00:00Z",
                periods=len(values),
                freq="15min",
            ),
            "active_power_kw": values,
        }
    )

    return AnomalyDataset(
        data=frame,
        timestamp_column="timestamp",
        target_column="active_power_kw",
    )


class TestStatisticalAnomalyResult:
    """Tests for statistical anomaly result properties."""

    def test_row_count(self) -> None:
        detector = ZScoreAnomalyDetector(
            threshold=1.5,
        )

        result = detector.detect(
            dataset=_dataset(),
        )

        assert result.row_count == 5

    def test_anomaly_count(self) -> None:
        detector = ZScoreAnomalyDetector(
            threshold=1.5,
        )

        result = detector.detect(
            dataset=_dataset(),
        )

        assert result.anomaly_count == 1

    def test_anomaly_rate(self) -> None:
        detector = ZScoreAnomalyDetector(
            threshold=1.5,
        )

        result = detector.detect(
            dataset=_dataset(),
        )

        assert result.anomaly_rate == pytest.approx(0.2)

    def test_anomalies_returns_only_flagged_rows(self) -> None:
        detector = ZScoreAnomalyDetector(
            threshold=1.5,
        )

        result = detector.detect(
            dataset=_dataset(),
        )

        anomalies = result.anomalies()

        assert len(anomalies) == 1
        assert anomalies["active_power_kw"].iloc[0] == 100.0
        assert anomalies["is_anomaly"].all()

    def test_anomalies_returns_independent_dataframe(self) -> None:
        detector = ZScoreAnomalyDetector(
            threshold=1.5,
        )

        result = detector.detect(
            dataset=_dataset(),
        )

        anomalies = result.anomalies()

        anomalies.loc[
            anomalies.index[0],
            "active_power_kw",
        ] = 9999.0

        assert 9999.0 not in result.data["active_power_kw"].tolist()


class TestZScoreAnomalyDetectorConstruction:
    """Tests for detector construction."""

    def test_default_threshold(self) -> None:
        detector = ZScoreAnomalyDetector()

        assert detector.threshold == pytest.approx(3.0)

    def test_custom_threshold(self) -> None:
        detector = ZScoreAnomalyDetector(
            threshold=2.5,
        )

        assert detector.threshold == pytest.approx(2.5)

    @pytest.mark.parametrize(
        "threshold",
        [
            0.0,
            -1.0,
            -10.0,
        ],
    )
    def test_rejects_non_positive_threshold(
        self,
        threshold: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="threshold must be greater than zero.",
        ):
            ZScoreAnomalyDetector(
                threshold=threshold,
            )

    @pytest.mark.parametrize(
        "threshold",
        [
            float("inf"),
            float("-inf"),
            float("nan"),
        ],
    )
    def test_rejects_non_finite_threshold(
        self,
        threshold: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="threshold must be finite.",
        ):
            ZScoreAnomalyDetector(
                threshold=threshold,
            )


class TestZScoreAnomalyDetectorDetect:
    """Tests for anomaly detection."""

    def test_returns_statistical_result(self) -> None:
        detector = ZScoreAnomalyDetector(
            threshold=1.5,
        )

        result = detector.detect(
            dataset=_dataset(),
        )

        assert isinstance(
            result,
            StatisticalAnomalyResult,
        )

    def test_result_contains_score_columns(self) -> None:
        detector = ZScoreAnomalyDetector(
            threshold=1.5,
        )

        result = detector.detect(
            dataset=_dataset(),
        )

        assert "z_score" in result.data.columns
        assert "absolute_z_score" in result.data.columns
        assert "is_anomaly" in result.data.columns

    def test_detects_expected_outlier(self) -> None:
        detector = ZScoreAnomalyDetector(
            threshold=1.5,
        )

        result = detector.detect(
            dataset=_dataset(),
        )

        assert result.data["is_anomaly"].tolist() == [
            False,
            False,
            False,
            False,
            True,
        ]

    def test_preserves_target_column(self) -> None:
        detector = ZScoreAnomalyDetector(
            threshold=1.5,
        )

        result = detector.detect(
            dataset=_dataset(),
        )

        assert result.target_column == "active_power_kw"

    def test_preserves_source_columns(self) -> None:
        dataset = _dataset()

        detector = ZScoreAnomalyDetector(
            threshold=1.5,
        )

        result = detector.detect(
            dataset=dataset,
        )

        assert "timestamp" in result.data.columns
        assert "active_power_kw" in result.data.columns

    def test_does_not_mutate_source_dataset(self) -> None:
        dataset = _dataset()

        detector = ZScoreAnomalyDetector(
            threshold=1.5,
        )

        detector.detect(
            dataset=dataset,
        )

        assert "z_score" not in dataset.data.columns
        assert "absolute_z_score" not in dataset.data.columns
        assert "is_anomaly" not in dataset.data.columns

    def test_constant_series_has_zero_scores(self) -> None:
        dataset = _dataset(
            values=[
                10.0,
                10.0,
                10.0,
                10.0,
            ]
        )

        detector = ZScoreAnomalyDetector()

        result = detector.detect(
            dataset=dataset,
        )

        assert result.standard_deviation == pytest.approx(0.0)

        assert result.data["z_score"].tolist() == [
            0.0,
            0.0,
            0.0,
            0.0,
        ]

        assert not result.data["is_anomaly"].any()

    def test_calculates_mean(self) -> None:
        detector = ZScoreAnomalyDetector(
            threshold=1.5,
        )

        result = detector.detect(
            dataset=_dataset(
                values=[
                    10.0,
                    20.0,
                    30.0,
                ]
            ),
        )

        assert result.mean == pytest.approx(20.0)

    def test_calculates_population_standard_deviation(
        self,
    ) -> None:
        detector = ZScoreAnomalyDetector(
            threshold=3.0,
        )

        result = detector.detect(
            dataset=_dataset(
                values=[
                    10.0,
                    20.0,
                    30.0,
                ]
            ),
        )

        assert result.standard_deviation == pytest.approx(8.1649658093)

    def test_uses_strict_threshold_comparison(self) -> None:
        detector = ZScoreAnomalyDetector(
            threshold=1.0,
        )

        result = detector.detect(
            dataset=_dataset(
                values=[
                    0.0,
                    10.0,
                ]
            ),
        )

        assert result.data["absolute_z_score"].tolist() == pytest.approx(
            [
                1.0,
                1.0,
            ]
        )

        assert result.data["is_anomaly"].tolist() == [
            False,
            False,
        ]

    def test_rejects_non_finite_target_values(self) -> None:
        dataset = _dataset()

        frame = dataset.copy_frame()

        frame.loc[
            0,
            "active_power_kw",
        ] = float("inf")

        invalid_dataset = AnomalyDataset(
            data=frame,
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        detector = ZScoreAnomalyDetector()

        with pytest.raises(
            ValueError,
            match="Anomaly target values must be finite.",
        ):
            detector.detect(
                dataset=invalid_dataset,
            )
