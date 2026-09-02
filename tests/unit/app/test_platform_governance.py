"""Focused Phase G platform-governance tests."""

from __future__ import annotations

import inspect

import pandas as pd
import pytest

from eoip.app.dashboards import administration, data_quality
from eoip.app.dashboards.administration import (
    SAFE_ADMIN_FIELDS,
    api_capabilities,
    contains_sensitive_configuration,
    database_metadata,
    safe_configuration,
    security_capabilities,
)
from eoip.app.dashboards.data_quality import (
    _governed_datasets,
    build_dataset_coverage,
    build_integrity_exceptions,
    build_quality_exceptions,
    calculate_completeness,
)
from eoip.config.settings import Settings


def test_completeness_derives_from_non_null_cells() -> None:
    """Completeness is a transparent cell-level calculation."""
    frame = pd.DataFrame({"a": [1, None], "b": [2, 3]})

    assert calculate_completeness(frame) == 75.0
    assert calculate_completeness(pd.DataFrame()) is None


def test_dataset_coverage_counts_records_missing_and_duplicates() -> None:
    """Coverage reports volume separately from measurable quality evidence."""
    source = pd.DataFrame({"value": [1.0, 1.0, None]})
    coverage = build_dataset_coverage({"Example": source})

    assert coverage.iloc[0]["Records"] == 3
    assert coverage.iloc[0]["Missing Cells"] == 1
    assert coverage.iloc[0]["Duplicate Records"] == 1
    assert coverage.iloc[0]["Completeness (%)"] == pytest.approx(66.6667)


def test_integrity_uses_exact_plant_equipment_identity() -> None:
    """Unknown composite identities are surfaced without causal inference."""
    datasets = _governed_datasets()
    integrity = build_integrity_exceptions(
        equipment=datasets["Equipment"],
        related_datasets={"Anomalies": datasets["Anomalies"]},
    )

    assert "TRF-002" in integrity["Equipment"].tolist()
    assert set(integrity["Issue"]) == {"Unknown plant/equipment relationship"}


def test_quality_exception_aggregation_and_partial_data() -> None:
    """Supported exception types aggregate without an overall quality score."""
    coverage = build_dataset_coverage(
        {"Partial": pd.DataFrame({"value": [1.0, None, None]})}
    )
    exceptions = build_quality_exceptions(coverage, pd.DataFrame())

    assert exceptions.iloc[0]["Issue"] == "Missing values"
    assert exceptions.iloc[0]["Affected Records"] == 2


def test_quality_derivations_do_not_mutate_sources() -> None:
    """Governance derivations preserve immutable source handling."""
    source = pd.DataFrame({"value": [1, 1]})
    original = source.copy(deep=True)

    build_dataset_coverage({"Example": source})

    pd.testing.assert_frame_equal(source, original)


def test_data_quality_does_not_fabricate_score_freshness_or_history() -> None:
    """Unsupported trust claims must remain absent from production code."""
    source = inspect.getsource(data_quality)

    assert "Overall Quality Score" not in source
    assert "Freshness (%)" not in source
    assert "Quality Trend" not in source
    assert "Pipeline Health" not in source
    assert "st.metric(" not in source
    assert "st.success(" not in source


def test_administration_uses_an_explicit_safe_allow_list() -> None:
    """Only reviewed configuration names may be presented."""
    assert SAFE_ADMIN_FIELDS
    assert not any(
        marker in field
        for field in SAFE_ADMIN_FIELDS
        for marker in ("password", "secret", "token", "url", "user")
    )


def test_safe_configuration_never_exposes_secret_values() -> None:
    """Passwords and token secrets must not enter rendered metadata."""
    password = "phase-g-database-password"
    token = "phase-g-token-secret-that-is-long-enough"
    configured = Settings(database_password=password, api_token_secret=token)
    safe = safe_configuration(configured)
    rendered = safe.to_string()

    assert password not in rendered
    assert token not in rendered
    assert not contains_sensitive_configuration(safe)


def test_platform_metadata_is_configuration_not_health() -> None:
    """Database and security metadata must use precise capability language."""
    database = database_metadata().to_string()
    security = security_capabilities().to_string()

    assert "Not verified" in database
    assert "OAuth2 bearer" in security
    assert "Healthy" not in database + security


def test_api_capabilities_derive_from_registered_routes() -> None:
    """API category counts should be introspected instead of hardcoded."""
    capabilities = api_capabilities()

    assert not capabilities.empty
    assert {"Health", "Authentication", "Administration"}.issubset(
        set(capabilities["Capability"])
    )


def test_administration_has_no_controls_or_runtime_health_claims() -> None:
    """Phase G Administration remains read-only and evidence-safe."""
    source = inspect.getsource(administration)

    assert "st.toggle(" not in source
    assert "st.selectbox(" not in source
    assert "st.success(" not in source
    assert "st.metric(" not in source
    assert "Healthy Services" not in source
    assert "Service Health" not in source
    assert "credential-bearing" not in source.casefold()
