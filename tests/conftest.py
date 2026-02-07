import pytest
from pathlib import Path

from src.starsim.economy.commodities import commodity_registry
from src.starsim.economy.recipes import recipe_registry
from src.starsim.events.registry import event_registry # Import event_registry


@pytest.fixture(autouse=True)
def setup_registries():
    # Ensure commodity registry is loaded before tests
    if not commodity_registry._commodities:
        commodity_registry.load_from_yaml(Path("data/commodities.yaml"))
    # Ensure recipe registry is loaded before tests
    if not recipe_registry._recipes:
        recipe_registry.load_from_yaml(Path("data/recipes.yaml"))
    # Ensure event registry is loaded before tests
    if not event_registry._events:
        event_registry.load_from_yaml(Path("data/events.yaml"))


@pytest.fixture
def universe_yaml_path() -> Path:
    return Path("data/universe.yaml")

def pytest_addoption(parser):
    """Adds the --update-goldens command-line option."""
    parser.addoption(
        "--update-goldens", action="store_true", default=False, help="Update golden regression files."
    )

def pytest_configure(config):
    """Ensures --update-goldens is only used with 'test_generator_regression.py'."""
    if config.option.update_goldens:
        if not any("test_generator_regression.py" in arg for arg in config.args):
            # Only warn if the user hasn't explicitly specified a file/dir pattern
            config.warn(
                "USERWARNING",
                "The --update-goldens flag is intended for use with test_generator_regression.py. "
                "Specify the test file explicitly or use it carefully.",
            )