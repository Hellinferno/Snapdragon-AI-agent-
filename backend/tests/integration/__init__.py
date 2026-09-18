"""Marker exports for the integration test package.

Keeps the integration directory importable so pytest collects it cleanly.
All tests here require real external network/API access and are deselected
from the default hermetic `pytest` run.
"""
