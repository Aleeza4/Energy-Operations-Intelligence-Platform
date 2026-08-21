"""Unit tests for EOIP anomaly threshold management."""

from __future__ import annotations

import pytest

from eoip.anomaly.thresholds import (
    AnomalyThreshold,
    ThresholdRegistry,
    ThresholdType,
)


class TestAnomalyThreshold:
    """Tests for anomaly threshold configuration."""

    def test_accepts_valid_z_score_threshold(self) -> None:
        threshold = AnomalyThreshold(
            name="z-score-default",
            threshold_type=ThresholdType.Z_SCORE,
            value=3.0,
        )

        assert threshold.name == "z-score-default"
        assert threshold.threshold_type is ThresholdType.Z_SCORE
        assert threshold.value == pytest.approx(3.0)
        assert threshold.enabled is True

    def test_accepts_valid_residual_threshold(self) -> None:
        threshold = AnomalyThreshold(
            name="residual-power",
            threshold_type=ThresholdType.RESIDUAL,
            value=50.0,
            enabled=False,
        )

        assert threshold.value == pytest.approx(50.0)
        assert threshold.enabled is False

    def test_accepts_negative_anomaly_score_threshold(self) -> None:
        threshold = AnomalyThreshold(
            name="isolation-score",
            threshold_type=ThresholdType.ANOMALY_SCORE,
            value=-0.25,
        )

        assert threshold.value == pytest.approx(-0.25)

    def test_rejects_empty_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="name must not be empty.",
        ):
            AnomalyThreshold(
                name=" ",
                threshold_type=ThresholdType.Z_SCORE,
                value=3.0,
            )

    @pytest.mark.parametrize(
        "value",
        [
            float("inf"),
            float("-inf"),
            float("nan"),
        ],
    )
    def test_rejects_non_finite_value(
        self,
        value: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="value must be finite.",
        ):
            AnomalyThreshold(
                name="invalid",
                threshold_type=ThresholdType.Z_SCORE,
                value=value,
            )

    @pytest.mark.parametrize(
        (
            "threshold_type",
            "value",
            "message",
        ),
        [
            (
                ThresholdType.Z_SCORE,
                0.0,
                "z_score threshold must be greater than zero.",
            ),
            (
                ThresholdType.Z_SCORE,
                -1.0,
                "z_score threshold must be greater than zero.",
            ),
            (
                ThresholdType.RESIDUAL,
                0.0,
                "residual threshold must be greater than zero.",
            ),
            (
                ThresholdType.RESIDUAL,
                -1.0,
                "residual threshold must be greater than zero.",
            ),
        ],
    )
    def test_rejects_non_positive_positive_only_thresholds(
        self,
        threshold_type: ThresholdType,
        value: float,
        message: str,
    ) -> None:
        with pytest.raises(
            ValueError,
            match=message,
        ):
            AnomalyThreshold(
                name="invalid",
                threshold_type=threshold_type,
                value=value,
            )


class TestThresholdRegistry:
    """Tests for anomaly threshold registry."""

    def test_starts_empty(self) -> None:
        registry = ThresholdRegistry()

        assert registry.count == 0
        assert registry.list_all() == ()
        assert registry.list_enabled() == ()

    def test_registers_threshold(self) -> None:
        registry = ThresholdRegistry()

        threshold = AnomalyThreshold(
            name="z-score",
            threshold_type=ThresholdType.Z_SCORE,
            value=3.0,
        )

        registry.register(threshold)

        assert registry.count == 1
        assert registry.contains("z-score")
        assert registry.get("z-score") == threshold

    def test_register_rejects_duplicate_name(self) -> None:
        registry = ThresholdRegistry()

        threshold = AnomalyThreshold(
            name="z-score",
            threshold_type=ThresholdType.Z_SCORE,
            value=3.0,
        )

        registry.register(threshold)

        with pytest.raises(
            ValueError,
            match="Threshold already exists: z-score",
        ):
            registry.register(threshold)

    def test_set_creates_threshold(self) -> None:
        registry = ThresholdRegistry()

        threshold = AnomalyThreshold(
            name="residual",
            threshold_type=ThresholdType.RESIDUAL,
            value=50.0,
        )

        registry.set(threshold)

        assert registry.get("residual") == threshold

    def test_set_replaces_existing_threshold(self) -> None:
        registry = ThresholdRegistry()

        first = AnomalyThreshold(
            name="z-score",
            threshold_type=ThresholdType.Z_SCORE,
            value=3.0,
        )

        second = AnomalyThreshold(
            name="z-score",
            threshold_type=ThresholdType.Z_SCORE,
            value=2.5,
        )

        registry.register(first)
        registry.set(second)

        assert registry.count == 1
        assert registry.get("z-score").value == pytest.approx(2.5)

    def test_get_rejects_empty_name(self) -> None:
        registry = ThresholdRegistry()

        with pytest.raises(
            ValueError,
            match="name must not be empty.",
        ):
            registry.get(" ")

    def test_get_raises_for_missing_threshold(self) -> None:
        registry = ThresholdRegistry()

        with pytest.raises(
            KeyError,
            match="Threshold not found: missing",
        ):
            registry.get("missing")

    def test_remove_threshold(self) -> None:
        registry = ThresholdRegistry()

        registry.register(
            AnomalyThreshold(
                name="z-score",
                threshold_type=ThresholdType.Z_SCORE,
                value=3.0,
            )
        )

        registry.remove("z-score")

        assert registry.count == 0
        assert not registry.contains("z-score")

    def test_remove_rejects_empty_name(self) -> None:
        registry = ThresholdRegistry()

        with pytest.raises(
            ValueError,
            match="name must not be empty.",
        ):
            registry.remove(" ")

    def test_remove_raises_for_missing_threshold(self) -> None:
        registry = ThresholdRegistry()

        with pytest.raises(
            KeyError,
            match="Threshold not found: missing",
        ):
            registry.remove("missing")

    def test_list_all_returns_sorted_thresholds(self) -> None:
        registry = ThresholdRegistry()

        registry.register(
            AnomalyThreshold(
                name="z-score",
                threshold_type=ThresholdType.Z_SCORE,
                value=3.0,
            )
        )

        registry.register(
            AnomalyThreshold(
                name="residual",
                threshold_type=ThresholdType.RESIDUAL,
                value=50.0,
            )
        )

        registry.register(
            AnomalyThreshold(
                name="isolation-score",
                threshold_type=ThresholdType.ANOMALY_SCORE,
                value=-0.2,
            )
        )

        assert [threshold.name for threshold in registry.list_all()] == [
            "isolation-score",
            "residual",
            "z-score",
        ]

    def test_list_enabled_excludes_disabled_thresholds(self) -> None:
        registry = ThresholdRegistry()

        registry.register(
            AnomalyThreshold(
                name="enabled",
                threshold_type=ThresholdType.Z_SCORE,
                value=3.0,
                enabled=True,
            )
        )

        registry.register(
            AnomalyThreshold(
                name="disabled",
                threshold_type=ThresholdType.RESIDUAL,
                value=50.0,
                enabled=False,
            )
        )

        assert [threshold.name for threshold in registry.list_enabled()] == [
            "enabled",
        ]

    def test_contains_returns_false_for_missing_threshold(self) -> None:
        registry = ThresholdRegistry()

        assert registry.contains("missing") is False

    def test_clear_removes_all_thresholds(self) -> None:
        registry = ThresholdRegistry()

        registry.register(
            AnomalyThreshold(
                name="z-score",
                threshold_type=ThresholdType.Z_SCORE,
                value=3.0,
            )
        )

        registry.register(
            AnomalyThreshold(
                name="residual",
                threshold_type=ThresholdType.RESIDUAL,
                value=50.0,
            )
        )

        registry.clear()

        assert registry.count == 0
        assert registry.list_all() == ()
