"""Database-backed anomaly storage for EOIP."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pandas as pd
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    delete,
    insert,
    select,
)
from sqlalchemy.engine import Engine

from eoip.anomaly.storage import (
    StoredAnomalyRun,
    validate_anomaly_frame_for_storage,
)

_METADATA = MetaData()


anomaly_runs = Table(
    "anomaly_runs",
    _METADATA,
    Column(
        "anomaly_run_id",
        String(36),
        primary_key=True,
    ),
    Column(
        "detector_name",
        String(255),
        nullable=False,
    ),
    Column(
        "target_column",
        String(255),
        nullable=False,
    ),
    Column(
        "generated_at",
        DateTime(timezone=True),
        nullable=False,
    ),
    Column(
        "row_count",
        Integer,
        nullable=False,
    ),
    Column(
        "anomaly_count",
        Integer,
        nullable=False,
    ),
)


anomaly_values = Table(
    "anomaly_values",
    _METADATA,
    Column(
        "anomaly_run_id",
        String(36),
        nullable=False,
        index=True,
    ),
    Column(
        "timestamp",
        DateTime(timezone=True),
        nullable=False,
    ),
    Column(
        "is_anomaly",
        Boolean,
        nullable=False,
    ),
    Column(
        "score",
        Float,
        nullable=True,
    ),
)


class DatabaseAnomalyStore:
    """Persist anomaly detection results using SQLAlchemy."""

    def __init__(
        self,
        *,
        engine: Engine,
    ) -> None:
        """Initialize the anomaly database store."""
        self._engine = engine

    def create_schema(self) -> None:
        """Create anomaly storage tables when absent."""
        _METADATA.create_all(
            self._engine,
            tables=[
                anomaly_runs,
                anomaly_values,
            ],
        )

    def save(
        self,
        *,
        detector_name: str,
        target_column: str,
        result_frame: pd.DataFrame,
        generated_at: datetime,
    ) -> StoredAnomalyRun:
        """Persist anomaly results and return storage metadata."""
        if not detector_name.strip():
            raise ValueError("detector_name must not be empty.")

        if not target_column.strip():
            raise ValueError("target_column must not be empty.")

        if generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware.")

        validate_anomaly_frame_for_storage(result_frame)

        anomaly_run_id = str(uuid4())

        anomaly_count = int(result_frame["is_anomaly"].sum())

        metadata = StoredAnomalyRun(
            anomaly_run_id=anomaly_run_id,
            detector_name=detector_name,
            target_column=target_column,
            generated_at=generated_at,
            row_count=len(result_frame),
            anomaly_count=anomaly_count,
        )

        score_column = self._resolve_score_column(result_frame)

        value_records = []

        for row in result_frame.itertuples(index=False):
            timestamp = row.timestamp

            is_anomaly = bool(row.is_anomaly)

            score = None

            if score_column is not None:
                raw_score = getattr(
                    row,
                    score_column,
                )

                if pd.notna(raw_score):
                    score = float(raw_score)

            if isinstance(
                timestamp,
                pd.Timestamp,
            ):
                timestamp = timestamp.to_pydatetime()

            value_records.append(
                {
                    "anomaly_run_id": anomaly_run_id,
                    "timestamp": timestamp,
                    "is_anomaly": is_anomaly,
                    "score": score,
                }
            )

        with self._engine.begin() as connection:
            connection.execute(
                insert(anomaly_runs),
                {
                    "anomaly_run_id": metadata.anomaly_run_id,
                    "detector_name": metadata.detector_name,
                    "target_column": metadata.target_column,
                    "generated_at": metadata.generated_at,
                    "row_count": metadata.row_count,
                    "anomaly_count": metadata.anomaly_count,
                },
            )

            connection.execute(
                insert(anomaly_values),
                value_records,
            )

        return metadata

    def load(
        self,
        *,
        anomaly_run_id: str,
    ) -> pd.DataFrame:
        """Load stored anomaly detection results."""
        if not anomaly_run_id.strip():
            raise ValueError("anomaly_run_id must not be empty.")

        statement = (
            select(
                anomaly_values.c.timestamp,
                anomaly_values.c.is_anomaly,
                anomaly_values.c.score,
            )
            .where(anomaly_values.c.anomaly_run_id == anomaly_run_id)
            .order_by(anomaly_values.c.timestamp)
        )

        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()

        if not rows:
            raise KeyError(f"Anomaly run not found: {anomaly_run_id}")

        frame = pd.DataFrame(rows)

        frame["timestamp"] = pd.to_datetime(
            frame["timestamp"],
            utc=True,
        )

        frame["is_anomaly"] = frame["is_anomaly"].astype(bool)

        frame["score"] = pd.to_numeric(
            frame["score"],
            errors="coerce",
        )

        return frame[
            [
                "timestamp",
                "is_anomaly",
                "score",
            ]
        ]

    def get_metadata(
        self,
        *,
        anomaly_run_id: str,
    ) -> StoredAnomalyRun:
        """Load metadata for a stored anomaly run."""
        if not anomaly_run_id.strip():
            raise ValueError("anomaly_run_id must not be empty.")

        statement = select(anomaly_runs).where(
            anomaly_runs.c.anomaly_run_id == anomaly_run_id
        )

        with self._engine.connect() as connection:
            row = connection.execute(statement).mappings().one_or_none()

        if row is None:
            raise KeyError(f"Anomaly run not found: {anomaly_run_id}")

        generated_at = row["generated_at"]

        if generated_at.tzinfo is None:
            generated_at = generated_at.replace(tzinfo=UTC)

        return StoredAnomalyRun(
            anomaly_run_id=row["anomaly_run_id"],
            detector_name=row["detector_name"],
            target_column=row["target_column"],
            generated_at=generated_at,
            row_count=row["row_count"],
            anomaly_count=row["anomaly_count"],
        )

    def delete(
        self,
        *,
        anomaly_run_id: str,
    ) -> None:
        """Delete a stored anomaly run and its values."""
        if not anomaly_run_id.strip():
            raise ValueError("anomaly_run_id must not be empty.")

        with self._engine.begin() as connection:
            existing = connection.execute(
                select(anomaly_runs.c.anomaly_run_id).where(
                    anomaly_runs.c.anomaly_run_id == anomaly_run_id
                )
            ).scalar_one_or_none()

            if existing is None:
                raise KeyError(f"Anomaly run not found: {anomaly_run_id}")

            connection.execute(
                delete(anomaly_values).where(
                    anomaly_values.c.anomaly_run_id == anomaly_run_id
                )
            )

            connection.execute(
                delete(anomaly_runs).where(
                    anomaly_runs.c.anomaly_run_id == anomaly_run_id
                )
            )

    @staticmethod
    def _resolve_score_column(
        frame: pd.DataFrame,
    ) -> str | None:
        """Return the first supported anomaly score column."""
        supported_columns = (
            "anomaly_score",
            "z_score",
            "absolute_z_score",
            "residual",
            "absolute_residual",
        )

        for column in supported_columns:
            if column in frame.columns:
                return column

        return None
