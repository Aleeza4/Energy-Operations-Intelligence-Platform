"""Unit tests for EOIP deterministic random-stream management."""

from __future__ import annotations

from types import MappingProxyType

import numpy as np
import pytest
from numpy.random import Generator, SeedSequence

from eoip.synthetic.random import (
    DEFAULT_STREAM_KEYS,
    DEFAULT_STREAM_VERSION,
    RandomContext,
    RandomStream,
    create_random_context,
)


def test_default_stream_keys_are_stable() -> None:
    """Verify the published stream allocation contract."""
    assert DEFAULT_STREAM_KEYS == (
        "portfolio",
        "weather",
        "degradation",
        "events",
        "telemetry_defects",
        "alarms",
        "incidents",
        "work_orders",
        "tariffs",
        "budgets",
        "meters",
        "plant_scada",
    )


def test_default_stream_version_is_stable() -> None:
    """Verify the public random-stream contract version."""
    assert DEFAULT_STREAM_VERSION == "1.0.0"


def test_create_random_context_returns_expected_type() -> None:
    """Verify the factory returns a RandomContext."""
    context = create_random_context(20_250_201)

    assert isinstance(context, RandomContext)


def test_context_exposes_root_seed_and_stream_metadata() -> None:
    """Verify context metadata is available."""
    context = create_random_context(20_250_201)

    assert context.root_seed == 20_250_201
    assert context.stream_version == DEFAULT_STREAM_VERSION
    assert context.stream_keys == DEFAULT_STREAM_KEYS
    assert len(context) == len(DEFAULT_STREAM_KEYS)


@pytest.mark.parametrize("value", [True, 1.5, "42", None])
def test_rejects_invalid_root_seed_type(value: object) -> None:
    """Verify root_seed must be an integer."""
    with pytest.raises(TypeError, match="root_seed must be an integer"):
        create_random_context(value)  # type: ignore[arg-type]


def test_rejects_negative_root_seed() -> None:
    """Verify root_seed cannot be negative."""
    with pytest.raises(ValueError, match="greater than or equal to zero"):
        create_random_context(-1)


def test_zero_root_seed_is_supported() -> None:
    """Verify zero remains a valid deterministic seed."""
    context = create_random_context(0)

    assert context.root_seed == 0


def test_named_streams_are_deterministic() -> None:
    """Verify identical contexts produce identical stream values."""
    first = create_random_context(123)
    second = create_random_context(123)

    first_values = first.stream("weather").random(10)
    second_values = second.stream("weather").random(10)

    assert np.array_equal(first_values, second_values)


def test_different_root_seeds_change_stream_values() -> None:
    """Verify changing the root seed changes stochastic output."""
    first = create_random_context(123)
    second = create_random_context(456)

    assert not np.array_equal(
        first.stream("weather").random(10),
        second.stream("weather").random(10),
    )


def test_named_streams_are_independent() -> None:
    """Verify unrelated streams do not share identical output."""
    context = create_random_context(123)

    weather = context.stream("weather").random(10)
    events = context.stream("events").random(10)

    assert not np.array_equal(weather, events)


def test_adding_unrelated_stream_does_not_perturb_existing_stream() -> None:
    """Verify stable name-derived seeding is independent of stream count."""
    base = create_random_context(
        123,
        stream_keys=("weather", "events"),
    )
    expanded = create_random_context(
        123,
        stream_keys=("weather", "events", "new_stream"),
    )

    assert np.array_equal(
        base.stream("weather").random(10),
        expanded.stream("weather").random(10),
    )
    assert np.array_equal(
        base.stream("events").random(10),
        expanded.stream("events").random(10),
    )


def test_reordering_stream_keys_does_not_change_stream_output() -> None:
    """Verify stream values depend on names, not tuple position."""
    first = create_random_context(
        123,
        stream_keys=("weather", "events"),
    )
    second = create_random_context(
        123,
        stream_keys=("events", "weather"),
    )

    assert np.array_equal(
        first.stream("weather").random(10),
        second.stream("weather").random(10),
    )


def test_stream_lookup_is_case_and_whitespace_normalized() -> None:
    """Verify stream names are normalized before lookup."""
    context = create_random_context(123)

    expected = create_random_context(123).stream("weather").random(5)
    actual = context.stream("  WEATHER  ").random(5)

    assert np.array_equal(actual, expected)


def test_unknown_stream_is_rejected() -> None:
    """Verify unknown stream names fail with available names."""
    context = create_random_context(123)

    with pytest.raises(KeyError, match="Unknown random stream"):
        context.stream("unknown")


def test_context_contains_stream_names() -> None:
    """Verify membership checks use normalized stream names."""
    context = create_random_context(123)

    assert "weather" in context
    assert " WEATHER " in context
    assert "unknown" not in context
    assert 123 not in context


def test_streams_mapping_is_immutable() -> None:
    """Verify callers cannot replace registered streams."""
    context = create_random_context(123)

    assert isinstance(context.streams, MappingProxyType)

    with pytest.raises(TypeError):
        context.streams["new"] = context.random_stream("weather")  # type: ignore[index]


def test_random_stream_metadata_types() -> None:
    """Verify stream wrappers expose NumPy random objects."""
    stream = create_random_context(123).random_stream("weather")

    assert isinstance(stream, RandomStream)
    assert isinstance(stream.seed_sequence, SeedSequence)
    assert isinstance(stream.generator, Generator)
    assert stream.name == "weather"


def test_random_stream_name_is_normalized() -> None:
    """Verify RandomStream normalizes its own name."""
    sequence = SeedSequence(123)
    stream = RandomStream(
        name="  WEATHER  ",
        seed_sequence=sequence,
        generator=np.random.default_rng(sequence),
    )

    assert stream.name == "weather"


def test_random_stream_rejects_empty_name() -> None:
    """Verify RandomStream names cannot be blank."""
    sequence = SeedSequence(123)

    with pytest.raises(ValueError, match="cannot be empty"):
        RandomStream(
            name="   ",
            seed_sequence=sequence,
            generator=np.random.default_rng(sequence),
        )


def test_random_stream_rejects_invalid_seed_sequence() -> None:
    """Verify stream seed metadata must use SeedSequence."""
    with pytest.raises(TypeError, match="SeedSequence"):
        RandomStream(
            name="weather",
            seed_sequence=object(),  # type: ignore[arg-type]
            generator=np.random.default_rng(123),
        )


def test_random_stream_rejects_invalid_generator() -> None:
    """Verify stream generators must use NumPy Generator."""
    with pytest.raises(TypeError, match="numpy Generator"):
        RandomStream(
            name="weather",
            seed_sequence=SeedSequence(123),
            generator=object(),  # type: ignore[arg-type]
        )


def test_state_fingerprint_is_deterministic() -> None:
    """Verify identical initial states have identical fingerprints."""
    first = create_random_context(123).random_stream("weather")
    second = create_random_context(123).random_stream("weather")

    assert first.state_fingerprint() == second.state_fingerprint()
    assert len(first.state_fingerprint()) == 64


def test_state_fingerprint_changes_after_consumption() -> None:
    """Verify state fingerprints reflect generator advancement."""
    stream = create_random_context(123).random_stream("weather")
    before = stream.state_fingerprint()

    stream.generator.random()
    after = stream.state_fingerprint()

    assert before != after


def test_entity_stream_is_deterministic() -> None:
    """Verify identical entity streams produce identical values."""
    first = create_random_context(123)
    second = create_random_context(123)

    assert np.array_equal(
        first.entity_stream("weather", "PLANT-001").random(10),
        second.entity_stream("weather", "PLANT-001").random(10),
    )


def test_entity_streams_are_entity_specific() -> None:
    """Verify different entity keys produce independent values."""
    context = create_random_context(123)

    first = context.entity_stream("weather", "PLANT-001").random(10)
    second = context.entity_stream("weather", "PLANT-002").random(10)

    assert not np.array_equal(first, second)


def test_entity_stream_does_not_advance_parent_stream() -> None:
    """Verify entity derivation does not mutate the parent stream."""
    first = create_random_context(123)
    second = create_random_context(123)

    first.entity_stream("weather", "PLANT-001").random(50)

    assert np.array_equal(
        first.stream("weather").random(10),
        second.stream("weather").random(10),
    )


def test_entity_processing_order_does_not_change_output() -> None:
    """Verify entity streams are stable regardless of iteration order."""
    context_a = create_random_context(123)
    context_b = create_random_context(123)

    first_order = {
        key: context_a.entity_stream("events", key).integers(0, 100, 5)
        for key in ("A", "B", "C")
    }
    second_order = {
        key: context_b.entity_stream("events", key).integers(0, 100, 5)
        for key in ("C", "B", "A")
    }

    for key in ("A", "B", "C"):
        assert np.array_equal(first_order[key], second_order[key])


@pytest.mark.parametrize("entity_key", [True, 1.5, None])
def test_entity_stream_rejects_invalid_key_types(
    entity_key: object,
) -> None:
    """Verify entity keys must be strings or integers."""
    context = create_random_context(123)

    with pytest.raises(TypeError, match="entity_key"):
        context.entity_stream(
            "weather",
            entity_key,  # type: ignore[arg-type]
        )


def test_entity_stream_rejects_negative_integer_key() -> None:
    """Verify integer entity keys cannot be negative."""
    context = create_random_context(123)

    with pytest.raises(ValueError, match="greater than or equal to zero"):
        context.entity_stream("weather", -1)


def test_entity_stream_rejects_blank_string_key() -> None:
    """Verify blank entity keys are rejected."""
    context = create_random_context(123)

    with pytest.raises(ValueError, match="cannot be empty"):
        context.entity_stream("weather", "   ")


def test_child_context_is_deterministic() -> None:
    """Verify child contexts are reproducible."""
    first = create_random_context(123).child_context("plant-001")
    second = create_random_context(123).child_context("plant-001")

    assert first.root_seed == second.root_seed
    assert np.array_equal(
        first.stream("events").random(10),
        second.stream("events").random(10),
    )


def test_different_child_namespaces_change_output() -> None:
    """Verify child namespaces create independent contexts."""
    context = create_random_context(123)

    first = context.child_context("plant-001")
    second = context.child_context("plant-002")

    assert first.root_seed != second.root_seed
    assert not np.array_equal(
        first.stream("events").random(10),
        second.stream("events").random(10),
    )


def test_child_context_does_not_advance_parent() -> None:
    """Verify child context derivation leaves parent streams unchanged."""
    first = create_random_context(123)
    second = create_random_context(123)

    first.child_context("subsystem").stream("weather").random(100)

    assert np.array_equal(
        first.stream("weather").random(10),
        second.stream("weather").random(10),
    )


def test_child_context_supports_custom_stream_keys() -> None:
    """Verify child contexts may expose a narrower stream set."""
    child = create_random_context(123).child_context(
        "subsystem",
        stream_keys=("weather", "events"),
    )

    assert child.stream_keys == ("weather", "events")
    assert len(child) == 2


def test_manifest_is_serialization_ready() -> None:
    """Verify random metadata can be written to a JSON manifest."""
    context = create_random_context(
        123,
        stream_keys=("weather", "events"),
    )
    manifest = context.manifest()

    assert manifest["root_seed"] == 123
    assert manifest["stream_version"] == DEFAULT_STREAM_VERSION
    assert manifest["stream_keys"] == ["weather", "events"]
    assert set(manifest["streams"]) == {"weather", "events"}

    weather_metadata = manifest["streams"]["weather"]  # type: ignore[index]
    assert isinstance(weather_metadata["spawn_key"], list)
    assert len(weather_metadata["initial_state_fingerprint"]) == 64


def test_manifest_is_independent_of_current_stream_state() -> None:
    """Verify manifest fingerprints describe initial stream allocation."""
    context = create_random_context(123)
    before = context.manifest()

    context.stream("weather").random(100)
    after = context.manifest()

    assert before == after


def test_context_repr_is_useful() -> None:
    """Verify developer representation contains key metadata."""
    value = repr(
        create_random_context(
            123,
            stream_keys=("weather", "events"),
        )
    )

    assert "RandomContext" in value
    assert "root_seed=123" in value
    assert "stream_count=2" in value
    assert DEFAULT_STREAM_VERSION in value


def test_rejects_non_tuple_stream_keys() -> None:
    """Verify stream_keys must be an immutable tuple."""
    with pytest.raises(TypeError, match="stream_keys must be a tuple"):
        create_random_context(
            123,
            stream_keys=["weather"],  # type: ignore[arg-type]
        )


def test_rejects_empty_stream_keys() -> None:
    """Verify at least one stream name is required."""
    with pytest.raises(ValueError, match="cannot be empty"):
        create_random_context(123, stream_keys=())


def test_rejects_duplicate_stream_keys_after_normalization() -> None:
    """Verify duplicate normalized stream names are rejected."""
    with pytest.raises(ValueError, match="unique names"):
        create_random_context(
            123,
            stream_keys=("weather", " WEATHER "),
        )


@pytest.mark.parametrize("stream_name", ["", "   "])
def test_rejects_blank_stream_names(stream_name: str) -> None:
    """Verify blank stream names are rejected."""
    with pytest.raises(ValueError, match="cannot be empty"):
        create_random_context(123, stream_keys=(stream_name,))


def test_rejects_non_string_stream_name() -> None:
    """Verify stream names must be strings."""
    with pytest.raises(TypeError, match="must be a string"):
        create_random_context(
            123,
            stream_keys=("weather", 1),  # type: ignore[arg-type]
        )


def test_stream_version_changes_stream_output() -> None:
    """Verify changing the allocation contract changes derived streams."""
    first = create_random_context(
        123,
        stream_keys=("weather",),
        stream_version="1.0.0",
    )
    second = create_random_context(
        123,
        stream_keys=("weather",),
        stream_version="2.0.0",
    )

    assert not np.array_equal(
        first.stream("weather").random(10),
        second.stream("weather").random(10),
    )


def test_rejects_blank_stream_version() -> None:
    """Verify stream_version cannot be blank."""
    with pytest.raises(ValueError, match="stream_version cannot be empty"):
        create_random_context(123, stream_version="   ")
