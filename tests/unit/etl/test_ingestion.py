"""Unit tests for EOIP Phase 3 source-data ingestion."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from eoip.etl.config import ETLConfig, IngestionConfig, QualityConfig, SourceFormat
from eoip.etl.ingestion import (
    IngestionBatch,
    SourceArtifact,
    SourceIngestor,
    SourceRun,
    discover_source_artifacts,
    discover_source_runs,
    ingest_source_run,
    iter_source_batches,
    load_source_run,
    read_source_artifact,
)


def _build_config(
    source_root: Path,
    *,
    source_format: SourceFormat = SourceFormat.PARQUET,
    batch_size: int = 2,
    recursive: bool = True,
    require_manifest: bool = True,
) -> ETLConfig:
    """Build a small deterministic ETL configuration."""
    return ETLConfig(
        ingestion=IngestionConfig(
            source_root=source_root,
            source_format=source_format,
            batch_size=batch_size,
            recursive=recursive,
        ),
        quality=QualityConfig(require_manifest=require_manifest),
    )


def _write_manifest(
    run_root: Path,
    *,
    run_id: str = "RUN-TEST-001",
) -> Path:
    """Write a minimal valid manifest."""
    manifest_path = run_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "generation_run_id": run_id,
                "manifest_version": "1.0.0",
            }
        ),
        encoding="utf-8",
    )
    return manifest_path


def _write_parquet(path: Path, frame: pd.DataFrame) -> None:
    """Write one test Parquet artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


class TestSourceArtifact:
    """Tests for SourceArtifact."""

    def test_valid_artifact(self) -> None:
        artifact = SourceArtifact(
            dataset_name="plants",
            path=Path("plants.parquet"),
            format=SourceFormat.PARQUET,
            size_bytes=100,
        )

        assert artifact.dataset_name == "plants"
        assert artifact.path == Path("plants.parquet")
        assert artifact.format is SourceFormat.PARQUET
        assert artifact.size_bytes == 100

    def test_dataset_name_is_trimmed(self) -> None:
        artifact = SourceArtifact(
            dataset_name="  plants  ",
            path=Path("plants.parquet"),
            format=SourceFormat.PARQUET,
            size_bytes=0,
        )
        assert artifact.dataset_name == "plants"

    def test_empty_dataset_name_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="dataset_name cannot be empty"):
            SourceArtifact(
                dataset_name="   ",
                path=Path("plants.parquet"),
                format=SourceFormat.PARQUET,
                size_bytes=0,
            )

    def test_invalid_format_is_rejected(self) -> None:
        with pytest.raises(TypeError, match="format must be a SourceFormat"):
            SourceArtifact(
                dataset_name="plants",
                path=Path("plants.parquet"),
                format="parquet",  # type: ignore[arg-type]
                size_bytes=0,
            )

    def test_negative_size_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="greater than or equal to zero"):
            SourceArtifact(
                dataset_name="plants",
                path=Path("plants.parquet"),
                format=SourceFormat.PARQUET,
                size_bytes=-1,
            )


class TestIngestionBatch:
    """Tests for IngestionBatch."""

    def test_row_count(self) -> None:
        batch = IngestionBatch(
            dataset_name="plants",
            source_path=Path("plants.parquet"),
            batch_number=0,
            row_offset=0,
            frame=pd.DataFrame({"plant_id": ["PLANT-001", "PLANT-002"]}),
        )
        assert batch.row_count == 2

    def test_negative_batch_number_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            IngestionBatch(
                dataset_name="plants",
                source_path=Path("plants.parquet"),
                batch_number=-1,
                row_offset=0,
                frame=pd.DataFrame(),
            )

    def test_invalid_frame_is_rejected(self) -> None:
        with pytest.raises(TypeError, match="pandas DataFrame"):
            IngestionBatch(
                dataset_name="plants",
                source_path=Path("plants.parquet"),
                batch_number=0,
                row_offset=0,
                frame=[],  # type: ignore[arg-type]
            )


class TestSourceRun:
    """Tests for SourceRun."""

    def test_valid_source_run(self) -> None:
        run = SourceRun(
            run_id="RUN-001",
            root=Path("runs/RUN-001"),
            manifest_path=Path("runs/RUN-001/manifest.json"),
            manifest={"generation_run_id": "RUN-001"},
        )

        assert run.run_id == "RUN-001"
        assert run.manifest["generation_run_id"] == "RUN-001"

    def test_run_id_is_trimmed(self) -> None:
        run = SourceRun(
            run_id="  RUN-001  ",
            root=Path("runs/RUN-001"),
            manifest_path=Path("runs/RUN-001/manifest.json"),
            manifest={},
        )
        assert run.run_id == "RUN-001"


class TestSourceRunDiscovery:
    """Tests for source-run discovery."""

    def test_missing_root_returns_empty_tuple(self, tmp_path: Path) -> None:
        config = _build_config(tmp_path / "missing")
        assert discover_source_runs(config) == ()

    def test_runs_are_sorted(self, tmp_path: Path) -> None:
        root = tmp_path / "runs"
        root.mkdir()

        (root / "RUN-003").mkdir()
        (root / "RUN-001").mkdir()
        (root / "RUN-002").mkdir()

        config = _build_config(root)
        runs = discover_source_runs(config)

        assert [path.name for path in runs] == [
            "RUN-001",
            "RUN-002",
            "RUN-003",
        ]

    def test_files_are_not_returned_as_runs(self, tmp_path: Path) -> None:
        root = tmp_path / "runs"
        root.mkdir()

        (root / "RUN-001").mkdir()
        (root / "not-a-run.txt").write_text("test", encoding="utf-8")

        config = _build_config(root)
        runs = discover_source_runs(config)

        assert len(runs) == 1
        assert runs[0].name == "RUN-001"


class TestLoadSourceRun:
    """Tests for source-run loading."""

    def test_loads_manifest(self, tmp_path: Path) -> None:
        root = tmp_path / "runs"
        run_root = root / "RUN-001"
        run_root.mkdir(parents=True)

        _write_manifest(run_root, run_id="RUN-001")
        config = _build_config(root)
        run = load_source_run(config, "RUN-001")

        assert run.run_id == "RUN-001"
        assert run.root == run_root
        assert run.manifest["generation_run_id"] == "RUN-001"

    def test_missing_run_is_rejected(self, tmp_path: Path) -> None:
        config = _build_config(tmp_path / "runs")
        with pytest.raises(FileNotFoundError):
            load_source_run(config, "RUN-MISSING")

    def test_missing_required_manifest_is_rejected(self, tmp_path: Path) -> None:
        root = tmp_path / "runs"
        run_root = root / "RUN-001"
        run_root.mkdir(parents=True)

        config = _build_config(root, require_manifest=True)
        with pytest.raises(FileNotFoundError, match="Required manifest"):
            load_source_run(config, "RUN-001")

    def test_manifest_can_be_optional(self, tmp_path: Path) -> None:
        root = tmp_path / "runs"
        run_root = root / "RUN-001"
        run_root.mkdir(parents=True)

        config = _build_config(root, require_manifest=False)
        run = load_source_run(config, "RUN-001")

        assert run.manifest == {}

    @pytest.mark.parametrize(
        "run_id",
        [
            "",
            "   ",
            ".",
            "..",
            "../RUN-001",
            "folder/RUN-001",
            r"folder\RUN-001",
        ],
    )
    def test_unsafe_run_id_is_rejected(
        self,
        tmp_path: Path,
        run_id: str,
    ) -> None:
        root = tmp_path / "runs"
        root.mkdir()
        config = _build_config(root)

        with pytest.raises(ValueError):
            load_source_run(config, run_id)

    def test_invalid_manifest_json_is_rejected(self, tmp_path: Path) -> None:
        root = tmp_path / "runs"
        run_root = root / "RUN-001"
        run_root.mkdir(parents=True)

        (run_root / "manifest.json").write_text("{invalid", encoding="utf-8")
        config = _build_config(root)

        with pytest.raises(ValueError, match="invalid JSON"):
            load_source_run(config, "RUN-001")


class TestArtifactDiscovery:
    """Tests for dataset artifact discovery."""

    def test_discovers_parquet_artifacts(self, tmp_path: Path) -> None:
        root = tmp_path / "runs"
        run_root = root / "RUN-001"
        run_root.mkdir(parents=True)

        _write_manifest(run_root)
        _write_parquet(
            run_root / "master" / "plants" / "part-00000.parquet",
            pd.DataFrame({"plant_id": ["PLANT-001"]}),
        )

        config = _build_config(root)
        run = load_source_run(config, "RUN-001")
        artifacts = discover_source_artifacts(config, run)

        assert len(artifacts) == 1
        assert artifacts[0].dataset_name == "plants"
        assert artifacts[0].format is SourceFormat.PARQUET

    def test_manifest_is_not_dataset_artifact(self, tmp_path: Path) -> None:
        root = tmp_path / "runs"
        run_root = root / "RUN-001"
        run_root.mkdir(parents=True)

        _write_manifest(run_root)
        config = _build_config(root)
        run = load_source_run(config, "RUN-001")

        assert discover_source_artifacts(config, run) == ()

    def test_artifacts_are_sorted_by_path(self, tmp_path: Path) -> None:
        root = tmp_path / "runs"
        run_root = root / "RUN-001"
        run_root.mkdir(parents=True)

        _write_manifest(run_root)

        for name in ("weather", "plants", "equipment"):
            _write_parquet(
                run_root / "master" / name / "part-00000.parquet",
                pd.DataFrame({"value": [1]}),
            )

        config = _build_config(root)
        run = load_source_run(config, "RUN-001")
        artifacts = discover_source_artifacts(config, run)

        assert [artifact.dataset_name for artifact in artifacts] == [
            "equipment",
            "plants",
            "weather",
        ]

    def test_non_matching_formats_are_ignored(self, tmp_path: Path) -> None:
        root = tmp_path / "runs"
        run_root = root / "RUN-001"
        run_root.mkdir(parents=True)

        _write_manifest(run_root)
        csv_path = run_root / "master" / "plants" / "part-00000.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        csv_path.write_text("plant_id\nPLANT-001\n", encoding="utf-8")

        config = _build_config(root, source_format=SourceFormat.PARQUET)
        run = load_source_run(config, "RUN-001")

        assert discover_source_artifacts(config, run) == ()


class TestArtifactReading:
    """Tests for individual artifact reading."""

    def test_reads_parquet(self, tmp_path: Path) -> None:
        root = tmp_path / "runs"
        run_root = root / "RUN-001"
        run_root.mkdir(parents=True)

        _write_manifest(run_root)

        expected = pd.DataFrame(
            {
                "plant_id": ["PLANT-001", "PLANT-002"],
                "capacity_mw": [50.0, 75.0],
            }
        )
        parquet_path = run_root / "master" / "plants" / "part-00000.parquet"
        _write_parquet(parquet_path, expected)

        config = _build_config(root)
        artifact = SourceArtifact(
            dataset_name="plants",
            path=parquet_path,
            format=SourceFormat.PARQUET,
            size_bytes=parquet_path.stat().st_size,
        )

        actual = read_source_artifact(config, artifact)
        pd.testing.assert_frame_equal(actual, expected)

    def test_reads_csv(self, tmp_path: Path) -> None:
        root = tmp_path / "runs"
        run_root = root / "RUN-001"
        run_root.mkdir(parents=True)

        _write_manifest(run_root)

        csv_path = run_root / "master" / "plants.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        expected = pd.DataFrame({"plant_id": ["PLANT-001"]})
        expected.to_csv(csv_path, index=False)

        config = _build_config(root, source_format=SourceFormat.CSV)
        artifact = SourceArtifact(
            dataset_name="plants",
            path=csv_path,
            format=SourceFormat.CSV,
            size_bytes=csv_path.stat().st_size,
        )

        actual = read_source_artifact(config, artifact)
        pd.testing.assert_frame_equal(actual, expected)

    def test_missing_artifact_is_rejected(self, tmp_path: Path) -> None:
        root = tmp_path / "runs"
        root.mkdir()
        config = _build_config(root)

        artifact = SourceArtifact(
            dataset_name="plants",
            path=root / "missing.parquet",
            format=SourceFormat.PARQUET,
            size_bytes=0,
        )

        with pytest.raises(FileNotFoundError):
            read_source_artifact(config, artifact)

    def test_artifact_outside_source_root_is_rejected(
        self,
        tmp_path: Path,
    ) -> None:
        root = tmp_path / "runs"
        root.mkdir()

        outside = tmp_path / "outside.parquet"
        _write_parquet(outside, pd.DataFrame({"value": [1]}))

        config = _build_config(root)
        artifact = SourceArtifact(
            dataset_name="outside",
            path=outside,
            format=SourceFormat.PARQUET,
            size_bytes=outside.stat().st_size,
        )

        with pytest.raises(
            ValueError,
            match="outside configured source root",
        ):
            read_source_artifact(config, artifact)


class TestBatching:
    """Tests for deterministic ingestion batching."""

    def test_batches_respect_batch_size(self, tmp_path: Path) -> None:
        root = tmp_path / "runs"
        run_root = root / "RUN-001"
        run_root.mkdir(parents=True)

        _write_manifest(run_root)
        parquet_path = run_root / "master" / "plants.parquet"
        _write_parquet(
            parquet_path,
            pd.DataFrame({"value": [1, 2, 3, 4, 5]}),
        )

        config = _build_config(root, batch_size=2)
        artifact = SourceArtifact(
            dataset_name="plants",
            path=parquet_path,
            format=SourceFormat.PARQUET,
            size_bytes=parquet_path.stat().st_size,
        )

        batches = tuple(iter_source_batches(config, artifact))

        assert [batch.row_count for batch in batches] == [2, 2, 1]
        assert [batch.batch_number for batch in batches] == [0, 1, 2]
        assert [batch.row_offset for batch in batches] == [0, 2, 4]

    def test_empty_dataset_yields_one_empty_batch(
        self,
        tmp_path: Path,
    ) -> None:
        root = tmp_path / "runs"
        run_root = root / "RUN-001"
        run_root.mkdir(parents=True)

        _write_manifest(run_root)
        parquet_path = run_root / "master" / "empty.parquet"
        _write_parquet(
            parquet_path,
            pd.DataFrame({"value": pd.Series(dtype="int64")}),
        )

        config = _build_config(root)
        artifact = SourceArtifact(
            dataset_name="empty",
            path=parquet_path,
            format=SourceFormat.PARQUET,
            size_bytes=parquet_path.stat().st_size,
        )

        batches = tuple(iter_source_batches(config, artifact))

        assert len(batches) == 1
        assert batches[0].row_count == 0
        assert batches[0].batch_number == 0
        assert batches[0].row_offset == 0


class TestRunIngestion:
    """Tests for complete source-run ingestion."""

    def test_ingests_multiple_datasets(self, tmp_path: Path) -> None:
        root = tmp_path / "runs"
        run_root = root / "RUN-001"
        run_root.mkdir(parents=True)

        _write_manifest(run_root)

        _write_parquet(
            run_root / "master" / "plants" / "part-00000.parquet",
            pd.DataFrame({"plant_id": ["PLANT-001"]}),
        )
        _write_parquet(
            run_root / "operations" / "alarms" / "part-00000.parquet",
            pd.DataFrame({"alarm_id": ["ALARM-001"]}),
        )

        config = _build_config(root)
        datasets = ingest_source_run(config, "RUN-001")

        assert sorted(datasets) == ["alarms", "plants"]
        assert datasets["plants"].iloc[0]["plant_id"] == "PLANT-001"
        assert datasets["alarms"].iloc[0]["alarm_id"] == "ALARM-001"

    def test_multiple_parts_are_combined(self, tmp_path: Path) -> None:
        root = tmp_path / "runs"
        run_root = root / "RUN-001"
        run_root.mkdir(parents=True)

        _write_manifest(run_root)
        dataset_root = run_root / "master" / "plants"

        _write_parquet(
            dataset_root / "part-00000.parquet",
            pd.DataFrame({"plant_id": ["PLANT-001"]}),
        )
        _write_parquet(
            dataset_root / "part-00001.parquet",
            pd.DataFrame({"plant_id": ["PLANT-002"]}),
        )

        config = _build_config(root)
        datasets = ingest_source_run(config, "RUN-001")

        assert len(datasets["plants"]) == 2
        assert datasets["plants"]["plant_id"].tolist() == [
            "PLANT-001",
            "PLANT-002",
        ]

    def test_ingestor_exposes_config(self, tmp_path: Path) -> None:
        config = _build_config(tmp_path / "runs")
        ingestor = SourceIngestor(config)
        assert ingestor.config is config
