"""Unit tests for EOIP bulk-loading utilities."""

from __future__ import annotations

import pytest

from eoip.database.bulk.base import (
    chunked,
    normalize_records,
    validate_uniform_columns,
)


class TestChunked:
    """Tests for record batching."""

    def test_chunked_splits_records_into_batches(self) -> None:
        records = [1, 2, 3, 4, 5]

        result = list(
            chunked(
                records,
                batch_size=2,
            )
        )

        assert result == [
            [1, 2],
            [3, 4],
            [5],
        ]

    def test_chunked_handles_exact_batch_size(self) -> None:
        records = [1, 2, 3, 4]

        result = list(
            chunked(
                records,
                batch_size=2,
            )
        )

        assert result == [
            [1, 2],
            [3, 4],
        ]

    def test_chunked_handles_single_batch(self) -> None:
        records = [1, 2]

        result = list(
            chunked(
                records,
                batch_size=10,
            )
        )

        assert result == [[1, 2]]

    def test_chunked_handles_empty_input(self) -> None:
        result = list(
            chunked(
                [],
                batch_size=5,
            )
        )

        assert result == []

    def test_chunked_supports_generators(self) -> None:
        records = (number for number in range(5))

        result = list(
            chunked(
                records,
                batch_size=2,
            )
        )

        assert result == [
            [0, 1],
            [2, 3],
            [4],
        ]

    @pytest.mark.parametrize(
        "batch_size",
        [
            0,
            -1,
            -100,
        ],
    )
    def test_chunked_rejects_invalid_batch_size(
        self,
        batch_size: int,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="batch_size must be greater than zero",
        ):
            list(
                chunked(
                    [1, 2, 3],
                    batch_size=batch_size,
                )
            )


class TestNormalizeRecords:
    """Tests for record normalization."""

    def test_normalize_records_returns_list(self) -> None:
        records = (
            {"plant_id": "PLANT001"},
            {"plant_id": "PLANT002"},
        )

        result = normalize_records(records)

        assert result == [
            {"plant_id": "PLANT001"},
            {"plant_id": "PLANT002"},
        ]

    def test_normalize_records_creates_independent_dictionaries(
        self,
    ) -> None:
        original = {
            "plant_id": "PLANT001",
        }

        result = normalize_records([original])

        assert result[0] == original
        assert result[0] is not original

    def test_normalize_records_handles_empty_input(self) -> None:
        result = normalize_records([])

        assert result == []


class TestValidateUniformColumns:
    """Tests for bulk-record column validation."""

    def test_returns_columns_from_first_record(self) -> None:
        records = [
            {
                "plant_id": "PLANT001",
                "status": "operational",
            },
            {
                "plant_id": "PLANT002",
                "status": "maintenance",
            },
        ]

        result = validate_uniform_columns(records)

        assert result == (
            "plant_id",
            "status",
        )

    def test_column_order_comes_from_first_record(self) -> None:
        records = [
            {
                "status": "operational",
                "plant_id": "PLANT001",
            },
            {
                "plant_id": "PLANT002",
                "status": "maintenance",
            },
        ]

        result = validate_uniform_columns(records)

        assert result == (
            "status",
            "plant_id",
        )

    def test_accepts_same_columns_in_different_order(self) -> None:
        records = [
            {
                "plant_id": "PLANT001",
                "status": "operational",
            },
            {
                "status": "maintenance",
                "plant_id": "PLANT002",
            },
        ]

        result = validate_uniform_columns(records)

        assert result == (
            "plant_id",
            "status",
        )

    def test_rejects_empty_records(self) -> None:
        with pytest.raises(
            ValueError,
            match="records must not be empty",
        ):
            validate_uniform_columns([])

    def test_rejects_record_with_no_columns(self) -> None:
        with pytest.raises(
            ValueError,
            match="records must contain at least one column",
        ):
            validate_uniform_columns([{}])

    def test_rejects_missing_column(self) -> None:
        records = [
            {
                "plant_id": "PLANT001",
                "status": "operational",
            },
            {
                "plant_id": "PLANT002",
            },
        ]

        with pytest.raises(
            ValueError,
            match=(
                "All bulk records must contain identical columns; "
                "record 2 does not match the first record"
            ),
        ):
            validate_uniform_columns(records)

    def test_rejects_extra_column(self) -> None:
        records = [
            {
                "plant_id": "PLANT001",
            },
            {
                "plant_id": "PLANT002",
                "status": "operational",
            },
        ]

        with pytest.raises(
            ValueError,
            match=(
                "All bulk records must contain identical columns; "
                "record 2 does not match the first record"
            ),
        ):
            validate_uniform_columns(records)
