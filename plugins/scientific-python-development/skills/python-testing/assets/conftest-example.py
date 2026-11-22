# tests/conftest.py
import pytest
import numpy as np
from pathlib import Path

@pytest.fixture(scope="session")
def test_data_dir():
    """Provide path to test data directory."""
    return Path(__file__).parent / "data"

@pytest.fixture
def rng():
    """Provide a seeded random generator (no global state)."""
    return np.random.default_rng(42)

@pytest.fixture
def sample_array(rng):
    """Provide sample NumPy array."""
    return rng.standard_normal(100)

@pytest.fixture
def temp_output_dir(tmp_path):
    """Provide temporary directory for test outputs."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir

@pytest.fixture(autouse=True)
def reset_random_state():
    """Reset legacy global NumPy random state before each test (for code that still uses np.random.*)."""
    np.random.seed(42)

@pytest.fixture(scope="session")
def large_dataset():
    """Load large dataset once per test session."""
    return load_reference_data()

# Platform-specific fixtures
@pytest.fixture(params=["Linux", "Darwin", "Windows"])
def platform_name(request, monkeypatch):
    """Parametrize tests across platforms."""
    monkeypatch.setattr("platform.system", lambda: request.param)
    return request.param

