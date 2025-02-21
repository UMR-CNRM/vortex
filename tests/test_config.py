import pytest

from vortex import config

config.VORTEX_CONFIG = {
    "data-tree": {
        "op-rootdir": "/op/rootdir",
        "rootdir": "/a/b/c/rootdir",
    },
    "storage": {
        "address": "storage.meteo.fr",
        "protocol": "ftp",
    },
}

def test_section_from_config():
    with pytest.raises(config.ConfigurationError):
        config_section = config.from_config("nonexist")

    config_section = config.from_config("data-tree")

    assert config_section == config.VORTEX_CONFIG["data-tree"]


def test_key_from_config():
    with pytest.raises(config.ConfigurationError):
        config_value = config.from_config("data-tree", "nonexist")

    config_value = config.from_config("data-tree", "rootdir")

    assert config_value == config.VORTEX_CONFIG["data-tree"]["rootdir"]


def test_set_config():
    config.set_config("newsection", "newkey", 42)

    assert config.from_config("newsection", "newkey") == 42


def test_is_defined():
    assert not config.is_defined("nonexist")
    assert config.is_defined("storage")
    assert not config.is_defined("storage", "nonexist")
    assert config.is_defined("storage", "protocol")


def test_get_from_config_w_default():

    assert config.get_from_config_w_default(
        "data-tree", "nonexist", "default",
    ) == "default"

    assert config.get_from_config_w_default(
        "data-tree", "op-rootdir", "default",
    ) == config.from_config("data-tree", "op-rootdir")
        
    
    
