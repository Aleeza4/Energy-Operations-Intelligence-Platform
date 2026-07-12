import structlog

from src.config import get_settings
from src.logging_config import configure_logging
from src.random_utils import set_random_seed


def main() -> None:
    """Validate the initial project configuration."""

    settings = get_settings()
    configure_logging(settings.log_level)
    set_random_seed(settings.random_seed)

    logger = structlog.get_logger()

    logger.info(
        "application_initialized",
        app_name=settings.app_name,
        environment=settings.app_env,
        version=settings.app_version,
        random_seed=settings.random_seed,
    )


if __name__ == "__main__":
    main()
