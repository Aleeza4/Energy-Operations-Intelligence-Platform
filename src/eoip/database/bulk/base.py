"""Shared utilities for EOIP database bulk-loading operations."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence


def chunked[T](
    records: Iterable[T],
    batch_size: int,
) -> Iterator[list[T]]:
    """Yield records in batches of at most ``batch_size``.

    Parameters
    ----------
    records:
        Records that should be divided into batches.
    batch_size:
        Maximum number of records in each batch.

    Yields
    ------
    list[T]
        Consecutive batches of records.

    Raises
    ------
    ValueError
        If ``batch_size`` is less than one.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be greater than zero")

    batch: list[T] = []

    for record in records:
        batch.append(record)

        if len(batch) >= batch_size:
            yield batch
            batch = []

    if batch:
        yield batch


def normalize_records(
    records: Iterable[dict[str, object]],
) -> list[dict[str, object]]:
    """Return independent dictionaries suitable for bulk insertion."""
    return [dict(record) for record in records]


def validate_uniform_columns(
    records: Sequence[dict[str, object]],
) -> tuple[str, ...]:
    """Validate that all records contain the same column names.

    The column order is taken from the first record.

    Parameters
    ----------
    records:
        Records to validate.

    Returns
    -------
    tuple[str, ...]
        Ordered column names.

    Raises
    ------
    ValueError
        If the input is empty or records do not have identical columns.
    """
    if not records:
        raise ValueError("records must not be empty")

    columns = tuple(records[0])

    if not columns:
        raise ValueError("records must contain at least one column")

    expected = set(columns)

    for position, record in enumerate(records[1:], start=2):
        if set(record) != expected:
            raise ValueError(
                "All bulk records must contain identical columns; "
                f"record {position} does not match the first record"
            )

    return columns
