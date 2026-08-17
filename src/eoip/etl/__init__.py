"""ETL and data-platform foundation for EOIP Phase 3.

The :mod:`eoip.etl` package provides the configuration and Prefect
orchestration foundation used by the Energy Operations Intelligence
Platform's ETL pipelines.

Only intentionally stable public interfaces are exported here. Internal
helpers remain owned by their respective modules.
"""

from eoip.etl.config import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_FLOW_RETRIES,
    DEFAULT_MAX_BAD_RECORDS,
    DEFAULT_RETRY_DELAY_SECONDS,
    DEFAULT_TASK_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    ETLConfig,
    ETLEnvironment,
    FailurePolicy,
    IngestionConfig,
    LoadMode,
    QualityConfig,
    RetryConfig,
    SourceFormat,
    StagingConfig,
    development_config,
    production_config,
    test_config,
)
from eoip.etl.prefect import (
    build_flow_options,
    build_task_options,
    eoip_flow,
    eoip_task,
    get_etl_logger,
)

__all__ = [
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_FLOW_RETRIES",
    "DEFAULT_MAX_BAD_RECORDS",
    "DEFAULT_RETRY_DELAY_SECONDS",
    "DEFAULT_TASK_RETRIES",
    "DEFAULT_TIMEOUT_SECONDS",
    "ETLConfig",
    "ETLEnvironment",
    "FailurePolicy",
    "IngestionConfig",
    "LoadMode",
    "QualityConfig",
    "RetryConfig",
    "SourceFormat",
    "StagingConfig",
    "build_flow_options",
    "build_task_options",
    "development_config",
    "eoip_flow",
    "eoip_task",
    "get_etl_logger",
    "production_config",
    "test_config",
]
