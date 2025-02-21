"""This module provides getter and setter functions to set and get
the value of configuration options, respectively.

"""

import tomli

from bronx.fancies import loggers

__all__ = [
    "load_config",
    "print_config",
    "from_config",
    "set_config",
    "is_defined",
]

VORTEX_CONFIG = {}

logger = loggers.getLogger(__name__)


class ConfigurationError(Exception):
    """Something is wrong with the provided configuration"""


def load_config(configpath="vortex.toml"):
    """Load configuration from a TOML configuration file

    Existing configuration values are overriden. The configuration
    is expected to have valid TOML syntax, e.g.

    .. code:: toml

       [data-tree]
       op_rootdir = "/chaine/mxpt001"

       [storage]
       address = "hendrix.meteo.fr"
       protocol = "ftp"
       # ...
    """
    global VORTEX_CONFIG
    try:
        with open(configpath, "rb") as f:
            VORTEX_CONFIG = tomli.load(f)
        print(f"Successfully read configuration file {configpath}")
    except FileNotFoundError:
        print(f"Could not read configuration file {configpath} (not found).")
        print("Use load_config(/path/to/config) to update the configuration")


def print_config():
    """Print configuration (key, value) pairs"""
    if VORTEX_CONFIG:
        for k, v in VORTEX_CONFIG:
            print(k.upper(), v)


def from_config(section, key=None):
    """Retrieve a configuration key value for a given section.

    If key is ``None``, the whole section is returned as a dictionary.

    """
    try:
        subconfig = VORTEX_CONFIG[section]
    except KeyError:
        raise ConfigurationError(
            f"Missing configuration section {section}",
        )
    if not key:
        return subconfig

    try:
        value = subconfig[key]
    except KeyError:
        raise ConfigurationError(
            f"Missing configuration key {key} in section {section}",
        )
    return value


def set_config(section, key, value):
    """Set a configuration key to a value"""
    global VORTEX_CONFIG
    if section not in VORTEX_CONFIG.keys():
        VORTEX_CONFIG[section] = {}
    if key in VORTEX_CONFIG[section]:
        logger.warning(f"Updating existing configuration {section}:{key}")
    VORTEX_CONFIG[section][key] = value


def is_defined(section, key=None):
    """Return whether or not the key is defined for the section.

    If ``key`` is ``None``, return whether or not the section exists
    in the current configuration.

    """
    if section not in VORTEX_CONFIG.keys():
        return False
    if key:
        return key in VORTEX_CONFIG[section].keys()
    return True


def get_from_config_w_default(section, key, default):
    try:
        return from_config(section, key)
    except ConfigurationError:
        return default
