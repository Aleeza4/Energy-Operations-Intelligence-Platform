"""Unit tests for EOIP anomaly alert generation."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest

from eoip.anomaly.alerts import (
    AnomalyAlert,
    AnomalySeverity,
    generate_anomaly_alerts,
    severity_from_score,
)


def _frame() -> pd.DataFrame:
    """Return a valid anomaly result frame."""
    return pd.DataFrame(
        {
            "timestamp": pd.date_range(
                start="2026-08-18T10:00:00Z",
                periods=4,
                freq="15min",
            ),
            "active_power_kw": [
                100.0,
                500.0,
                105.0,
                20.0,
            ],
            "z_score": [
                0.2,
                5.5,
                0.4,
                -4.2,
            ],
            "is_anomaly": [
                False,
                True,
                False,
                True,
            ],
        }
    )


class TestAnomalyAlert:
    """Tests for anomaly alert records."""

    def test_accepts_valid_alert(self) -> None:
        alert = AnomalyAlert(
            alert_id="alert-001",
            timestamp=datetime(
                2026,
                8,
                18,
                10,
                0,
                tzinfo=UTC,
            ),
            source="z_score_detector",
            metric="active_power_kw",
            observed_value=500.0,
            score=5.5,
            severity=AnomalySeverity.CRITICAL,
            message="Anomaly detected.",
        )

        assert alert.alert_id == "alert-001"
        assert alert.source == "z_score_detector"
        assert alert.metric == "active_power_kw"
        assert alert.observed_value == pytest.approx(500.0)
        assert alert.score == pytest.approx(5.5)
        assert alert.severity is AnomalySeverity.CRITICAL

    def test_rejects_empty_alert_id(self) -> None:
        with pytest.raises(
            ValueError,
            match="alert_id must not be empty.",
        ):
            AnomalyAlert(
                alert_id=" ",
                timestamp=datetime.now(UTC),
                source="detector",
                metric="active_power_kw",
                observed_value=100.0,
                score=3.0,
                severity=AnomalySeverity.MEDIUM,
                message="Anomaly detected.",
            )

    def test_rejects_naive_timestamp(self) -> None:
        with pytest.raises(
            ValueError,
            match="timestamp must be timezone-aware.",
        ):
            AnomalyAlert(
                alert_id="alert-001",
                timestamp=datetime(
                    2026,
                    8,
                    18,
                    10,
                    0,
                ),
                source="detector",
                metric="active_power_kw",
                observed_value=100.0,
                score=3.0,
                severity=AnomalySeverity.MEDIUM,
                message="Anomaly detected.",
            )

    def test_rejects_empty_source(self) -> None:
        with pytest.raises(
            ValueError,
            match="source must not be empty.",
        ):
            AnomalyAlert(
                alert_id="alert-001",
                timestamp=datetime.now(UTC),
                source=" ",
                metric="active_power_kw",
                observed_value=100.0,
                score=3.0,
                severity=AnomalySeverity.MEDIUM,
                message="Anomaly detected.",
            )

    def test_rejects_empty_metric(self) -> None:
        with pytest.raises(
            ValueError,
            match="metric must not be empty.",
        ):
            AnomalyAlert(
                alert_id="alert-001",
                timestamp=datetime.now(UTC),
                source="detector",
                metric=" ",
                observed_value=100.0,
                score=3.0,
                severity=AnomalySeverity.MEDIUM,
                message="Anomaly detected.",
            )

    def test_rejects_empty_message(self) -> None:
        with pytest.raises(
            ValueError,
            match="message must not be empty.",
        ):
            AnomalyAlert(
                alert_id="alert-001",
                timestamp=datetime.now(UTC),
                source="detector",
                metric="active_power_kw",
                observed_value=100.0,
                score=3.0,
                severity=AnomalySeverity.MEDIUM,
                message=" ",
            )


class TestSeverityFromScore:
    """Tests for anomaly severity mapping."""

    @pytest.mark.parametrize(
        ("score", "expected"),
        [
            (0.0, AnomalySeverity.LOW),
            (2.99, AnomalySeverity.LOW),
            (3.0, AnomalySeverity.MEDIUM),
            (3.99, AnomalySeverity.MEDIUM),
            (4.0, AnomalySeverity.HIGH),
            (4.99, AnomalySeverity.HIGH),
            (5.0, AnomalySeverity.CRITICAL),
            (10.0, AnomalySeverity.CRITICAL),
        ],
    )
    def test_maps_positive_scores(
        self,
        score: float,
        expected: AnomalySeverity,
    ) -> None:
        assert severity_from_score(score) is expected

    @pytest.mark.parametrize(
        ("score", "expected"),
        [
            (-2.99, AnomalySeverity.LOW),
            (-3.0, AnomalySeverity.MEDIUM),
            (-4.0, AnomalySeverity.HIGH),
            (-5.0, AnomalySeverity.CRITICAL),
        ],
    )
    def test_uses_absolute_score(
        self,
        score: float,
        expected: AnomalySeverity,
    ) -> None:
        assert severity_from_score(score) is expected


class TestGenerateAnomalyAlerts:
    """Tests for anomaly alert generation."""

    def test_generates_alerts_for_flagged_rows(self) -> None:
        alerts = generate_anomaly_alerts(
            frame=_frame(),
            timestamp_column="timestamp",
            metric_column="active_power_kw",
            score_column="z_score",
            source="z_score_detector",
        )

        assert len(alerts) == 2
        assert all(isinstance(alert, AnomalyAlert) for alert in alerts)

    def test_ignores_non_anomalous_rows(self) -> None:
        alerts = generate_anomaly_alerts(
            frame=_frame(),
            timestamp_column="timestamp",
            metric_column="active_power_kw",
            score_column="z_score",
            source="z_score_detector",
        )

        assert [alert.observed_value for alert in alerts] == pytest.approx(
            [
                500.0,
                20.0,
            ]
        )

    def test_generates_unique_alert_ids(self) -> None:
        alerts = generate_anomaly_alerts(
            frame=_frame(),
            timestamp_column="timestamp",
            metric_column="active_power_kw",
            score_column="z_score",
            source="z_score_detector",
        )

        alert_ids = [alert.alert_id for alert in alerts]

        assert len(alert_ids) == len(set(alert_ids))

    def test_preserves_source(self) -> None:
        alerts = generate_anomaly_alerts(
            frame=_frame(),
            timestamp_column="timestamp",
            metric_column="active_power_kw",
            score_column="z_score",
            source="z_score_detector",
        )

        assert all(alert.source == "z_score_detector" for alert in alerts)

    def test_preserves_metric_name(self) -> None:
        alerts = generate_anomaly_alerts(
            frame=_frame(),
            timestamp_column="timestamp",
            metric_column="active_power_kw",
            score_column="z_score",
            source="z_score_detector",
        )

        assert all(alert.metric == "active_power_kw" for alert in alerts)

    def test_preserves_scores(self) -> None:
        alerts = generate_anomaly_alerts(
            frame=_frame(),
            timestamp_column="timestamp",
            metric_column="active_power_kw",
            score_column="z_score",
            source="z_score_detector",
        )

        assert [alert.score for alert in alerts] == pytest.approx(
            [
                5.5,
                -4.2,
            ]
        )

    def test_assigns_expected_severity(self) -> None:
        alerts = generate_anomaly_alerts(
            frame=_frame(),
            timestamp_column="timestamp",
            metric_column="active_power_kw",
            score_column="z_score",
            source="z_score_detector",
        )

        assert alerts[0].severity is AnomalySeverity.CRITICAL
        assert alerts[1].severity is AnomalySeverity.HIGH

    def test_generates_timezone_aware_timestamps(self) -> None:
        alerts = generate_anomaly_alerts(
            frame=_frame(),
            timestamp_column="timestamp",
            metric_column="active_power_kw",
            score_column="z_score",
            source="z_score_detector",
        )

        assert all(alert.timestamp.tzinfo is not None for alert in alerts)

    def test_generates_message(self) -> None:
        alerts = generate_anomaly_alerts(
            frame=_frame(),
            timestamp_column="timestamp",
            metric_column="active_power_kw",
            score_column="z_score",
            source="z_score_detector",
        )

        assert alerts[0].message == (
            "Anomaly detected for active_power_kw " "with score 5.500."
        )

    def test_returns_empty_list_for_empty_frame(self) -> None:
        alerts = generate_anomaly_alerts(
            frame=pd.DataFrame(),
            timestamp_column="timestamp",
            metric_column="active_power_kw",
            score_column="z_score",
            source="z_score_detector",
        )

        assert alerts == []

    def test_returns_empty_list_when_no_anomalies(self) -> None:
        frame = _frame()

        frame["is_anomaly"] = False

        alerts = generate_anomaly_alerts(
            frame=frame,
            timestamp_column="timestamp",
            metric_column="active_power_kw",
            score_column="z_score",
            source="z_score_detector",
        )

        assert alerts == []

    def test_supports_custom_anomaly_column(self) -> None:
        frame = _frame().rename(
            columns={
                "is_anomaly": "flagged",
            }
        )

        alerts = generate_anomaly_alerts(
            frame=frame,
            timestamp_column="timestamp",
            metric_column="active_power_kw",
            score_column="z_score",
            anomaly_column="flagged",
            source="z_score_detector",
        )

        assert len(alerts) == 2

    @pytest.mark.parametrize(
        ("argument", "message"),
        [
            (
                "timestamp_column",
                "timestamp_column must not be empty.",
            ),
            (
                "metric_column",
                "metric_column must not be empty.",
            ),
            (
                "score_column",
                "score_column must not be empty.",
            ),
            (
                "anomaly_column",
                "anomaly_column must not be empty.",
            ),
            (
                "source",
                "source must not be empty.",
            ),
        ],
    )
    def test_rejects_empty_arguments(
        self,
        argument: str,
        message: str,
    ) -> None:
        kwargs = {
            "frame": _frame(),
            "timestamp_column": "timestamp",
            "metric_column": "active_power_kw",
            "score_column": "z_score",
            "anomaly_column": "is_anomaly",
            "source": "z_score_detector",
        }

        kwargs[argument] = " "

        with pytest.raises(
            ValueError,
            match=message,
        ):
            generate_anomaly_alerts(**kwargs)

    def test_rejects_missing_required_columns(self) -> None:
        frame = _frame().drop(columns=["z_score"])

        with pytest.raises(
            ValueError,
            match=("Alert source frame is missing required columns"),
        ):
            generate_anomaly_alerts(
                frame=frame,
                timestamp_column="timestamp",
                metric_column="active_power_kw",
                score_column="z_score",
                source="z_score_detector",
            )

    def test_rejects_non_numeric_metric_column(self) -> None:
        frame = _frame()

        frame["active_power_kw"] = [
            "a",
            "b",
            "c",
            "d",
        ]

        with pytest.raises(
            TypeError,
            match="Metric column must contain numeric values.",
        ):
            generate_anomaly_alerts(
                frame=frame,
                timestamp_column="timestamp",
                metric_column="active_power_kw",
                score_column="z_score",
                source="z_score_detector",
            )

    def test_rejects_non_numeric_score_column(self) -> None:
        frame = _frame()

        frame["z_score"] = [
            "a",
            "b",
            "c",
            "d",
        ]

        with pytest.raises(
            TypeError,
            match="Score column must contain numeric values.",
        ):
            generate_anomaly_alerts(
                frame=frame,
                timestamp_column="timestamp",
                metric_column="active_power_kw",
                score_column="z_score",
                source="z_score_detector",
            )

    def test_rejects_non_boolean_anomaly_column(self) -> None:
        frame = _frame()

        frame["is_anomaly"] = [
            0,
            1,
            0,
            1,
        ]

        with pytest.raises(
            TypeError,
            match="Anomaly column must be boolean.",
        ):
            generate_anomaly_alerts(
                frame=frame,
                timestamp_column="timestamp",
                metric_column="active_power_kw",
                score_column="z_score",
                source="z_score_detector",
            )
