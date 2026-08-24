"""Unit tests for EOIP Phase 3 Prefect foundation utilities."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest
from prefect import flow, task
from prefect.logging import disable_run_logger

from eoip.etl.config import (
    ETLConfig,
    ETLEnvironment,
    RetryConfig,
)
from eoip.etl.prefect import (
    build_flow_options,
    build_task_options,
    eoip_flow,
    eoip_task,
    get_etl_logger,
)


@pytest.fixture
def etl_config() -> ETLConfig:
    """Return a deterministic ETL configuration for Prefect tests."""
    return ETLConfig(
        environment=ETLEnvironment.TEST,
        pipeline_name="test-etl-pipeline",
        retry=RetryConfig(
            flow_retries=3,
            task_retries=4,
            retry_delay_seconds=2.5,
            timeout_seconds=120.0,
        ),
    )


@pytest.fixture
def disabled_run_logger() -> Generator[None]:
    """Disable Prefect run logger requirements for direct-call tests."""
    with disable_run_logger():
        yield


class TestBuildFlowOptions:
    """Tests for Prefect flow option construction."""

    def test_builds_expected_options(
        self,
        etl_config: ETLConfig,
    ) -> None:
        """Flow options reflect the ETL retry configuration."""
        result = build_flow_options(etl_config)

        assert result == {
            "name": "test-etl-pipeline",
            "retries": 3,
            "retry_delay_seconds": 2.5,
            "timeout_seconds": 120.0,
            "validate_parameters": True,
        }

    def test_custom_name_overrides_pipeline_name(
        self,
        etl_config: ETLConfig,
    ) -> None:
        """Explicit flow names override the configured pipeline name."""
        result = build_flow_options(
            etl_config,
            name="custom-flow",
        )

        assert result["name"] == "custom-flow"

    def test_custom_name_is_trimmed(
        self,
        etl_config: ETLConfig,
    ) -> None:
        """Flow names are normalized before use."""
        result = build_flow_options(
            etl_config,
            name="  custom-flow  ",
        )

        assert result["name"] == "custom-flow"

    def test_none_name_uses_pipeline_name(
        self,
        etl_config: ETLConfig,
    ) -> None:
        """None uses the ETL pipeline name."""
        result = build_flow_options(
            etl_config,
            name=None,
        )

        assert result["name"] == etl_config.pipeline_name

    def test_empty_name_is_rejected(
        self,
        etl_config: ETLConfig,
    ) -> None:
        """Blank explicit flow names are invalid."""
        with pytest.raises(
            ValueError,
            match="flow name cannot be empty",
        ):
            build_flow_options(
                etl_config,
                name="   ",
            )

    def test_invalid_config_is_rejected(self) -> None:
        """Flow options require an ETLConfig instance."""
        with pytest.raises(
            TypeError,
            match="config must be an ETLConfig",
        ):
            build_flow_options("invalid")  # type: ignore[arg-type]


class TestBuildTaskOptions:
    """Tests for Prefect task option construction."""

    def test_builds_expected_options(
        self,
        etl_config: ETLConfig,
    ) -> None:
        """Task options reflect the ETL retry configuration."""
        result = build_task_options(
            etl_config,
            name="ingest-source",
        )

        assert result == {
            "name": "ingest-source",
            "retries": 4,
            "retry_delay_seconds": 2.5,
        }

    def test_task_name_is_trimmed(
        self,
        etl_config: ETLConfig,
    ) -> None:
        """Task names are normalized before use."""
        result = build_task_options(
            etl_config,
            name="  ingest-source  ",
        )

        assert result["name"] == "ingest-source"

    def test_empty_task_name_is_rejected(
        self,
        etl_config: ETLConfig,
    ) -> None:
        """Blank task names are invalid."""
        with pytest.raises(
            ValueError,
            match="task name cannot be empty",
        ):
            build_task_options(
                etl_config,
                name="   ",
            )

    def test_non_string_task_name_is_rejected(
        self,
        etl_config: ETLConfig,
    ) -> None:
        """Task names must be strings."""
        with pytest.raises(
            TypeError,
            match="task name must be a string",
        ):
            build_task_options(
                etl_config,
                name=123,  # type: ignore[arg-type]
            )

    def test_invalid_config_is_rejected(self) -> None:
        """Task options require an ETLConfig instance."""
        with pytest.raises(
            TypeError,
            match="config must be an ETLConfig",
        ):
            build_task_options(  # type: ignore[arg-type]
                "invalid",
                name="task",
            )


class TestEOIPFlow:
    """Tests for the EOIP Prefect flow decorator."""

    def test_returns_prefect_flow(
        self,
        etl_config: ETLConfig,
    ) -> None:
        """The decorator creates a Prefect Flow object."""

        @eoip_flow(
            etl_config,
            name="example-flow",
        )
        def example() -> int:
            return 42

        assert isinstance(example, type(flow(lambda: None)))
        assert example.name == "example-flow"

    def test_flow_configuration_is_applied(
        self,
        etl_config: ETLConfig,
    ) -> None:
        """Configured retry and timeout values reach Prefect."""

        @eoip_flow(etl_config)
        def example() -> None:
            return None

        assert example.name == "test-etl-pipeline"
        assert example.retries == 3
        assert example.retry_delay_seconds == 2.5
        assert example.timeout_seconds == 120.0

    def test_wrapped_function_preserves_name(
        self,
        etl_config: ETLConfig,
    ) -> None:
        """The original function metadata is retained."""

        @eoip_flow(
            etl_config,
            name="metadata-flow",
        )
        def example_function() -> None:
            """Example function."""
            return None

        assert example_function.fn.__name__ == "example_function"

    def test_flow_executes_function(
        self,
        etl_config: ETLConfig,
    ) -> None:
        """Decorated flows execute the wrapped callable."""

        @eoip_flow(
            etl_config,
            name="execution-flow",
        )
        def add(
            left: int,
            right: int,
        ) -> int:
            return left + right

        result = add(10, 5)

        assert result == 15


class TestEOIPTask:
    """Tests for the EOIP Prefect task decorator."""

    def test_returns_prefect_task(
        self,
        etl_config: ETLConfig,
    ) -> None:
        """The decorator creates a Prefect Task object."""

        @eoip_task(
            etl_config,
            name="example-task",
        )
        def example() -> int:
            return 42

        assert isinstance(example, type(task(lambda: None)))
        assert example.name == "example-task"

    def test_task_configuration_is_applied(
        self,
        etl_config: ETLConfig,
    ) -> None:
        """Configured retry values reach Prefect."""

        @eoip_task(
            etl_config,
            name="configured-task",
        )
        def example() -> None:
            return None

        assert example.name == "configured-task"
        assert example.retries == 4
        assert example.retry_delay_seconds == 2.5

    def test_wrapped_function_preserves_name(
        self,
        etl_config: ETLConfig,
    ) -> None:
        """The original task function metadata is retained."""

        @eoip_task(
            etl_config,
            name="metadata-task",
        )
        def example_function() -> None:
            """Example task."""
            return None

        assert example_function.fn.__name__ == "example_function"

    def test_task_function_can_be_called_directly(
        self,
        etl_config: ETLConfig,
        disabled_run_logger: None,
    ) -> None:
        """Underlying task logic remains directly testable."""

        @eoip_task(
            etl_config,
            name="addition-task",
        )
        def add(
            left: int,
            right: int,
        ) -> int:
            return left + right

        result = add.fn(7, 8)

        assert result == 15


class TestETLLogger:
    """Tests for the Prefect logger accessor."""

    def test_logger_is_available_when_run_logger_disabled(
        self,
        disabled_run_logger: None,
    ) -> None:
        """Logger accessor remains callable in test contexts."""
        logger = get_etl_logger()

        assert logger is not None
        assert hasattr(logger, "info")


class TestPrefectFoundationContract:
    """Higher-level contract tests for the Prefect foundation."""

    def test_flow_and_task_use_separate_retry_counts(
        self,
        etl_config: ETLConfig,
    ) -> None:
        """Flow and task retry policies remain independently configurable."""
        flow_options = build_flow_options(etl_config)
        task_options = build_task_options(
            etl_config,
            name="contract-task",
        )

        assert flow_options["retries"] == 3
        assert task_options["retries"] == 4

    def test_options_are_new_mappings_each_time(
        self,
        etl_config: ETLConfig,
    ) -> None:
        """Option builders do not expose shared mutable dictionaries."""
        first = build_flow_options(etl_config)
        second = build_flow_options(etl_config)

        assert first == second
        assert first is not second

    def test_options_can_be_inspected_without_prefect_execution(
        self,
        etl_config: ETLConfig,
    ) -> None:
        """Configuration can be validated without starting a Prefect run."""
        flow_options: dict[str, Any] = build_flow_options(etl_config)
        task_options: dict[str, Any] = build_task_options(
            etl_config,
            name="inspection-task",
        )

        assert flow_options["name"] == "test-etl-pipeline"
        assert task_options["name"] == "inspection-task"
