"""Reusable CSV download helpers for EOIP dashboards."""

from __future__ import annotations

import re

import pandas as pd
import streamlit as st

from eoip.app.components.filters import FilterSelection

_FILENAME_TOKEN_PATTERN = re.compile(r"[^a-z0-9]+")


def dataframe_to_csv_bytes(dataframe: pd.DataFrame) -> bytes:
    """Serialize a DataFrame as deterministic UTF-8 CSV without its index."""
    return dataframe.to_csv(index=False, lineterminator="\n").encode("utf-8")


def filename_token(value: str) -> str:
    """Convert a display value into a safe lowercase filename token."""
    normalized = _FILENAME_TOKEN_PATTERN.sub("-", value.strip().lower()).strip("-")
    return normalized or "all"


def build_report_filename(
    report_name: str,
    *,
    filters: FilterSelection | None = None,
    extension: str = "csv",
) -> str:
    """Build a meaningful deterministic report filename."""
    parts = ["eoip", filename_token(report_name)]

    if filters is not None:
        parts.append(filename_token(filters.plant))
        if filters.equipment_id is not None:
            parts.append(filename_token(filters.equipment_id))
        parts.extend(
            [
                filters.start_date.isoformat(),
                filters.end_date.isoformat(),
            ]
        )

    suffix = filename_token(extension)
    return f"{'_'.join(parts)}.{suffix}"


def render_csv_download(
    dataframe: pd.DataFrame,
    *,
    label: str,
    report_name: str,
    filters: FilterSelection | None = None,
    key: str | None = None,
) -> None:
    """Render a safe CSV download button for a dashboard table."""
    st.download_button(
        label=label,
        data=dataframe_to_csv_bytes(dataframe),
        file_name=build_report_filename(report_name, filters=filters),
        mime="text/csv; charset=utf-8",
        disabled=dataframe.empty,
        key=key,
    )
