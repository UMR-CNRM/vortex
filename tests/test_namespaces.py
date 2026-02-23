import vortex
import footprints
import pytest


def test_default_is_multi():
    p = footprints.proxy.provider(experiment="dummy", block="dummy")
    assert p.namespace == "vortex.multi.fr"


def test_cache_only():
    p = footprints.proxy.provider(
        experiment="dummy", block="dummy", archive=False
    )
    assert p.namespace == "vortex.cache.fr"


def test_archive_only():
    p = footprints.proxy.provider(
        experiment="dummy", block="dummy", cache=False
    )
    assert p.namespace == "vortex.archive.fr"


def test_both_true_is_multi():
    p = footprints.proxy.provider(
        experiment="dummy",
        block="dummy",
        cache=True,
        archive=True,
    )
    assert p.namespace == "vortex.multi.fr"


def error_if_both_false():
    with pytest.raises(ValueError):
        footprints.proxy.provider(
            experiment="dummy",
            block="dummy",
            cache=False,
            archive=False,
        )


def error_if_missing_config():
    vortex.config.VORTEX_CONFIG = []
    assert not vortex.config.is_defined("storage")
    with pytest.raises(ValueError):
        footprints.proxy.provider(
            experiment="dummy",
            block="dummy",
            archive=True,
        )
