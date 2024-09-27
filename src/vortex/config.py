import tomli


VORTEX_CONFIG = None


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
