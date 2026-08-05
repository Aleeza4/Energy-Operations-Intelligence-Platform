"""
Unit tests for EOIP project directory initialization.

These tests verify the permanent directory collection, successful directory
creation, and clear error handling when a required path conflicts with a file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import eoip.core.directories as directories_module
from eoip.core.directories import (
    get_required_directories,
    initialize_project_directories,
)
from eoip.core.exceptions import DirectoryInitializationError


def test_get_required_directories_returns_expected_collection() -> None:
    """The permanent EOIP directory collection should contain 23 unique paths."""
    required_directories = get_required_directories()

    assert isinstance(required_directories, tuple)
    assert len(required_directories) == 23
    assert len(set(required_directories)) == 23
    assert all(isinstance(directory, Path) for directory in required_directories)


def test_initialize_project_directories_creates_all_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Directory initialization should create every configured directory."""
    temporary_directories = (
        tmp_path / "config",
        tmp_path / "data",
        tmp_path / "data" / "raw",
        tmp_path / "logs",
        tmp_path / "tests",
    )

    monkeypatch.setattr(
        directories_module,
        "_REQUIRED_DIRECTORIES",
        temporary_directories,
    )

    initialized_directories = initialize_project_directories()

    assert initialized_directories == temporary_directories
    assert all(
        directory.exists() and directory.is_dir()
        for directory in initialized_directories
    )


def test_initialize_project_directories_rejects_file_conflict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A file occupying a required directory path should raise a clear error."""
    conflicting_path = tmp_path / "data"
    conflicting_path.write_text(
        "This file intentionally conflicts with a required directory.",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        directories_module,
        "_REQUIRED_DIRECTORIES",
        (conflicting_path,),
    )

    with pytest.raises(
        DirectoryInitializationError,
        match="could not create the required directory",
    ):
        initialize_project_directories()
