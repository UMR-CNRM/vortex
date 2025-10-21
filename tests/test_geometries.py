"""Tests for geometry loading from distribution and user configuration."""

import os
import tempfile
from pathlib import Path
from unittest.mock import PropertyMock, patch

import pytest


@pytest.fixture
def user_geometries_file():
    """Create a temporary user geometries.ini file and set up the environment."""
    # Create a temporary directory for user config
    with tempfile.TemporaryDirectory() as tmpdir:
        user_config_dir = Path(tmpdir)
        geometries_file = user_config_dir / "geometries.ini"

        # Write test geometries to the file
        geometries_file.write_text("""# User-specific geometries for testing
[test_user_geo]
info       = My custom test geometry
kind       = gauss
area       = france
truncation = 999
stretching = 3.0

[test_projected]
info       = User projected geometry
kind       = projected
area       = testarea
resolution = 5.0
runit      = km
""")

        # Patch the configrc property to return our temp directory
        with patch(
            "vortex.gloves.Glove.configrc", new_callable=PropertyMock
        ) as mock_configrc:
            mock_configrc.return_value = str(user_config_dir)
            yield geometries_file


@pytest.fixture
def user_override_file():
    """Create a user geometries.ini that overrides a standard geometry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        user_config_dir = Path(tmpdir)
        geometries_file = user_config_dir / "geometries.ini"

        # Override a standard geometry
        geometries_file.write_text("""# Override standard geometry
[global798]
info       = User-overridden ARPEGE geometry
kind       = gauss
area       = custom
truncation = 798
stretching = 5.0
""")

        with patch(
            "vortex.gloves.Glove.configrc", new_callable=PropertyMock
        ) as mock_configrc:
            mock_configrc.return_value = str(user_config_dir)
            yield geometries_file


def test_load_standard_geometries():
    """Test that standard geometries are loaded from distribution."""
    from vortex.data import geometries

    # Should have loaded standard geometries
    # There are 335 in the distribution at the time of writing
    assert len(geometries.keys()) > 300

    # Check a known standard geometry
    assert "global798" in geometries.keys()

    geo = geometries.get(tag="global798")
    assert geo.info == "ARPEGE TL798 stretched-rotated geometry"
    assert geo.truncation == 798
    assert geo.stretching == 2.4
    assert geo.area == "france"


def test_load_user_geometries(user_geometries_file):
    """Test that user geometries are loaded from ~/.vortexrc/geometries.ini."""
    # Import geometries module - this will trigger load() with our patched configrc
    # need to reload to pick up the new configrc path
    import importlib
    from vortex.data import geometries as geom_module

    importlib.reload(geom_module)

    from vortex.data import geometries

    # User geometries should be present
    assert "test_user_geo" in geometries.keys()
    assert "test_projected" in geometries.keys()

    # Check user gaussian geometry
    geo = geometries.get(tag="test_user_geo")
    assert geo.info == "My custom test geometry"
    assert geo.truncation == 999
    assert geo.stretching == 3.0
    assert type(geo).__name__ == "GaussGeometry"

    # Check user projected geometry
    geo2 = geometries.get(tag="test_projected")
    assert geo2.info == "User projected geometry"
    assert geo2.resolution == 5.0
    assert type(geo2).__name__ == "ProjectedGeometry"


def test_user_geometry_override(user_override_file):
    """Test that user geometries override standard ones with the same tag."""
    import importlib
    from vortex.data import geometries as geom_module

    importlib.reload(geom_module)

    from vortex.data import geometries

    # The global798 geometry should have user values, not standard ones
    geo = geometries.get(tag="global798")
    assert geo.info == "User-overridden ARPEGE geometry"
    assert geo.area == "custom"
    assert geo.stretching == 5.0
    assert (
        geo.truncation == 798
    )  # Same as original but with different stretching


def test_geometry_singleton_behavior():
    """Test that GetByTag returns the same object for repeated calls."""
    from vortex.data import geometries

    # Multiple retrievals should return the same object
    geo1 = geometries.get(tag="global798")
    geo2 = geometries.Geometry("global798")
    geo3 = geometries.GaussGeometry("global798")

    # All should be the exact same object (singleton behavior)
    assert geo1 is geo2
    assert geo2 is geo3


def test_create_new_geometry_requires_explicit_new():
    """Test that creating a non-existent geometry requires new=True."""
    from vortex.data import geometries

    # Trying to access non-existent geometry should raise RuntimeError
    with pytest.raises(RuntimeError, match="does not exist yet"):
        geometries.Geometry("nonexistent_geometry")

    # But creating with new=True should work
    new_geo = geometries.GaussGeometry(
        tag="runtime_created_geo",
        new=True,
        info="Created at runtime",
        truncation=100,
        stretching=2.0,
        area="test",
    )

    assert new_geo.tag == "runtime_created_geo"

    # Now it should be accessible
    retrieved = geometries.Geometry("runtime_created_geo")
    assert retrieved is new_geo
