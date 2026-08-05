"""
Custom exception hierarchy for the Energy Operations Intelligence Platform.

All EOIP-specific exceptions must inherit from EOIPError so application
failures can be handled consistently across configuration, data generation,
validation, ETL, database, analytics, machine learning, API, and dashboard
components.
"""

from __future__ import annotations


class EOIPError(Exception):
    """Base exception for every EOIP-specific application error."""


class ConfigurationError(EOIPError):
    """Raised when application configuration is missing, invalid, or unsafe."""


class DirectoryInitializationError(EOIPError):
    """Raised when a required project directory cannot be created or accessed."""


class DatabaseError(EOIPError):
    """Raised when a database connection, transaction, or query operation fails."""


class ValidationError(EOIPError):
    """Raised when data fails a mandatory validation rule."""


class ETLError(EOIPError):
    """Raised when an extraction, transformation, or loading operation fails."""


class DataGenerationError(EOIPError):
    """Raised when synthetic data generation cannot complete successfully."""


class AnalyticsError(EOIPError):
    """Raised when a deterministic analytical or KPI calculation fails."""


class ForecastingError(EOIPError):
    """Raised when forecasting preparation, training, or evaluation fails."""


class ModelError(EOIPError):
    """Raised when a machine-learning model operation fails."""


class RecommendationError(EOIPError):
    """Raised when an operational recommendation cannot be generated or ranked."""


class VisualizationError(EOIPError):
    """Raised when a reusable visualization cannot be constructed."""


class DashboardError(EOIPError):
    """Raised when the Streamlit application encounters an unrecoverable error."""


class APIError(EOIPError):
    """Raised when an API request, response, or service operation fails."""
