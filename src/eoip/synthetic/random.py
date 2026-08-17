"""
Deterministic named random-stream management for EOIP Phase 2.

This module is the sole owner of synthetic random-state creation. It uses
NumPy SeedSequence and Generator objects to provide stable named child streams
whose outputs do not change when unrelated downstream generators are added.

No generator should use NumPy's global random state or Python's random module.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

import numpy as np
from numpy.random import Generator, SeedSequence

DEFAULT_STREAM_KEYS: Final[tuple[str, ...]] = (
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

DEFAULT_STREAM_VERSION: Final[str] = "1.0.0"


@dataclass(frozen=True, slots=True)
class RandomStream:
    """Metadata and generator for one deterministic named random stream."""

    name: str
    seed_sequence: SeedSequence
    generator: Generator

    def __post_init__(self) -> None:
        """Validate stream metadata and NumPy random objects."""
        normalized_name = self.name.strip().lower()
        object.__setattr__(self, "name", normalized_name)

        if not normalized_name:
            raise ValueError("Random stream name cannot be empty.")

        if not isinstance(self.seed_sequence, SeedSequence):
            raise TypeError("seed_sequence must be a numpy SeedSequence.")

        if not isinstance(self.generator, Generator):
            raise TypeError("generator must be a numpy Generator.")

    @property
    def spawn_key(self) -> tuple[int, ...]:
        """Return the deterministic SeedSequence spawn key."""
        return tuple(self.seed_sequence.spawn_key)

    @property
    def entropy(self) -> int | tuple[int, ...]:
        """Return the root entropy carried by this child stream."""
        value = self.seed_sequence.entropy
        if isinstance(value, np.ndarray):
            return tuple(int(item) for item in value.tolist())
        if isinstance(value, (list, tuple)):
            return tuple(int(item) for item in value)
        return int(value)

    def state_fingerprint(self) -> str:
        """Return a deterministic fingerprint of current generator state."""
        normalized = json.dumps(
            self.generator.bit_generator.state,
            sort_keys=True,
            separators=(",", ":"),
            default=_json_default,
        ).encode("utf-8")
        return hashlib.sha256(normalized).hexdigest()


class RandomContext:
    """
    Stable collection of named NumPy random streams.

    Stream seeds are derived from the root seed plus a stable hash of each
    stream name and the declared stream version. They do not depend on tuple
    ordering or on how many other stream names exist.
    """

    __slots__ = (
        "_root_seed",
        "_stream_keys",
        "_stream_version",
        "_streams",
    )

    def __init__(
        self,
        root_seed: int,
        *,
        stream_keys: tuple[str, ...] = DEFAULT_STREAM_KEYS,
        stream_version: str = DEFAULT_STREAM_VERSION,
    ) -> None:
        """Create a validated deterministic random context."""
        _validate_root_seed(root_seed)
        normalized_version = _normalize_non_empty_string(
            "stream_version",
            stream_version,
        )
        normalized_keys = _normalize_stream_keys(stream_keys)

        streams = {
            name: _create_stream(
                root_seed=root_seed,
                stream_name=name,
                stream_version=normalized_version,
            )
            for name in normalized_keys
        }

        self._root_seed = root_seed
        self._stream_keys = normalized_keys
        self._stream_version = normalized_version
        self._streams: Mapping[str, RandomStream] = MappingProxyType(streams)

    @property
    def root_seed(self) -> int:
        """Return the global deterministic seed."""
        return self._root_seed

    @property
    def stream_version(self) -> str:
        """Return the random-stream allocation contract version."""
        return self._stream_version

    @property
    def stream_keys(self) -> tuple[str, ...]:
        """Return all available stream names in canonical order."""
        return self._stream_keys

    @property
    def streams(self) -> Mapping[str, RandomStream]:
        """Return the immutable stream mapping."""
        return self._streams

    def stream(self, name: str) -> Generator:
        """Return the NumPy generator for a named stream."""
        return self.random_stream(name).generator

    def random_stream(self, name: str) -> RandomStream:
        """Return full metadata for one named random stream."""
        normalized_name = _normalize_stream_name(name)

        try:
            return self._streams[normalized_name]
        except KeyError as exc:
            available = ", ".join(self._stream_keys)
            raise KeyError(
                f"Unknown random stream '{name}'. " f"Available streams: {available}."
            ) from exc

    def entity_stream(
        self,
        stream_name: str,
        entity_key: str | int,
    ) -> Generator:
        """
        Return a deterministic generator for one entity within a stream.

        Creating entity generators does not advance or mutate the parent named
        stream. This supports stable per-plant, per-equipment, and per-event
        random behavior regardless of processing order.
        """
        normalized_name = _normalize_stream_name(stream_name)
        if normalized_name not in self._streams:
            available = ", ".join(self._stream_keys)
            raise KeyError(
                f"Unknown random stream '{stream_name}'. "
                f"Available streams: {available}."
            )

        normalized_entity_key = _normalize_entity_key(entity_key)
        seed_words = _derive_seed_words(
            root_seed=self._root_seed,
            namespace=(
                f"{self._stream_version}:"
                f"{normalized_name}:entity:{normalized_entity_key}"
            ),
        )
        return np.random.default_rng(SeedSequence(seed_words))

    def child_context(
        self,
        namespace: str,
        *,
        stream_keys: tuple[str, ...] | None = None,
    ) -> RandomContext:
        """
        Return an independent deterministic context for a sub-pipeline.

        The child root seed is derived from the parent root seed, stream
        version, and namespace without consuming any existing generator.
        """
        normalized_namespace = _normalize_non_empty_string(
            "namespace",
            namespace,
        )
        derived_words = _derive_seed_words(
            root_seed=self._root_seed,
            namespace=(f"{self._stream_version}:context:{normalized_namespace}"),
        )
        derived_seed = _words_to_integer(derived_words)

        return RandomContext(
            derived_seed,
            stream_keys=stream_keys or self._stream_keys,
            stream_version=self._stream_version,
        )

    def manifest(self) -> dict[str, object]:
        """Return serialization-ready random-stream metadata."""
        return {
            "root_seed": self._root_seed,
            "stream_version": self._stream_version,
            "stream_keys": list(self._stream_keys),
            "streams": {
                name: {
                    "entropy": stream.entropy,
                    "spawn_key": list(stream.spawn_key),
                    "initial_state_fingerprint": _initial_fingerprint(
                        root_seed=self._root_seed,
                        stream_name=name,
                        stream_version=self._stream_version,
                    ),
                }
                for name, stream in self._streams.items()
            },
        }

    def __contains__(self, name: object) -> bool:
        """Return whether a stream name exists."""
        return isinstance(name, str) and name.strip().lower() in self._streams

    def __len__(self) -> int:
        """Return the number of named streams."""
        return len(self._streams)

    def __repr__(self) -> str:
        """Return a concise developer representation."""
        return (
            "RandomContext("
            f"root_seed={self._root_seed}, "
            f"stream_version={self._stream_version!r}, "
            f"stream_count={len(self)}"
            ")"
        )


def create_random_context(
    root_seed: int,
    *,
    stream_keys: tuple[str, ...] = DEFAULT_STREAM_KEYS,
    stream_version: str = DEFAULT_STREAM_VERSION,
) -> RandomContext:
    """Create a deterministic Phase 2 random context."""
    return RandomContext(
        root_seed,
        stream_keys=stream_keys,
        stream_version=stream_version,
    )


def _create_stream(
    *,
    root_seed: int,
    stream_name: str,
    stream_version: str,
) -> RandomStream:
    """Create one stable named random stream."""
    seed_words = _derive_seed_words(
        root_seed=root_seed,
        namespace=f"{stream_version}:stream:{stream_name}",
    )
    seed_sequence = SeedSequence(seed_words)
    return RandomStream(
        name=stream_name,
        seed_sequence=seed_sequence,
        generator=np.random.default_rng(seed_sequence),
    )


def _derive_seed_words(
    *,
    root_seed: int,
    namespace: str,
) -> tuple[int, ...]:
    """Derive stable 32-bit seed words from a seed and namespace."""
    payload = f"{root_seed}:{namespace}".encode()
    digest = hashlib.sha256(payload).digest()

    digest_words = tuple(
        int.from_bytes(digest[index : index + 4], "big") for index in range(0, 32, 4)
    )
    root_low = root_seed & 0xFFFFFFFF
    root_high = (root_seed >> 32) & 0xFFFFFFFF
    return (root_low, root_high, *digest_words)


def _words_to_integer(words: tuple[int, ...]) -> int:
    """Convert deterministic seed words into one non-negative integer."""
    payload = b"".join(int(word).to_bytes(4, "big", signed=False) for word in words)
    return int.from_bytes(
        hashlib.sha256(payload).digest()[:16],
        "big",
        signed=False,
    )


def _initial_fingerprint(
    *,
    root_seed: int,
    stream_name: str,
    stream_version: str,
) -> str:
    """Return the initial state fingerprint without mutating a stream."""
    stream = _create_stream(
        root_seed=root_seed,
        stream_name=stream_name,
        stream_version=stream_version,
    )
    return stream.state_fingerprint()


def _normalize_stream_keys(
    stream_keys: tuple[str, ...],
) -> tuple[str, ...]:
    """Validate, normalize, and preserve canonical stream ordering."""
    if not isinstance(stream_keys, tuple):
        raise TypeError("stream_keys must be a tuple.")

    if not stream_keys:
        raise ValueError("stream_keys cannot be empty.")

    normalized = tuple(_normalize_stream_name(name) for name in stream_keys)

    if len(normalized) != len(set(normalized)):
        raise ValueError("stream_keys must contain unique names.")

    return normalized


def _normalize_stream_name(name: str) -> str:
    """Normalize and validate one random-stream name."""
    return _normalize_non_empty_string("stream name", name).lower()


def _normalize_entity_key(entity_key: str | int) -> str:
    """Normalize a deterministic entity key."""
    if isinstance(entity_key, bool):
        raise TypeError("entity_key must be a string or integer.")

    if isinstance(entity_key, int):
        if entity_key < 0:
            raise ValueError(
                "Integer entity_key must be greater than or equal to zero."
            )
        return str(entity_key)

    if isinstance(entity_key, str):
        return _normalize_non_empty_string("entity_key", entity_key)

    raise TypeError("entity_key must be a string or integer.")


def _normalize_non_empty_string(name: str, value: str) -> str:
    """Normalize and validate a non-empty string."""
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} cannot be empty.")

    return normalized


def _validate_root_seed(root_seed: int) -> None:
    """Validate a non-negative integer root seed."""
    if isinstance(root_seed, bool) or not isinstance(root_seed, int):
        raise TypeError("root_seed must be an integer.")

    if root_seed < 0:
        raise ValueError("root_seed must be greater than or equal to zero.")


def _json_default(value: object) -> object:
    """Normalize NumPy scalar and array values for JSON serialization."""
    if isinstance(value, np.ndarray):
        return value.tolist()

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        return float(value)

    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable.")


__all__ = [
    "DEFAULT_STREAM_KEYS",
    "DEFAULT_STREAM_VERSION",
    "RandomContext",
    "RandomStream",
    "create_random_context",
]
