"""Unit tests for EOIP recommendation prioritization."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from eoip.optimization.recommendation_priority import (
    RecommendationPriorityWeights,
    prioritize_recommendations,
)


def _frame() -> pd.DataFrame:
    """Return deterministic recommendation-priority inputs."""
    return pd.DataFrame(
        {
            "equipment_id": [
                "INV-001",
                "INV-002",
                "INV-003",
                "INV-004",
            ],
            "recommendation_type": [
                "maintenance",
                "performance_recovery",
                "monitor",
                "no_action",
            ],
            "risk_score": [
                0.90,
                0.60,
                0.40,
                0.10,
            ],
            "expected_benefit": [
                10000.0,
                7000.0,
                2000.0,
                0.0,
            ],
            "recoverable_energy_kwh": [
                500.0,
                800.0,
                100.0,
                0.0,
            ],
        }
    )


class TestRecommendationPriorityWeights:
    """Tests for recommendation-priority weights."""

    def test_default_weights_sum_to_one(self) -> None:
        weights = RecommendationPriorityWeights()

        total = (
            weights.risk_score
            + weights.expected_benefit
            + weights.recoverable_energy
            + weights.recommendation_type
        )

        assert total == pytest.approx(1.0)

    def test_accepts_custom_weights(self) -> None:
        weights = RecommendationPriorityWeights(
            risk_score=0.50,
            expected_benefit=0.20,
            recoverable_energy=0.20,
            recommendation_type=0.10,
        )

        assert weights.risk_score == pytest.approx(0.50)

    def test_rejects_negative_weight(self) -> None:
        with pytest.raises(
            ValueError,
            match=("Recommendation priority weights must not be negative."),
        ):
            RecommendationPriorityWeights(
                risk_score=-0.10,
                expected_benefit=0.40,
                recoverable_energy=0.40,
                recommendation_type=0.30,
            )

    @pytest.mark.parametrize(
        "value",
        [
            math.nan,
            math.inf,
            -math.inf,
        ],
    )
    def test_rejects_non_finite_weight(
        self,
        value: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="Recommendation priority weights must be finite.",
        ):
            RecommendationPriorityWeights(
                risk_score=value,
            )

    def test_rejects_weights_not_summing_to_one(self) -> None:
        with pytest.raises(
            ValueError,
            match="Recommendation priority weights must sum to 1.",
        ):
            RecommendationPriorityWeights(
                risk_score=0.50,
                expected_benefit=0.30,
                recoverable_energy=0.30,
                recommendation_type=0.10,
            )


class TestPrioritizeRecommendations:
    """Tests for recommendation prioritization."""

    def test_adds_priority_columns(self) -> None:
        result = prioritize_recommendations(frame=_frame())

        assert "recommendation_priority_score" in result.columns

        assert "recommendation_priority_rank" in result.columns

    def test_preserves_row_count(self) -> None:
        frame = _frame()

        result = prioritize_recommendations(frame=frame)

        assert len(result) == len(frame)

    def test_priority_scores_are_between_zero_and_one(
        self,
    ) -> None:
        result = prioritize_recommendations(frame=_frame())

        assert (
            result["recommendation_priority_score"]
            .between(
                0.0,
                1.0,
            )
            .all()
        )

    def test_priority_scores_descend(self) -> None:
        result = prioritize_recommendations(frame=_frame())

        assert result["recommendation_priority_score"].is_monotonic_decreasing

    def test_assigns_sequential_ranks(self) -> None:
        result = prioritize_recommendations(frame=_frame())

        assert result["recommendation_priority_rank"].tolist() == [
            1,
            2,
            3,
            4,
        ]

    def test_high_value_maintenance_action_ranks_first(
        self,
    ) -> None:
        result = prioritize_recommendations(frame=_frame())

        assert (
            result.loc[
                0,
                "equipment_id",
            ]
            == "INV-001"
        )

    def test_no_action_low_value_asset_ranks_last(
        self,
    ) -> None:
        result = prioritize_recommendations(frame=_frame())

        assert (
            result.loc[
                len(result) - 1,
                "equipment_id",
            ]
            == "INV-004"
        )

    def test_maintenance_type_receives_highest_type_score(
        self,
    ) -> None:
        frame = pd.DataFrame(
            {
                "equipment_id": [
                    "INV-001",
                    "INV-002",
                    "INV-003",
                    "INV-004",
                ],
                "recommendation_type": [
                    "maintenance",
                    "performance_recovery",
                    "monitor",
                    "no_action",
                ],
                "risk_score": [
                    0.50,
                    0.50,
                    0.50,
                    0.50,
                ],
                "expected_benefit": [
                    1000.0,
                    1000.0,
                    1000.0,
                    1000.0,
                ],
                "recoverable_energy_kwh": [
                    100.0,
                    100.0,
                    100.0,
                    100.0,
                ],
            }
        )

        weights = RecommendationPriorityWeights(
            risk_score=0.0,
            expected_benefit=0.0,
            recoverable_energy=0.0,
            recommendation_type=1.0,
        )

        result = prioritize_recommendations(
            frame=frame,
            weights=weights,
        )

        assert result["equipment_id"].tolist() == [
            "INV-001",
            "INV-002",
            "INV-003",
            "INV-004",
        ]

    def test_expected_benefit_is_normalized(self) -> None:
        frame = pd.DataFrame(
            {
                "equipment_id": [
                    "INV-001",
                    "INV-002",
                ],
                "recommendation_type": [
                    "monitor",
                    "monitor",
                ],
                "risk_score": [
                    0.50,
                    0.50,
                ],
                "expected_benefit": [
                    1000.0,
                    500.0,
                ],
                "recoverable_energy_kwh": [
                    0.0,
                    0.0,
                ],
            }
        )

        weights = RecommendationPriorityWeights(
            risk_score=0.0,
            expected_benefit=1.0,
            recoverable_energy=0.0,
            recommendation_type=0.0,
        )

        result = prioritize_recommendations(
            frame=frame,
            weights=weights,
        )

        assert result.loc[
            0,
            "recommendation_priority_score",
        ] == pytest.approx(1.0)

        assert result.loc[
            1,
            "recommendation_priority_score",
        ] == pytest.approx(0.5)

    def test_recoverable_energy_is_normalized(self) -> None:
        frame = pd.DataFrame(
            {
                "equipment_id": [
                    "INV-001",
                    "INV-002",
                ],
                "recommendation_type": [
                    "monitor",
                    "monitor",
                ],
                "risk_score": [
                    0.50,
                    0.50,
                ],
                "expected_benefit": [
                    0.0,
                    0.0,
                ],
                "recoverable_energy_kwh": [
                    1000.0,
                    250.0,
                ],
            }
        )

        weights = RecommendationPriorityWeights(
            risk_score=0.0,
            expected_benefit=0.0,
            recoverable_energy=1.0,
            recommendation_type=0.0,
        )

        result = prioritize_recommendations(
            frame=frame,
            weights=weights,
        )

        assert result.loc[
            0,
            "recommendation_priority_score",
        ] == pytest.approx(1.0)

        assert result.loc[
            1,
            "recommendation_priority_score",
        ] == pytest.approx(0.25)

    def test_zero_benefits_are_handled_safely(self) -> None:
        frame = _frame()

        frame["expected_benefit"] = 0.0

        result = prioritize_recommendations(frame=frame)

        assert result["recommendation_priority_score"].notna().all()

    def test_zero_recoverable_energy_is_handled_safely(
        self,
    ) -> None:
        frame = _frame()

        frame["recoverable_energy_kwh"] = 0.0

        result = prioritize_recommendations(frame=frame)

        assert result["recommendation_priority_score"].notna().all()

    def test_ties_are_broken_by_equipment_id(self) -> None:
        frame = pd.DataFrame(
            {
                "equipment_id": [
                    "INV-002",
                    "INV-001",
                ],
                "recommendation_type": [
                    "monitor",
                    "monitor",
                ],
                "risk_score": [
                    0.50,
                    0.50,
                ],
                "expected_benefit": [
                    1000.0,
                    1000.0,
                ],
                "recoverable_energy_kwh": [
                    100.0,
                    100.0,
                ],
            }
        )

        result = prioritize_recommendations(frame=frame)

        assert result["equipment_id"].tolist() == [
            "INV-001",
            "INV-002",
        ]

    def test_does_not_mutate_source_frame(self) -> None:
        frame = _frame()
        original = frame.copy(deep=True)

        prioritize_recommendations(frame=frame)

        pd.testing.assert_frame_equal(
            frame,
            original,
        )

    def test_rejects_empty_frame(self) -> None:
        with pytest.raises(
            ValueError,
            match=("Recommendation priority frame must not be empty."),
        ):
            prioritize_recommendations(frame=pd.DataFrame())

    def test_rejects_missing_required_column(self) -> None:
        frame = _frame().drop(columns=["risk_score"])

        with pytest.raises(
            ValueError,
            match=("Recommendation priority frame is missing " "required columns"),
        ):
            prioritize_recommendations(frame=frame)

    def test_rejects_non_numeric_risk_score(self) -> None:
        frame = _frame()

        frame["risk_score"] = [
            "a",
            "b",
            "c",
            "d",
        ]

        with pytest.raises(
            TypeError,
            match="Column 'risk_score' must be numeric.",
        ):
            prioritize_recommendations(frame=frame)

    def test_rejects_missing_numeric_value(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "expected_benefit",
        ] = math.nan

        with pytest.raises(
            ValueError,
            match=("Column 'expected_benefit' must not contain " "missing values."),
        ):
            prioritize_recommendations(frame=frame)

    def test_rejects_non_finite_numeric_value(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "recoverable_energy_kwh",
        ] = math.inf

        with pytest.raises(
            ValueError,
            match=(
                "Column 'recoverable_energy_kwh' must contain only " "finite values."
            ),
        ):
            prioritize_recommendations(frame=frame)

    @pytest.mark.parametrize(
        "risk_score",
        [
            -0.01,
            1.01,
        ],
    )
    def test_rejects_invalid_risk_score(
        self,
        risk_score: float,
    ) -> None:
        frame = _frame()

        frame.loc[
            0,
            "risk_score",
        ] = risk_score

        with pytest.raises(
            ValueError,
            match="Risk scores must be between 0 and 1.",
        ):
            prioritize_recommendations(frame=frame)

    def test_rejects_negative_expected_benefit(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "expected_benefit",
        ] = -1.0

        with pytest.raises(
            ValueError,
            match="Expected benefits must not be negative.",
        ):
            prioritize_recommendations(frame=frame)

    def test_rejects_negative_recoverable_energy(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "recoverable_energy_kwh",
        ] = -1.0

        with pytest.raises(
            ValueError,
            match=("Recoverable energy values must not be negative."),
        ):
            prioritize_recommendations(frame=frame)

    def test_rejects_blank_equipment_identifier(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "equipment_id",
        ] = " "

        with pytest.raises(
            ValueError,
            match="Equipment identifiers must not be empty.",
        ):
            prioritize_recommendations(frame=frame)

    def test_rejects_unsupported_recommendation_type(
        self,
    ) -> None:
        frame = _frame()

        frame.loc[
            0,
            "recommendation_type",
        ] = "unknown"

        with pytest.raises(
            ValueError,
            match="Unsupported recommendation type: unknown",
        ):
            prioritize_recommendations(frame=frame)

    def test_supports_custom_column_names(self) -> None:
        frame = _frame().rename(
            columns={
                "equipment_id": "asset_id",
                "recommendation_type": "action_type",
                "risk_score": "asset_risk",
                "expected_benefit": "benefit",
                "recoverable_energy_kwh": "recoverable",
            }
        )

        result = prioritize_recommendations(
            frame=frame,
            equipment_id_column="asset_id",
            recommendation_type_column="action_type",
            risk_score_column="asset_risk",
            expected_benefit_column="benefit",
            recoverable_energy_column="recoverable",
        )

        assert "recommendation_priority_score" in result.columns

        assert "recommendation_priority_rank" in result.columns
