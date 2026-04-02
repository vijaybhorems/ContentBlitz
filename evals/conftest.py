"""Shared fixtures and configuration for evals."""

import pytest


def pytest_collection_modifyitems(config, items):
    """Add 'eval' marker to all tests in the evals directory."""
    for item in items:
        if "evals" in str(item.fspath):
            item.add_marker(pytest.mark.eval)
