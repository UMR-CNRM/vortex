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


@pytest.fixture
def clean_config():
    """Save and restore VORTEX_CONFIG and _PATH around a test."""
    saved_cfg = config.VORTEX_CONFIG.copy()
    saved_path = config._PATH
    config.VORTEX_CONFIG = {}
    config._PATH = None
    yield
    config.VORTEX_CONFIG = saved_cfg
    config._PATH = saved_path


@pytest.fixture
def toml_config_file(tmp_path):
    p = tmp_path / "vortex.toml"
    p.write_text('[data-tree]\nrootdir = "/tmp/data"\n')
    return p


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
    assert (
        config.get_from_config_w_default(
            "data-tree",
            "nonexist",
            "default",
        )
        == "default"
    )

    assert config.get_from_config_w_default(
        "data-tree",
        "op-rootdir",
        "default",
    ) == config.from_config("data-tree", "op-rootdir")


def test_load_config_populates_config(clean_config, toml_config_file):
    config.load_config(toml_config_file)

    assert config.VORTEX_CONFIG == {"data-tree": {"rootdir": "/tmp/data"}}


def test_load_config_sets_file_property(clean_config, toml_config_file):
    config.load_config(toml_config_file)

    assert config.file == toml_config_file.absolute()


def test_load_config_overrides_existing(clean_config, tmp_path):
    first = tmp_path / "first.toml"
    first.write_text('[section-a]\nkey = "value-a"\n')
    second = tmp_path / "second.toml"
    second.write_text('[section-b]\nkey = "value-b"\n')

    config.load_config(first)
    config.load_config(second)

    assert "section-a" not in config.VORTEX_CONFIG
    assert config.VORTEX_CONFIG == {"section-b": {"key": "value-b"}}


def test_load_config_file_not_found(clean_config, tmp_path, capsys):
    config.load_config(tmp_path / "nonexistent.toml")

    captured = capsys.readouterr()
    assert "not found" in captured.out
    assert config.VORTEX_CONFIG == {}
