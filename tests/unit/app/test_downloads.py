"""Tests for EOIP report download helpers."""

from __future__ import annotations

from datetime import date

import pandas as pd

from eoip.app.components.downloads import (
    build_report_filename,
    dataframe_to_csv_bytes,
    filename_token,
)
from eoip.app.components.filters import FilterSelection


def test_csv_serialization_is_utf8_and_omits_index() -> None:
    dataframe = pd.DataFrame({"Plant": ["Solar Plant A"], "Energy": [12.5]})

    content = dataframe_to_csv_bytes(dataframe)

    assert content.decode("utf-8") == "Plant,Energy\nSolar Plant A,12.5\n"
    assert not content.startswith(b"\xef\xbb\xbf")


def test_empty_dataframe_serialization_preserves_headers() -> None:
    dataframe = pd.DataFrame(columns=["Plant", "Energy"])

    assert dataframe_to_csv_bytes(dataframe) == b"Plant,Energy\n"


def test_filename_token_is_safe() -> None:
    assert filename_token("Plant Performance / Summary") == "plant-performance-summary"


def test_report_filename_includes_filter_context() -> None:
    filters = FilterSelection(
        plant="Solar Plant B",
        start_date=date(2026, 8, 15),
        end_date=date(2026, 8, 21),
        equipment_id="INV-003",
    )

    filename = build_report_filename("Asset Health", filters=filters)

    assert filename == (
        "eoip_asset-health_solar-plant-b_inv-003_2026-08-15_2026-08-21.csv"
    )
