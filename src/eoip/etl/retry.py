"""Error handling and retry utilities for EOIP Phase 3 ETL pipelines.

This module provides deterministic retry decisions, retry-attempt metadata,
exponential backoff calculation, failure metadata, and safe execution wrappers.

The retry layer is intentionally independent of Prefect so the same policy can
be reused by Prefect tasks, integration tests, CLI workflows, and local runs.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final

from eoip.etl.config import RetryConfig

DEFAULT_BACKOFF_MULTIPLIER: Final[float] = 2.0
DEFAULT_MAX_RETRY_DELAY_SECONDS: Final[float] = 300.0

DEFAULT_RETRYABLE_EXCEPTIONS: Final[tuple[type[BaseException], ...]] = (
    ConnectionError,
    TimeoutError,
)

DEFAULT_NON_RETRYABLE_EXCEPTIONS: Final[tuple[type[BaseException], ...]] = (
    KeyboardInterrupt,
    SystemExit,
)


class RetryDecision(StrEnum):
    """Outcome of a retry-policy decision."""

    SUCCESS = "success"
    RETRY = "retry"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Runtime retry policy derived from ETL RetryConfig."""

    maximum_retries: int
    retry_delay_seconds: float
    timeout_seconds: float
    backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER
    maximum_retry_delay_seconds: float = DEFAULT_MAX_RETRY_DELAY_SECONDS
    retryable_exceptions: tuple[type[BaseException], ...] = DEFAULT_RETRYABLE_EXCEPTIONS
    non_retryable_exceptions: tuple[type[BaseException], ...] = (
        DEFAULT_NON_RETRYABLE_EXCEPTIONS
    )

    def __post_init__(self) -> None:
        """Validate retry-policy configuration."""
        _validate_non_negative_int(
            "maximum_retries",
            self.maximum_retries,
        )
        _validate_positive_number(
            "retry_delay_seconds",
            self.retry_delay_seconds,
        )
        _validate_positive_number(
            "timeout_seconds",
            self.timeout_seconds,
        )
        _validate_positive_number(
            "backoff_multiplier",
            self.backoff_multiplier,
        )
        _validate_positive_number(
            "maximum_retry_delay_seconds",
            self.maximum_retry_delay_seconds,
        )

        _validate_exception_tuple(
            "retryable_exceptions",
            self.retryable_exceptions,
        )
        _validate_exception_tuple(
            "non_retryable_exceptions",
            self.non_retryable_exceptions,
        )

        overlap = set(self.retryable_exceptions) & set(self.non_retryable_exceptions)

        if overlap:
            names = sorted(exception_type.__name__ for exception_type in overlap)
            raise ValueError(
                "retryable_exceptions and non_retryable_exceptions "
                f"cannot overlap: {names}"
            )

    @classmethod
    def for_task(
        cls,
        config: RetryConfig,
        *,
        retryable_exceptions: tuple[type[BaseException], ...] = (
            DEFAULT_RETRYABLE_EXCEPTIONS
        ),
        non_retryable_exceptions: tuple[type[BaseException], ...] = (
            DEFAULT_NON_RETRYABLE_EXCEPTIONS
        ),
        backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER,
        maximum_retry_delay_seconds: float = (DEFAULT_MAX_RETRY_DELAY_SECONDS),
    ) -> RetryPolicy:
        """Create a task-level retry policy from RetryConfig."""
        _validate_retry_config(config)

        return cls(
            maximum_retries=config.task_retries,
            retry_delay_seconds=float(config.retry_delay_seconds),
            timeout_seconds=float(config.timeout_seconds),
            backoff_multiplier=backoff_multiplier,
            maximum_retry_delay_seconds=maximum_retry_delay_seconds,
            retryable_exceptions=retryable_exceptions,
            non_retryable_exceptions=non_retryable_exceptions,
        )

    @classmethod
    def for_flow(
        cls,
        config: RetryConfig,
        *,
        retryable_exceptions: tuple[type[BaseException], ...] = (
            DEFAULT_RETRYABLE_EXCEPTIONS
        ),
        non_retryable_exceptions: tuple[type[BaseException], ...] = (
            DEFAULT_NON_RETRYABLE_EXCEPTIONS
        ),
        backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER,
        maximum_retry_delay_seconds: float = (DEFAULT_MAX_RETRY_DELAY_SECONDS),
    ) -> RetryPolicy:
        """Create a flow-level retry policy from RetryConfig."""
        _validate_retry_config(config)

        return cls(
            maximum_retries=config.flow_retries,
            retry_delay_seconds=float(config.retry_delay_seconds),
            timeout_seconds=float(config.timeout_seconds),
            backoff_multiplier=backoff_multiplier,
            maximum_retry_delay_seconds=maximum_retry_delay_seconds,
            retryable_exceptions=retryable_exceptions,
            non_retryable_exceptions=non_retryable_exceptions,
        )

    @property
    def maximum_attempts(self) -> int:
        """Return total attempts including the initial execution."""
        return self.maximum_retries + 1

    def delay_for_retry(
        self,
        retry_number: int,
    ) -> float:
        """Return exponential-backoff delay for one retry number."""
        _validate_positive_int(
            "retry_number",
            retry_number,
        )

        delay = self.retry_delay_seconds * (
            self.backoff_multiplier ** (retry_number - 1)
        )

        return min(
            delay,
            self.maximum_retry_delay_seconds,
        )

    def is_retryable(
        self,
        error: BaseException,
    ) -> bool:
        """Return whether an exception is eligible for retry."""
        if not isinstance(
            error,
            BaseException,
        ):
            raise TypeError("error must be an exception.")

        if isinstance(
            error,
            self.non_retryable_exceptions,
        ):
            return False

        return isinstance(
            error,
            self.retryable_exceptions,
        )


@dataclass(frozen=True, slots=True)
class RetryAttempt:
    """Metadata describing one execution attempt."""

    attempt_number: int
    started_monotonic: float
    completed_monotonic: float
    decision: RetryDecision
    delay_before_next_attempt: float | None = None
    error_type: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Validate retry-attempt metadata."""
        _validate_positive_int(
            "attempt_number",
            self.attempt_number,
        )
        _validate_non_negative_number(
            "started_monotonic",
            self.started_monotonic,
        )
        _validate_non_negative_number(
            "completed_monotonic",
            self.completed_monotonic,
        )

        if self.completed_monotonic < self.started_monotonic:
            raise ValueError(
                "completed_monotonic cannot be earlier " "than started_monotonic."
            )

        if not isinstance(
            self.decision,
            RetryDecision,
        ):
            raise TypeError("decision must be a RetryDecision.")

        if self.delay_before_next_attempt is not None:
            _validate_non_negative_number(
                "delay_before_next_attempt",
                self.delay_before_next_attempt,
            )

        if self.decision is RetryDecision.SUCCESS:
            if self.error_type is not None:
                raise ValueError("Successful attempts cannot contain error_type.")

            if self.error_message is not None:
                raise ValueError("Successful attempts cannot contain error_message.")

            if self.delay_before_next_attempt is not None:
                raise ValueError("Successful attempts cannot contain retry delay.")

        if self.decision in (
            RetryDecision.RETRY,
            RetryDecision.FAIL,
        ):
            if self.error_type is None:
                raise ValueError("Failed attempts require error_type.")

            if self.error_message is None:
                raise ValueError("Failed attempts require error_message.")

        if (
            self.decision is RetryDecision.FAIL
            and self.delay_before_next_attempt is not None
        ):
            raise ValueError("Final failed attempts cannot contain retry delay.")

    @property
    def duration_seconds(self) -> float:
        """Return elapsed attempt duration."""
        return self.completed_monotonic - self.started_monotonic


@dataclass(frozen=True, slots=True)
class RetryExecutionResult:
    """Result of successful execution under a retry policy."""

    value: Any
    attempts: tuple[RetryAttempt, ...]

    def __post_init__(self) -> None:
        """Validate successful execution result."""
        if not isinstance(
            self.attempts,
            tuple,
        ):
            raise TypeError("attempts must be a tuple.")

        if not self.attempts:
            raise ValueError("attempts cannot be empty.")

        for attempt in self.attempts:
            if not isinstance(
                attempt,
                RetryAttempt,
            ):
                raise TypeError("attempts must contain RetryAttempt objects.")

        if self.attempts[-1].decision is not RetryDecision.SUCCESS:
            raise ValueError(
                "Successful execution result must end " "with a SUCCESS attempt."
            )

    @property
    def attempt_count(self) -> int:
        """Return total number of attempts made."""
        return len(self.attempts)

    @property
    def retry_count(self) -> int:
        """Return number of retries performed."""
        return max(
            0,
            self.attempt_count - 1,
        )


class RetryExhaustedError(RuntimeError):
    """Raised when execution fails without another retry."""

    def __init__(
        self,
        message: str,
        *,
        attempts: tuple[RetryAttempt, ...],
        last_error: BaseException,
    ) -> None:
        """Create a retry-exhaustion error."""
        if not isinstance(
            message,
            str,
        ):
            raise TypeError("message must be a string.")

        if not message.strip():
            raise ValueError("message cannot be empty.")

        if not isinstance(
            attempts,
            tuple,
        ):
            raise TypeError("attempts must be a tuple.")

        if not attempts:
            raise ValueError("attempts cannot be empty.")

        for attempt in attempts:
            if not isinstance(
                attempt,
                RetryAttempt,
            ):
                raise TypeError("attempts must contain RetryAttempt objects.")

        if not isinstance(
            last_error,
            BaseException,
        ):
            raise TypeError("last_error must be an exception.")

        super().__init__(message)

        self.attempts = attempts
        self.last_error = last_error

    @property
    def attempt_count(self) -> int:
        """Return number of attempts that were made."""
        return len(self.attempts)


def execute_with_retry[T](
    function: Callable[..., T],
    policy: RetryPolicy,
    *args: Any,
    sleep_function: Callable[[float], None] = time.sleep,
    monotonic_function: Callable[[], float] = time.monotonic,
    **kwargs: Any,
) -> RetryExecutionResult:
    """Execute a callable according to a deterministic retry policy.

    The callable is executed synchronously. If a completed execution exceeds
    ``policy.timeout_seconds``, the attempt is treated as a TimeoutError.

    This helper does not forcibly terminate a running callable. Hard task
    cancellation remains the responsibility of the orchestration layer.
    """
    if not callable(function):
        raise TypeError("function must be callable.")

    if not isinstance(
        policy,
        RetryPolicy,
    ):
        raise TypeError("policy must be a RetryPolicy.")

    if not callable(sleep_function):
        raise TypeError("sleep_function must be callable.")

    if not callable(monotonic_function):
        raise TypeError("monotonic_function must be callable.")

    attempts: list[RetryAttempt] = []

    for attempt_number in range(
        1,
        policy.maximum_attempts + 1,
    ):
        started = float(monotonic_function())

        try:
            value = function(
                *args,
                **kwargs,
            )

        except BaseException as error:
            completed = float(monotonic_function())

            _validate_monotonic_pair(
                started,
                completed,
            )

            if should_retry(
                policy,
                error,
                attempt_number=attempt_number,
            ):
                delay = policy.delay_for_retry(attempt_number)

                attempts.append(
                    _failed_attempt(
                        attempt_number=attempt_number,
                        started=started,
                        completed=completed,
                        error=error,
                        decision=RetryDecision.RETRY,
                        delay=delay,
                    )
                )

                sleep_function(delay)
                continue

            attempts.append(
                _failed_attempt(
                    attempt_number=attempt_number,
                    started=started,
                    completed=completed,
                    error=error,
                    decision=RetryDecision.FAIL,
                )
            )

            raise RetryExhaustedError(
                "Execution failed after " f"{attempt_number} attempt(s).",
                attempts=tuple(attempts),
                last_error=error,
            ) from error

        completed = float(monotonic_function())

        _validate_monotonic_pair(
            started,
            completed,
        )

        elapsed = completed - started

        if elapsed > policy.timeout_seconds:
            timeout_error = TimeoutError(
                "Execution exceeded timeout of " f"{policy.timeout_seconds} seconds."
            )

            if should_retry(
                policy,
                timeout_error,
                attempt_number=attempt_number,
            ):
                delay = policy.delay_for_retry(attempt_number)

                attempts.append(
                    _failed_attempt(
                        attempt_number=attempt_number,
                        started=started,
                        completed=completed,
                        error=timeout_error,
                        decision=RetryDecision.RETRY,
                        delay=delay,
                    )
                )

                sleep_function(delay)
                continue

            attempts.append(
                _failed_attempt(
                    attempt_number=attempt_number,
                    started=started,
                    completed=completed,
                    error=timeout_error,
                    decision=RetryDecision.FAIL,
                )
            )

            raise RetryExhaustedError(
                "Execution failed after " f"{attempt_number} attempt(s).",
                attempts=tuple(attempts),
                last_error=timeout_error,
            ) from timeout_error

        attempts.append(
            RetryAttempt(
                attempt_number=attempt_number,
                started_monotonic=started,
                completed_monotonic=completed,
                decision=RetryDecision.SUCCESS,
            )
        )

        return RetryExecutionResult(
            value=value,
            attempts=tuple(attempts),
        )

    raise RuntimeError("Retry execution reached an unreachable state.")


def should_retry(
    policy: RetryPolicy,
    error: BaseException,
    *,
    attempt_number: int,
) -> bool:
    """Return whether another execution attempt should occur."""
    if not isinstance(
        policy,
        RetryPolicy,
    ):
        raise TypeError("policy must be a RetryPolicy.")

    if not isinstance(
        error,
        BaseException,
    ):
        raise TypeError("error must be an exception.")

    _validate_positive_int(
        "attempt_number",
        attempt_number,
    )

    if attempt_number >= policy.maximum_attempts:
        return False

    return policy.is_retryable(error)


def retry_delays(
    policy: RetryPolicy,
) -> tuple[float, ...]:
    """Return every configured retry delay."""
    if not isinstance(
        policy,
        RetryPolicy,
    ):
        raise TypeError("policy must be a RetryPolicy.")

    return tuple(
        policy.delay_for_retry(retry_number)
        for retry_number in range(
            1,
            policy.maximum_retries + 1,
        )
    )


def extend_retryable_exceptions(
    policy: RetryPolicy,
    exceptions: Iterable[type[BaseException]],
) -> RetryPolicy:
    """Return a policy containing additional retryable exceptions."""
    if not isinstance(
        policy,
        RetryPolicy,
    ):
        raise TypeError("policy must be a RetryPolicy.")

    try:
        additions = tuple(exceptions)
    except TypeError as exc:
        raise TypeError("exceptions must be iterable.") from exc

    _validate_exception_tuple(
        "exceptions",
        additions,
    )

    combined = list(policy.retryable_exceptions)

    for exception_type in additions:
        if exception_type not in combined:
            combined.append(exception_type)

    return RetryPolicy(
        maximum_retries=policy.maximum_retries,
        retry_delay_seconds=policy.retry_delay_seconds,
        timeout_seconds=policy.timeout_seconds,
        backoff_multiplier=policy.backoff_multiplier,
        maximum_retry_delay_seconds=(policy.maximum_retry_delay_seconds),
        retryable_exceptions=tuple(combined),
        non_retryable_exceptions=(policy.non_retryable_exceptions),
    )


def _failed_attempt(
    *,
    attempt_number: int,
    started: float,
    completed: float,
    error: BaseException,
    decision: RetryDecision,
    delay: float | None = None,
) -> RetryAttempt:
    """Build deterministic metadata for a failed attempt."""
    return RetryAttempt(
        attempt_number=attempt_number,
        started_monotonic=started,
        completed_monotonic=completed,
        decision=decision,
        delay_before_next_attempt=delay,
        error_type=type(error).__name__,
        error_message=str(error),
    )


def _validate_retry_config(
    config: RetryConfig,
) -> None:
    """Validate RetryConfig type."""
    if not isinstance(
        config,
        RetryConfig,
    ):
        raise TypeError("config must be a RetryConfig.")


def _validate_exception_tuple(
    name: str,
    value: tuple[type[BaseException], ...],
) -> None:
    """Validate a tuple containing exception classes."""
    if not isinstance(
        value,
        tuple,
    ):
        raise TypeError(f"{name} must be a tuple.")

    for exception_type in value:
        if not isinstance(
            exception_type,
            type,
        ):
            raise TypeError(f"{name} must contain exception classes.")

        if not issubclass(
            exception_type,
            BaseException,
        ):
            raise TypeError(f"{name} must contain exception classes.")


def _validate_positive_int(
    name: str,
    value: int,
) -> None:
    """Validate a strictly positive integer."""
    if isinstance(
        value,
        bool,
    ) or not isinstance(
        value,
        int,
    ):
        raise TypeError(f"{name} must be an integer.")

    if value <= 0:
        raise ValueError(f"{name} must be greater than zero.")


def _validate_non_negative_int(
    name: str,
    value: int,
) -> None:
    """Validate a non-negative integer."""
    if isinstance(
        value,
        bool,
    ) or not isinstance(
        value,
        int,
    ):
        raise TypeError(f"{name} must be an integer.")

    if value < 0:
        raise ValueError(f"{name} must be greater than or equal to zero.")


def _validate_positive_number(
    name: str,
    value: float,
) -> None:
    """Validate a strictly positive finite number."""
    if isinstance(
        value,
        bool,
    ) or not isinstance(
        value,
        (int, float),
    ):
        raise TypeError(f"{name} must be numeric.")

    numeric = float(value)

    if not math.isfinite(numeric):
        raise ValueError(f"{name} must be finite.")

    if numeric <= 0.0:
        raise ValueError(f"{name} must be greater than zero.")


def _validate_non_negative_number(
    name: str,
    value: float,
) -> None:
    """Validate a non-negative finite number."""
    if isinstance(
        value,
        bool,
    ) or not isinstance(
        value,
        (int, float),
    ):
        raise TypeError(f"{name} must be numeric.")

    numeric = float(value)

    if not math.isfinite(numeric):
        raise ValueError(f"{name} must be finite.")

    if numeric < 0.0:
        raise ValueError(f"{name} must be greater than or equal to zero.")


def _validate_monotonic_pair(
    started: float,
    completed: float,
) -> None:
    """Validate timestamps returned by the monotonic clock."""
    _validate_non_negative_number(
        "started_monotonic",
        started,
    )
    _validate_non_negative_number(
        "completed_monotonic",
        completed,
    )

    if completed < started:
        raise ValueError("monotonic_function returned decreasing values.")


__all__ = [
    "DEFAULT_BACKOFF_MULTIPLIER",
    "DEFAULT_MAX_RETRY_DELAY_SECONDS",
    "DEFAULT_NON_RETRYABLE_EXCEPTIONS",
    "DEFAULT_RETRYABLE_EXCEPTIONS",
    "RetryAttempt",
    "RetryDecision",
    "RetryExecutionResult",
    "RetryExhaustedError",
    "RetryPolicy",
    "execute_with_retry",
    "extend_retryable_exceptions",
    "retry_delays",
    "should_retry",
]
