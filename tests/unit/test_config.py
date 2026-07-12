from src.config import Settings
from src.random_utils import set_random_seed


def test_default_settings() -> None:
    settings = Settings()

    assert settings.app_name == "Energy Operations Intelligence Platform"
    assert settings.random_seed == 42


def test_random_seed() -> None:
    set_random_seed(42)
