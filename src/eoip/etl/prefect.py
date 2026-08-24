"""Prefect foundation utilities for EOIP Phase 3 ETL workflows.

This module centralizes Prefect flow/task configuration so downstream ETL
modules do not duplicate retry, timeout, naming, or logging behavior.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from prefect import flow, get_run_logger, task

from eoip.etl.config import ETLConfig

P = ParamSpec("P")
R = TypeVar("R")


def build_flow_options(
    config: ETLConfig,
    *,
    name: str | None = None,
) -> dict[str, Any]:
    """Build Prefect flow decorator options from an ETL configuration."""
    if not isinstance(config, ETLConfig):
        raise TypeError("config must be an ETLConfig.")

    resolved_name = _resolve_name(
        name=name,
        fallback=config.pipeline_name,
        field_name="flow name",
    )

    return {
        "name": resolved_name,
        "retries": config.retry.flow_retries,
        "retry_delay_seconds": config.retry.retry_delay_seconds,
        "timeout_seconds": config.retry.timeout_seconds,
        "validate_parameters": True,
    }


def build_task_options(
    config: ETLConfig,
    *,
    name: str,
) -> dict[str, Any]:
    """Build Prefect task decorator options from an ETL configuration."""
    if not isinstance(config, ETLConfig):
        raise TypeError("config must be an ETLConfig.")

    resolved_name = _resolve_name(
        name=name,
        fallback="eoip-etl-task",
        field_name="task name",
    )

    return {
        "name": resolved_name,
        "retries": config.retry.task_retries,
        "retry_delay_seconds": config.retry.retry_delay_seconds,
    }


def eoip_flow(
    config: ETLConfig,
    *,
    name: str | None = None,
) -> Callable[[Callable[P, R]], Any]:
    """Decorate a callable as an EOIP-configured Prefect flow."""
    options = build_flow_options(
        config,
        name=name,
    )

    def decorator(function: Callable[P, R]) -> Any:
        @wraps(function)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            logger = get_run_logger()
            logger.info(
                "Starting EOIP ETL flow '%s' in environment '%s'.",
                options["name"],
                config.environment.value,
            )

            result = function(*args, **kwargs)

            logger.info(
                "Completed EOIP ETL flow '%s'.",
                options["name"],
            )
            return result

        return flow(**options)(wrapped)

    return decorator


def eoip_task(
    config: ETLConfig,
    *,
    name: str,
) -> Callable[[Callable[P, R]], Any]:
    """Decorate a callable as an EOIP-configured Prefect task."""
    options = build_task_options(
        config,
        name=name,
    )

    def decorator(function: Callable[P, R]) -> Any:
        @wraps(function)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            logger = get_run_logger()
            logger.info(
                "Starting EOIP ETL task '%s'.",
                options["name"],
            )

            result = function(*args, **kwargs)

            logger.info(
                "Completed EOIP ETL task '%s'.",
                options["name"],
            )
            return result

        return task(**options)(wrapped)

    return decorator


def get_etl_logger() -> Any:
    """Return the Prefect logger for the active flow or task run."""
    return get_run_logger()


def _resolve_name(
    *,
    name: str | None,
    fallback: str,
    field_name: str,
) -> str:
    """Normalize and validate a Prefect flow or task name."""
    resolved_name = fallback if name is None else name

    if not isinstance(resolved_name, str):
        raise TypeError(f"{field_name} must be a string.")

    normalized_name = resolved_name.strip()

    if not normalized_name:
        raise ValueError(f"{field_name} cannot be empty.")

    return normalized_name


__all__ = [
    "build_flow_options",
    "build_task_options",
    "eoip_flow",
    "eoip_task",
    "get_etl_logger",
]
