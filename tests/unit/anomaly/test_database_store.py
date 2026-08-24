"""Unit tests for the EOIP database-backed anomaly store."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from eoip.anomaly.database_store import DatabaseAnomalyStore
from eoip.anomaly.storage import StoredAnomalyRun


@pytest.fixture
def engine() -> Generator[Engine, None, None]:
    """Create an isolated in-memory database."""
    database_engine = create_engine(
        "sqlite+pysqlite:///:memory:",
    )

    try:
        yield database_engine
    finally:
        database_engine.dispose()


@pytest.fixture
def store(
    engine: Engine,
) -> DatabaseAnomalyStore:
    """Create an anomaly store with its schema."""
    anomaly_store = DatabaseAnomalyStore(
        engine=engine,
    )

    anomaly_store.create_schema()

    return anomaly_store


def _frame() -> pd.DataFrame:
    """Return valid anomaly detection results."""
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
            "anomaly_score": [
                0.10,
                -0.55,
                0.08,
                -0.42,
            ],
            "is_anomaly": [
                False,
                True,
                False,
                True,
            ],
        }
    )


def _generated_at() -> datetime:
    """Return a deterministic timezone-aware generation time."""
    return datetime(
        2026,
        8,
        18,
        12,
        0,
        tzinfo=UTC,
    )


def _save(
    store: DatabaseAnomalyStore,
) -> StoredAnomalyRun:
    """Persist one anomaly run."""
    return store.save(
        detector_name="isolation_forest",
        target_column="active_power_kw",
        result_frame=_frame(),
        generated_at=_generated_at(),
    )


class TestDatabaseAnomalyStoreSave:
    """Tests for anomaly persistence."""

    def test_save_returns_metadata(
        self,
        store: DatabaseAnomalyStore,
    ) -> None:
        metadata = _save(store)

        assert metadata.anomaly_run_id
        assert metadata.detector_name == "isolation_forest"
        assert metadata.target_column == "active_power_kw"
        assert metadata.generated_at == _generated_at()
        assert metadata.row_count == 4
        assert metadata.anomaly_count == 2

    def test_save_generates_unique_run_ids(
        self,
        store: DatabaseAnomalyStore,
    ) -> None:
        first = _save(store)
        second = _save(store)

        assert first.anomaly_run_id != second.anomaly_run_id

    def test_save_counts_anomalies(
        self,
        store: DatabaseAnomalyStore,
    ) -> None:
        frame = _frame()

        frame["is_anomaly"] = [
            True,
            True,
            True,
            False,
        ]

        metadata = store.save(
            detector_name="isolation_forest",
            target_column="active_power_kw",
            result_frame=frame,
            generated_at=_generated_at(),
        )

        assert metadata.row_count == 4
        assert metadata.anomaly_count == 3

    def test_save_allows_zero_anomalies(
        self,
        store: DatabaseAnomalyStore,
    ) -> None:
        frame = _frame()

        frame["is_anomaly"] = False

        metadata = store.save(
            detector_name="isolation_forest",
            target_column="active_power_kw",
            result_frame=frame,
            generated_at=_generated_at(),
        )

        assert metadata.row_count == 4
        assert metadata.anomaly_count == 0

    def test_rejects_empty_detector_name(
        self,
        store: DatabaseAnomalyStore,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="detector_name must not be empty.",
        ):
            store.save(
                detector_name=" ",
                target_column="active_power_kw",
                result_frame=_frame(),
                generated_at=_generated_at(),
            )

    def test_rejects_empty_target_column(
        self,
        store: DatabaseAnomalyStore,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="target_column must not be empty.",
        ):
            store.save(
                detector_name="isolation_forest",
                target_column=" ",
                result_frame=_frame(),
                generated_at=_generated_at(),
            )

    def test_rejects_naive_generated_at(
        self,
        store: DatabaseAnomalyStore,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="generated_at must be timezone-aware.",
        ):
            store.save(
                detector_name="isolation_forest",
                target_column="active_power_kw",
                result_frame=_frame(),
                generated_at=datetime(
                    2026,
                    8,
                    18,
                    12,
                    0,
                ),
            )

    def test_rejects_invalid_result_frame(
        self,
        store: DatabaseAnomalyStore,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="Anomaly result frame must not be empty.",
        ):
            store.save(
                detector_name="isolation_forest",
                target_column="active_power_kw",
                result_frame=pd.DataFrame(),
                generated_at=_generated_at(),
            )


class TestDatabaseAnomalyStoreLoad:
    """Tests for loading persisted anomaly results."""

    def test_load_returns_saved_results(
        self,
        store: DatabaseAnomalyStore,
    ) -> None:
        metadata = _save(store)

        loaded = store.load(
            anomaly_run_id=metadata.anomaly_run_id,
        )

        assert len(loaded) == 4

        assert list(loaded.columns) == [
            "timestamp",
            "is_anomaly",
            "score",
        ]

        assert loaded["is_anomaly"].tolist() == [
            False,
            True,
            False,
            True,
        ]

        assert loaded["score"].tolist() == pytest.approx(
            [
                0.10,
                -0.55,
                0.08,
                -0.42,
            ]
        )

    def test_load_sorts_results_by_timestamp(
        self,
        store: DatabaseAnomalyStore,
    ) -> None:
        frame = (
            _frame()
            .iloc[
                [
                    2,
                    0,
                    3,
                    1,
                ]
            ]
            .reset_index(drop=True)
        )

        metadata = store.save(
            detector_name="isolation_forest",
            target_column="active_power_kw",
            result_frame=frame,
            generated_at=_generated_at(),
        )

        loaded = store.load(
            anomaly_run_id=metadata.anomaly_run_id,
        )

        assert loaded["timestamp"].is_monotonic_increasing

    def test_load_normalizes_timestamps_to_utc(
        self,
        store: DatabaseAnomalyStore,
    ) -> None:
        metadata = _save(store)

        loaded = store.load(
            anomaly_run_id=metadata.anomaly_run_id,
        )

        assert isinstance(
            loaded["timestamp"].dtype,
            pd.DatetimeTZDtype,
        )

        assert str(loaded["timestamp"].dt.tz) == "UTC"

    def test_rejects_empty_anomaly_run_id(
        self,
        store: DatabaseAnomalyStore,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="anomaly_run_id must not be empty.",
        ):
            store.load(
                anomaly_run_id=" ",
            )

    def test_raises_for_missing_anomaly_run(
        self,
        store: DatabaseAnomalyStore,
    ) -> None:
        with pytest.raises(
            KeyError,
            match="Anomaly run not found",
        ):
            store.load(
                anomaly_run_id="missing-run",
            )


class TestDatabaseAnomalyStoreMetadata:
    """Tests for stored anomaly metadata."""

    def test_get_metadata_returns_saved_metadata(
        self,
        store: DatabaseAnomalyStore,
    ) -> None:
        saved = _save(store)

        loaded = store.get_metadata(
            anomaly_run_id=saved.anomaly_run_id,
        )

        assert loaded.anomaly_run_id == saved.anomaly_run_id
        assert loaded.detector_name == saved.detector_name
        assert loaded.target_column == saved.target_column
        assert loaded.row_count == saved.row_count
        assert loaded.anomaly_count == saved.anomaly_count

    def test_metadata_timestamp_is_timezone_aware(
        self,
        store: DatabaseAnomalyStore,
    ) -> None:
        saved = _save(store)

        loaded = store.get_metadata(
            anomaly_run_id=saved.anomaly_run_id,
        )

        assert loaded.generated_at.tzinfo is not None

    def test_rejects_empty_anomaly_run_id(
        self,
        store: DatabaseAnomalyStore,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="anomaly_run_id must not be empty.",
        ):
            store.get_metadata(
                anomaly_run_id=" ",
            )

    def test_raises_for_missing_anomaly_run(
        self,
        store: DatabaseAnomalyStore,
    ) -> None:
        with pytest.raises(
            KeyError,
            match="Anomaly run not found",
        ):
            store.get_metadata(
                anomaly_run_id="missing-run",
            )


class TestDatabaseAnomalyStoreDelete:
    """Tests for deleting anomaly runs."""

    def test_delete_removes_anomaly_run(
        self,
        store: DatabaseAnomalyStore,
    ) -> None:
        metadata = _save(store)

        store.delete(
            anomaly_run_id=metadata.anomaly_run_id,
        )

        with pytest.raises(
            KeyError,
            match="Anomaly run not found",
        ):
            store.load(
                anomaly_run_id=metadata.anomaly_run_id,
            )

    def test_delete_removes_metadata(
        self,
        store: DatabaseAnomalyStore,
    ) -> None:
        metadata = _save(store)

        store.delete(
            anomaly_run_id=metadata.anomaly_run_id,
        )

        with pytest.raises(
            KeyError,
            match="Anomaly run not found",
        ):
            store.get_metadata(
                anomaly_run_id=metadata.anomaly_run_id,
            )

    def test_delete_does_not_affect_other_runs(
        self,
        store: DatabaseAnomalyStore,
    ) -> None:
        first = _save(store)
        second = _save(store)

        store.delete(
            anomaly_run_id=first.anomaly_run_id,
        )

        loaded = store.load(
            anomaly_run_id=second.anomaly_run_id,
        )

        assert len(loaded) == 4

    def test_rejects_empty_anomaly_run_id(
        self,
        store: DatabaseAnomalyStore,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="anomaly_run_id must not be empty.",
        ):
            store.delete(
                anomaly_run_id=" ",
            )

    def test_raises_for_missing_anomaly_run(
        self,
        store: DatabaseAnomalyStore,
    ) -> None:
        with pytest.raises(
            KeyError,
            match="Anomaly run not found",
        ):
            store.delete(
                anomaly_run_id="missing-run",
            )
