import tomli

from bronx.fancies import loggers


VORTEX_CONFIG = {}

logger = loggers.getLogger(__name__)


def load_config(configpath="vortex.toml"):
    global VORTEX_CONFIG
    try:
        with open(configpath, "rb") as f:
             VORTEX_CONFIG = tomli.load(f)
        print(f"Successfully read configuration file {configpath}")
    except FileNotFoundError:
        print(
            f"Could not read configuration file {configpath}"
            " (not found)."
        )
        print(
            "Use load_config(/path/to/config) to update the configuration"
        )


def print_config():
    if VORTEX_CONFIG:
        for k, v in VORTEX_CONFIG:
            print(k.upper(), v)


def from_config(section, key=None):
    try:
        subconfig = VORTEX_CONFIG[section]
    except KeyError as e:
        print(f"Could not find section {section} in configuration")
        raise(e)

    if not key:
        return subconfig

    try:
        value = subconfig[key]
    except KeyError as e :
        print(f"Could not find key {key} in section {section} of configuration")
        raise(e)
    return value


def set_config(section, key, value):
    global VORTEX_CONFIG
    if section not in VORTEX_CONFIG.keys():
        VORTEX_CONFIG[section] = {}
    if key in VORTEX_CONFIG[section]:
        logger.warning(
            f"Updating existing configuration {section}:{key}"
        )
    VORTEX_CONFIG[section][key] = value


def is_defined(section, key=None):
    if section not in VORTEX_CONFIG.keys():
        return False
    if key:
        return key in VORTEX_CONFIG[section].keys()
    return True


def get_from_config_w_default(section, key, default):
    logger.info(f"Reading config value {section}.{key}")
    try:
        return from_config(section, key)
    except KeyError:
        return default
