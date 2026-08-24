"""Unit tests for EOIP Phase 3 ETL retry utilities."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from eoip.etl.config import RetryConfig
from eoip.etl.retry import (
    DEFAULT_BACKOFF_MULTIPLIER,
    DEFAULT_MAX_RETRY_DELAY_SECONDS,
    DEFAULT_NON_RETRYABLE_EXCEPTIONS,
    DEFAULT_RETRYABLE_EXCEPTIONS,
    RetryAttempt,
    RetryDecision,
    RetryExecutionResult,
    RetryExhaustedError,
    RetryPolicy,
    execute_with_retry,
    extend_retryable_exceptions,
    retry_delays,
    should_retry,
)


def _retry_config(
    *,
    task_retries: int = 2,
    flow_retries: int = 1,
    retry_delay_seconds: float = 1.0,
    timeout_seconds: float = 10.0,
) -> RetryConfig:
    """Return a deterministic retry configuration."""
    return RetryConfig(
        task_retries=task_retries,
        flow_retries=flow_retries,
        retry_delay_seconds=retry_delay_seconds,
        timeout_seconds=timeout_seconds,
    )


def _policy(
    *,
    maximum_retries: int = 2,
    retry_delay_seconds: float = 1.0,
    timeout_seconds: float = 10.0,
    backoff_multiplier: float = 2.0,
    maximum_retry_delay_seconds: float = 300.0,
    retryable_exceptions: tuple[type[BaseException], ...] = (
        ConnectionError,
        TimeoutError,
    ),
    non_retryable_exceptions: tuple[type[BaseException], ...] = (
        KeyboardInterrupt,
        SystemExit,
    ),
) -> RetryPolicy:
    """Return a deterministic retry policy."""
    return RetryPolicy(
        maximum_retries=maximum_retries,
        retry_delay_seconds=retry_delay_seconds,
        timeout_seconds=timeout_seconds,
        backoff_multiplier=backoff_multiplier,
        maximum_retry_delay_seconds=maximum_retry_delay_seconds,
        retryable_exceptions=retryable_exceptions,
        non_retryable_exceptions=non_retryable_exceptions,
    )


def _success_attempt() -> RetryAttempt:
    """Return a representative successful attempt."""
    return RetryAttempt(
        attempt_number=1,
        started_monotonic=1.0,
        completed_monotonic=2.0,
        decision=RetryDecision.SUCCESS,
    )


def _fail_attempt() -> RetryAttempt:
    """Return a representative failed attempt."""
    return RetryAttempt(
        attempt_number=1,
        started_monotonic=1.0,
        completed_monotonic=2.0,
        decision=RetryDecision.FAIL,
        error_type="ValueError",
        error_message="bad value",
    )


def _clock(values: list[float]):
    """Return a deterministic monotonic clock callable."""
    iterator = iter(values)
    return lambda: next(iterator)


class TestRetryDecision:
    """Tests for RetryDecision."""

    def test_values_are_stable(self) -> None:
        assert RetryDecision.SUCCESS.value == "success"
        assert RetryDecision.RETRY.value == "retry"
        assert RetryDecision.FAIL.value == "fail"


class TestRetryPolicy:
    """Tests for RetryPolicy."""

    def test_valid_policy(self) -> None:
        policy = _policy()

        assert policy.maximum_retries == 2
        assert policy.maximum_attempts == 3
        assert policy.retry_delay_seconds == 1.0
        assert policy.timeout_seconds == 10.0

    def test_task_policy_uses_task_retry_count(self) -> None:
        policy = RetryPolicy.for_task(
            _retry_config(
                task_retries=4,
                flow_retries=2,
            )
        )

        assert policy.maximum_retries == 4
        assert policy.maximum_attempts == 5

    def test_flow_policy_uses_flow_retry_count(self) -> None:
        policy = RetryPolicy.for_flow(
            _retry_config(
                task_retries=4,
                flow_retries=2,
            )
        )

        assert policy.maximum_retries == 2
        assert policy.maximum_attempts == 3

    def test_task_policy_rejects_invalid_config(self) -> None:
        with pytest.raises(
            TypeError,
            match="config must be a RetryConfig",
        ):
            RetryPolicy.for_task("invalid")  # type: ignore[arg-type]

    def test_maximum_retries_rejects_negative_value(self) -> None:
        with pytest.raises(ValueError):
            _policy(maximum_retries=-1)

    @pytest.mark.parametrize(
        "field_name",
        [
            "retry_delay_seconds",
            "timeout_seconds",
            "backoff_multiplier",
            "maximum_retry_delay_seconds",
        ],
    )
    def test_positive_numeric_settings_reject_zero(
        self,
        field_name: str,
    ) -> None:
        kwargs = {
            field_name: 0.0,
        }

        with pytest.raises(ValueError):
            _policy(**kwargs)

    def test_retryable_exceptions_requires_tuple(self) -> None:
        with pytest.raises(
            TypeError,
            match="retryable_exceptions must be a tuple",
        ):
            _policy(retryable_exceptions=[ConnectionError])  # type: ignore[arg-type]

    def test_retryable_exceptions_require_exception_classes(self) -> None:
        with pytest.raises(
            TypeError,
            match="must contain exception classes",
        ):
            _policy(retryable_exceptions=("ConnectionError",))  # type: ignore[arg-type]

    def test_retryable_non_retryable_overlap_is_rejected(self) -> None:
        with pytest.raises(
            ValueError,
            match="cannot overlap",
        ):
            _policy(
                retryable_exceptions=(ConnectionError,),
                non_retryable_exceptions=(ConnectionError,),
            )

    def test_delay_for_retry_uses_exponential_backoff(self) -> None:
        policy = _policy(
            retry_delay_seconds=2.0,
            backoff_multiplier=3.0,
        )

        assert policy.delay_for_retry(1) == 2.0
        assert policy.delay_for_retry(2) == 6.0
        assert policy.delay_for_retry(3) == 18.0

    def test_delay_for_retry_is_capped(self) -> None:
        policy = _policy(
            retry_delay_seconds=10.0,
            backoff_multiplier=10.0,
            maximum_retry_delay_seconds=50.0,
        )

        assert policy.delay_for_retry(1) == 10.0
        assert policy.delay_for_retry(2) == 50.0
        assert policy.delay_for_retry(3) == 50.0

    def test_delay_for_retry_requires_positive_retry_number(
        self,
    ) -> None:
        with pytest.raises(ValueError):
            _policy().delay_for_retry(0)

    def test_retryable_error_is_detected(self) -> None:
        assert _policy().is_retryable(ConnectionError("temporary"))

    def test_non_retryable_error_is_detected(self) -> None:
        assert not _policy().is_retryable(KeyboardInterrupt())

    def test_unlisted_error_is_not_retryable(self) -> None:
        assert not _policy().is_retryable(ValueError("bad"))

    def test_is_retryable_rejects_non_exception(self) -> None:
        with pytest.raises(
            TypeError,
            match="error must be an exception",
        ):
            _policy().is_retryable("bad")  # type: ignore[arg-type]

    def test_policy_is_frozen(self) -> None:
        policy = _policy()

        with pytest.raises(FrozenInstanceError):
            policy.maximum_retries = 5  # type: ignore[misc]


class TestRetryAttempt:
    """Tests for RetryAttempt."""

    def test_success_attempt(self) -> None:
        attempt = _success_attempt()

        assert attempt.duration_seconds == 1.0
        assert attempt.decision is RetryDecision.SUCCESS

    def test_retry_attempt(self) -> None:
        attempt = RetryAttempt(
            attempt_number=1,
            started_monotonic=1.0,
            completed_monotonic=1.5,
            decision=RetryDecision.RETRY,
            delay_before_next_attempt=2.0,
            error_type="ConnectionError",
            error_message="temporary",
        )

        assert attempt.delay_before_next_attempt == 2.0
        assert attempt.duration_seconds == 0.5

    def test_attempt_number_must_be_positive(self) -> None:
        with pytest.raises(ValueError):
            RetryAttempt(
                attempt_number=0,
                started_monotonic=1.0,
                completed_monotonic=2.0,
                decision=RetryDecision.SUCCESS,
            )

    def test_completed_time_cannot_precede_started_time(self) -> None:
        with pytest.raises(
            ValueError,
            match="cannot be earlier",
        ):
            RetryAttempt(
                attempt_number=1,
                started_monotonic=2.0,
                completed_monotonic=1.0,
                decision=RetryDecision.SUCCESS,
            )

    def test_success_cannot_contain_error_metadata(self) -> None:
        with pytest.raises(
            ValueError,
            match="error_type",
        ):
            RetryAttempt(
                attempt_number=1,
                started_monotonic=1.0,
                completed_monotonic=2.0,
                decision=RetryDecision.SUCCESS,
                error_type="ValueError",
            )

    def test_retry_requires_error_type(self) -> None:
        with pytest.raises(
            ValueError,
            match="error_type",
        ):
            RetryAttempt(
                attempt_number=1,
                started_monotonic=1.0,
                completed_monotonic=2.0,
                decision=RetryDecision.RETRY,
                error_message="temporary",
            )

    def test_retry_requires_error_message(self) -> None:
        with pytest.raises(
            ValueError,
            match="error_message",
        ):
            RetryAttempt(
                attempt_number=1,
                started_monotonic=1.0,
                completed_monotonic=2.0,
                decision=RetryDecision.RETRY,
                error_type="ConnectionError",
            )

    def test_final_failure_cannot_have_retry_delay(self) -> None:
        with pytest.raises(
            ValueError,
            match="cannot contain retry delay",
        ):
            RetryAttempt(
                attempt_number=1,
                started_monotonic=1.0,
                completed_monotonic=2.0,
                decision=RetryDecision.FAIL,
                delay_before_next_attempt=1.0,
                error_type="ValueError",
                error_message="bad value",
            )


class TestRetryExecutionResult:
    """Tests for RetryExecutionResult."""

    def test_valid_result(self) -> None:
        result = RetryExecutionResult(
            value=42,
            attempts=(_success_attempt(),),
        )

        assert result.value == 42
        assert result.attempt_count == 1
        assert result.retry_count == 0

    def test_retry_count_is_attempt_count_minus_one(self) -> None:
        retry_attempt = RetryAttempt(
            attempt_number=1,
            started_monotonic=1.0,
            completed_monotonic=2.0,
            decision=RetryDecision.RETRY,
            delay_before_next_attempt=1.0,
            error_type="ConnectionError",
            error_message="temporary",
        )
        success_attempt = RetryAttempt(
            attempt_number=2,
            started_monotonic=3.0,
            completed_monotonic=4.0,
            decision=RetryDecision.SUCCESS,
        )

        result = RetryExecutionResult(
            value="ok",
            attempts=(
                retry_attempt,
                success_attempt,
            ),
        )

        assert result.attempt_count == 2
        assert result.retry_count == 1

    def test_attempts_must_be_tuple(self) -> None:
        with pytest.raises(
            TypeError,
            match="attempts must be a tuple",
        ):
            RetryExecutionResult(
                value=1,
                attempts=[_success_attempt()],  # type: ignore[arg-type]
            )

    def test_attempts_cannot_be_empty(self) -> None:
        with pytest.raises(
            ValueError,
            match="attempts cannot be empty",
        ):
            RetryExecutionResult(
                value=1,
                attempts=(),
            )

    def test_result_must_end_with_success(self) -> None:
        with pytest.raises(
            ValueError,
            match="must end with a SUCCESS",
        ):
            RetryExecutionResult(
                value=None,
                attempts=(_fail_attempt(),),
            )


class TestRetryExhaustedError:
    """Tests for RetryExhaustedError."""

    def test_error_exposes_attempts_and_last_error(self) -> None:
        last_error = ValueError("bad")

        error = RetryExhaustedError(
            "failed",
            attempts=(_fail_attempt(),),
            last_error=last_error,
        )

        assert str(error) == "failed"
        assert error.attempt_count == 1
        assert error.last_error is last_error

    def test_empty_message_is_rejected(self) -> None:
        with pytest.raises(
            ValueError,
            match="message cannot be empty",
        ):
            RetryExhaustedError(
                " ",
                attempts=(_fail_attempt(),),
                last_error=ValueError("bad"),
            )

    def test_empty_attempts_are_rejected(self) -> None:
        with pytest.raises(
            ValueError,
            match="attempts cannot be empty",
        ):
            RetryExhaustedError(
                "failed",
                attempts=(),
                last_error=ValueError("bad"),
            )


class TestExecuteWithRetry:
    """Tests for execute_with_retry."""

    def test_success_on_first_attempt(self) -> None:
        result = execute_with_retry(
            lambda: 42,
            _policy(),
            sleep_function=lambda _: None,
            monotonic_function=_clock(
                [
                    1.0,
                    2.0,
                ]
            ),
        )

        assert result.value == 42
        assert result.attempt_count == 1
        assert result.retry_count == 0
        assert result.attempts[0].decision is RetryDecision.SUCCESS

    def test_retryable_failure_then_success(self) -> None:
        calls = {
            "count": 0,
        }
        sleeps: list[float] = []

        def function() -> str:
            calls["count"] += 1

            if calls["count"] == 1:
                raise ConnectionError("temporary")

            return "ok"

        result = execute_with_retry(
            function,
            _policy(),
            sleep_function=sleeps.append,
            monotonic_function=_clock(
                [
                    1.0,
                    2.0,
                    3.0,
                    4.0,
                ]
            ),
        )

        assert result.value == "ok"
        assert result.attempt_count == 2
        assert result.retry_count == 1
        assert sleeps == [1.0]
        assert result.attempts[0].decision is RetryDecision.RETRY
        assert result.attempts[1].decision is RetryDecision.SUCCESS

    def test_retryable_failure_exhausts_attempts(self) -> None:
        sleeps: list[float] = []

        def function() -> None:
            raise ConnectionError("still unavailable")

        with pytest.raises(RetryExhaustedError) as exc_info:
            execute_with_retry(
                function,
                _policy(
                    maximum_retries=2,
                ),
                sleep_function=sleeps.append,
                monotonic_function=_clock(
                    [
                        1.0,
                        2.0,
                        3.0,
                        4.0,
                        5.0,
                        6.0,
                    ]
                ),
            )

        error = exc_info.value

        assert error.attempt_count == 3
        assert sleeps == [
            1.0,
            2.0,
        ]
        assert isinstance(
            error.last_error,
            ConnectionError,
        )
        assert error.attempts[-1].decision is RetryDecision.FAIL

    def test_non_retryable_error_fails_immediately(self) -> None:
        sleeps: list[float] = []

        with pytest.raises(RetryExhaustedError) as exc_info:
            execute_with_retry(
                lambda: (_ for _ in ()).throw(ValueError("bad input")),
                _policy(),
                sleep_function=sleeps.append,
                monotonic_function=_clock(
                    [
                        1.0,
                        2.0,
                    ]
                ),
            )

        assert exc_info.value.attempt_count == 1
        assert isinstance(
            exc_info.value.last_error,
            ValueError,
        )
        assert sleeps == []

    def test_timeout_is_retried_when_retryable(self) -> None:
        calls = {
            "count": 0,
        }
        sleeps: list[float] = []

        def function() -> str:
            calls["count"] += 1
            return "ok"

        result = execute_with_retry(
            function,
            _policy(
                maximum_retries=1,
                timeout_seconds=1.0,
            ),
            sleep_function=sleeps.append,
            monotonic_function=_clock(
                [
                    1.0,
                    3.0,
                    4.0,
                    4.5,
                ]
            ),
        )

        assert calls["count"] == 2
        assert result.value == "ok"
        assert result.retry_count == 1
        assert sleeps == [1.0]
        assert result.attempts[0].error_type == "TimeoutError"

    def test_timeout_exhaustion_raises(self) -> None:
        with pytest.raises(RetryExhaustedError) as exc_info:
            execute_with_retry(
                lambda: "ok",
                _policy(
                    maximum_retries=0,
                    timeout_seconds=1.0,
                ),
                sleep_function=lambda _: None,
                monotonic_function=_clock(
                    [
                        1.0,
                        3.0,
                    ]
                ),
            )

        assert isinstance(
            exc_info.value.last_error,
            TimeoutError,
        )

    def test_function_arguments_are_forwarded(self) -> None:
        result = execute_with_retry(
            lambda x, y=0: x + y,
            _policy(),
            2,
            y=3,
            sleep_function=lambda _: None,
            monotonic_function=_clock(
                [
                    1.0,
                    2.0,
                ]
            ),
        )

        assert result.value == 5

    def test_invalid_function_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="function must be callable",
        ):
            execute_with_retry(
                1,  # type: ignore[arg-type]
                _policy(),
            )

    def test_invalid_policy_is_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="policy must be a RetryPolicy",
        ):
            execute_with_retry(
                lambda: None,
                "invalid",  # type: ignore[arg-type]
            )

    def test_decreasing_monotonic_values_are_rejected(self) -> None:
        with pytest.raises(
            ValueError,
            match="decreasing values",
        ):
            execute_with_retry(
                lambda: "ok",
                _policy(),
                sleep_function=lambda _: None,
                monotonic_function=_clock(
                    [
                        2.0,
                        1.0,
                    ]
                ),
            )


class TestRetryHelpers:
    """Tests for public retry helper functions."""

    def test_should_retry_retryable_error(self) -> None:
        assert should_retry(
            _policy(),
            ConnectionError("temporary"),
            attempt_number=1,
        )

    def test_should_retry_false_on_last_attempt(self) -> None:
        policy = _policy(
            maximum_retries=2,
        )

        assert not should_retry(
            policy,
            ConnectionError("temporary"),
            attempt_number=3,
        )

    def test_should_retry_false_for_non_retryable_error(self) -> None:
        assert not should_retry(
            _policy(),
            ValueError("bad"),
            attempt_number=1,
        )

    def test_retry_delays_returns_all_delays(self) -> None:
        policy = _policy(
            maximum_retries=3,
            retry_delay_seconds=2.0,
            backoff_multiplier=2.0,
        )

        assert retry_delays(policy) == (
            2.0,
            4.0,
            8.0,
        )

    def test_extend_retryable_exceptions(self) -> None:
        policy = extend_retryable_exceptions(
            _policy(),
            (ValueError,),
        )

        assert ValueError in policy.retryable_exceptions
        assert policy.is_retryable(ValueError("temporary"))

    def test_extend_retryable_exceptions_does_not_duplicate(
        self,
    ) -> None:
        policy = extend_retryable_exceptions(
            _policy(),
            (ConnectionError,),
        )

        assert policy.retryable_exceptions.count(ConnectionError) == 1

    def test_extend_retryable_exceptions_rejects_invalid_type(
        self,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="exception classes",
        ):
            extend_retryable_exceptions(
                _policy(),
                ("ValueError",),  # type: ignore[arg-type]
            )


class TestRetryConstants:
    """Tests for stable retry defaults."""

    def test_default_constants(self) -> None:
        assert DEFAULT_BACKOFF_MULTIPLIER == 2.0
        assert DEFAULT_MAX_RETRY_DELAY_SECONDS == 300.0
        assert (
            ConnectionError,
            TimeoutError,
        ) == DEFAULT_RETRYABLE_EXCEPTIONS


assert (
    KeyboardInterrupt,
    SystemExit,
) == DEFAULT_NON_RETRYABLE_EXCEPTIONS
