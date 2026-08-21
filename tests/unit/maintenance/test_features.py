"""Unit tests for EOIP predictive-maintenance feature engineering."""

from __future__ import annotations

import pandas as pd
import pytest

from eoip.maintenance.features import (
    add_delta_features,
    add_lag_features,
    add_rolling_features,
)


def _frame() -> pd.DataFrame:
    """Return deterministic multi-equipment maintenance data."""
    return pd.DataFrame(
        {
            "equipment_id": [
                "INV-001",
                "INV-001",
                "INV-001",
                "INV-001",
                "INV-002",
                "INV-002",
                "INV-002",
                "INV-002",
            ],
            "active_power_kw": [
                100.0,
                110.0,
                120.0,
                130.0,
                200.0,
                210.0,
                220.0,
                230.0,
            ],
            "temperature_c": [
                40.0,
                41.0,
                42.0,
                43.0,
                50.0,
                51.0,
                52.0,
                53.0,
            ],
        }
    )


class TestAddLagFeatures:
    """Tests for per-equipment lag features."""

    def test_adds_single_lag(self) -> None:
        result = add_lag_features(
            _frame(),
            equipment_id_column="equipment_id",
            feature_columns=["active_power_kw"],
            lags=[1],
        )

        assert "active_power_kw_lag_1" in result.columns

    def test_adds_multiple_features_and_lags(self) -> None:
        result = add_lag_features(
            _frame(),
            equipment_id_column="equipment_id",
            feature_columns=[
                "active_power_kw",
                "temperature_c",
            ],
            lags=[
                1,
                2,
            ],
        )

        assert "active_power_kw_lag_1" in result.columns
        assert "active_power_kw_lag_2" in result.columns
        assert "temperature_c_lag_1" in result.columns
        assert "temperature_c_lag_2" in result.columns

    def test_calculates_lag_values_correctly(self) -> None:
        result = add_lag_features(
            _frame(),
            equipment_id_column="equipment_id",
            feature_columns=["active_power_kw"],
            lags=[1],
        )

        assert pd.isna(
            result.loc[
                0,
                "active_power_kw_lag_1",
            ]
        )

        assert result.loc[
            1,
            "active_power_kw_lag_1",
        ] == pytest.approx(100.0)

        assert result.loc[
            2,
            "active_power_kw_lag_1",
        ] == pytest.approx(110.0)

    def test_lag_does_not_cross_equipment_boundary(self) -> None:
        result = add_lag_features(
            _frame(),
            equipment_id_column="equipment_id",
            feature_columns=["active_power_kw"],
            lags=[1],
        )

        assert pd.isna(
            result.loc[
                4,
                "active_power_kw_lag_1",
            ]
        )

        assert result.loc[
            5,
            "active_power_kw_lag_1",
        ] == pytest.approx(200.0)

    def test_supports_second_lag(self) -> None:
        result = add_lag_features(
            _frame(),
            equipment_id_column="equipment_id",
            feature_columns=["active_power_kw"],
            lags=[2],
        )

        assert pd.isna(
            result.loc[
                0,
                "active_power_kw_lag_2",
            ]
        )

        assert pd.isna(
            result.loc[
                1,
                "active_power_kw_lag_2",
            ]
        )

        assert result.loc[
            2,
            "active_power_kw_lag_2",
        ] == pytest.approx(100.0)

    def test_does_not_mutate_source_frame(self) -> None:
        frame = _frame()
        original = frame.copy(deep=True)

        add_lag_features(
            frame,
            equipment_id_column="equipment_id",
            feature_columns=["active_power_kw"],
            lags=[1],
        )

        pd.testing.assert_frame_equal(
            frame,
            original,
        )

    def test_rejects_empty_equipment_column_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="equipment_id_column must not be empty.",
        ):
            add_lag_features(
                _frame(),
                equipment_id_column=" ",
                feature_columns=["active_power_kw"],
                lags=[1],
            )

    def test_rejects_missing_equipment_column(self) -> None:
        with pytest.raises(
            ValueError,
            match=("Missing equipment identifier column: " "missing_equipment"),
        ):
            add_lag_features(
                _frame(),
                equipment_id_column="missing_equipment",
                feature_columns=["active_power_kw"],
                lags=[1],
            )

    def test_rejects_empty_feature_list(self) -> None:
        with pytest.raises(
            ValueError,
            match="At least one feature column must be provided.",
        ):
            add_lag_features(
                _frame(),
                equipment_id_column="equipment_id",
                feature_columns=[],
                lags=[1],
            )

    def test_rejects_missing_feature_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="Maintenance feature columns are missing",
        ):
            add_lag_features(
                _frame(),
                equipment_id_column="equipment_id",
                feature_columns=["missing_feature"],
                lags=[1],
            )

    def test_rejects_non_numeric_feature(self) -> None:
        frame = _frame()
        frame["status"] = "normal"

        with pytest.raises(
            TypeError,
            match="Feature column must be numeric: status",
        ):
            add_lag_features(
                frame,
                equipment_id_column="equipment_id",
                feature_columns=["status"],
                lags=[1],
            )

    def test_rejects_empty_lag_list(self) -> None:
        with pytest.raises(
            ValueError,
            match="At least one lag must be provided.",
        ):
            add_lag_features(
                _frame(),
                equipment_id_column="equipment_id",
                feature_columns=["active_power_kw"],
                lags=[],
            )

    @pytest.mark.parametrize(
        "lag",
        [
            0,
            -1,
            -10,
        ],
    )
    def test_rejects_non_positive_lag(
        self,
        lag: int,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="Lag values must be greater than zero.",
        ):
            add_lag_features(
                _frame(),
                equipment_id_column="equipment_id",
                feature_columns=["active_power_kw"],
                lags=[lag],
            )


class TestAddRollingFeatures:
    """Tests for per-equipment rolling features."""

    def test_adds_mean_and_std_columns(self) -> None:
        result = add_rolling_features(
            _frame(),
            equipment_id_column="equipment_id",
            feature_columns=["active_power_kw"],
            windows=[2],
        )

        assert "active_power_kw_rolling_mean_2" in result.columns

        assert "active_power_kw_rolling_std_2" in result.columns

    def test_rolling_mean_uses_previous_values_only(self) -> None:
        result = add_rolling_features(
            _frame(),
            equipment_id_column="equipment_id",
            feature_columns=["active_power_kw"],
            windows=[2],
        )

        assert pd.isna(
            result.loc[
                0,
                "active_power_kw_rolling_mean_2",
            ]
        )

        assert pd.isna(
            result.loc[
                1,
                "active_power_kw_rolling_mean_2",
            ]
        )

        assert result.loc[
            2,
            "active_power_kw_rolling_mean_2",
        ] == pytest.approx(105.0)

    def test_rolling_std_uses_previous_values_only(self) -> None:
        result = add_rolling_features(
            _frame(),
            equipment_id_column="equipment_id",
            feature_columns=["active_power_kw"],
            windows=[2],
        )

        assert result.loc[
            2,
            "active_power_kw_rolling_std_2",
        ] == pytest.approx(7.0710678119)

    def test_rolling_window_resets_for_new_equipment(self) -> None:
        result = add_rolling_features(
            _frame(),
            equipment_id_column="equipment_id",
            feature_columns=["active_power_kw"],
            windows=[2],
        )

        assert pd.isna(
            result.loc[
                4,
                "active_power_kw_rolling_mean_2",
            ]
        )

        assert pd.isna(
            result.loc[
                5,
                "active_power_kw_rolling_mean_2",
            ]
        )

        assert result.loc[
            6,
            "active_power_kw_rolling_mean_2",
        ] == pytest.approx(205.0)

    def test_supports_multiple_windows(self) -> None:
        result = add_rolling_features(
            _frame(),
            equipment_id_column="equipment_id",
            feature_columns=["active_power_kw"],
            windows=[
                2,
                3,
            ],
        )

        assert "active_power_kw_rolling_mean_2" in result.columns

        assert "active_power_kw_rolling_mean_3" in result.columns

    def test_supports_multiple_features(self) -> None:
        result = add_rolling_features(
            _frame(),
            equipment_id_column="equipment_id",
            feature_columns=[
                "active_power_kw",
                "temperature_c",
            ],
            windows=[2],
        )

        assert "active_power_kw_rolling_mean_2" in result.columns

        assert "temperature_c_rolling_mean_2" in result.columns

    def test_does_not_mutate_source_frame(self) -> None:
        frame = _frame()
        original = frame.copy(deep=True)

        add_rolling_features(
            frame,
            equipment_id_column="equipment_id",
            feature_columns=["active_power_kw"],
            windows=[2],
        )

        pd.testing.assert_frame_equal(
            frame,
            original,
        )

    def test_rejects_empty_window_list(self) -> None:
        with pytest.raises(
            ValueError,
            match="At least one rolling window must be provided.",
        ):
            add_rolling_features(
                _frame(),
                equipment_id_column="equipment_id",
                feature_columns=["active_power_kw"],
                windows=[],
            )

    @pytest.mark.parametrize(
        "window",
        [
            0,
            -1,
            -10,
        ],
    )
    def test_rejects_non_positive_window(
        self,
        window: int,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="Rolling windows must be greater than zero.",
        ):
            add_rolling_features(
                _frame(),
                equipment_id_column="equipment_id",
                feature_columns=["active_power_kw"],
                windows=[window],
            )


class TestAddDeltaFeatures:
    """Tests for per-equipment delta features."""

    def test_adds_delta_column(self) -> None:
        result = add_delta_features(
            _frame(),
            equipment_id_column="equipment_id",
            feature_columns=["active_power_kw"],
        )

        assert "active_power_kw_delta" in result.columns

    def test_calculates_delta_correctly(self) -> None:
        result = add_delta_features(
            _frame(),
            equipment_id_column="equipment_id",
            feature_columns=["active_power_kw"],
        )

        assert pd.isna(
            result.loc[
                0,
                "active_power_kw_delta",
            ]
        )

        assert result.loc[
            1,
            "active_power_kw_delta",
        ] == pytest.approx(10.0)

        assert result.loc[
            2,
            "active_power_kw_delta",
        ] == pytest.approx(10.0)

    def test_delta_resets_for_new_equipment(self) -> None:
        result = add_delta_features(
            _frame(),
            equipment_id_column="equipment_id",
            feature_columns=["active_power_kw"],
        )

        assert pd.isna(
            result.loc[
                4,
                "active_power_kw_delta",
            ]
        )

        assert result.loc[
            5,
            "active_power_kw_delta",
        ] == pytest.approx(10.0)

    def test_supports_multiple_features(self) -> None:
        result = add_delta_features(
            _frame(),
            equipment_id_column="equipment_id",
            feature_columns=[
                "active_power_kw",
                "temperature_c",
            ],
        )

        assert "active_power_kw_delta" in result.columns
        assert "temperature_c_delta" in result.columns

    def test_does_not_mutate_source_frame(self) -> None:
        frame = _frame()
        original = frame.copy(deep=True)

        add_delta_features(
            frame,
            equipment_id_column="equipment_id",
            feature_columns=["active_power_kw"],
        )

        pd.testing.assert_frame_equal(
            frame,
            original,
        )

    def test_rejects_empty_feature_list(self) -> None:
        with pytest.raises(
            ValueError,
            match="At least one feature column must be provided.",
        ):
            add_delta_features(
                _frame(),
                equipment_id_column="equipment_id",
                feature_columns=[],
            )

    def test_rejects_missing_feature_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="Maintenance feature columns are missing",
        ):
            add_delta_features(
                _frame(),
                equipment_id_column="equipment_id",
                feature_columns=["missing_feature"],
            )

    def test_rejects_non_numeric_feature(self) -> None:
        frame = _frame()
        frame["status"] = "normal"

        with pytest.raises(
            TypeError,
            match="Feature column must be numeric: status",
        ):
            add_delta_features(
                frame,
                equipment_id_column="equipment_id",
                feature_columns=["status"],
            )
