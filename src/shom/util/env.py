"""
Utilities about the environment.
"""

import sys


def config_to_env_vars(cfg):
    """Extract from a ConfigSet options that starts with `env_`."""
    env_vars = {}
    for key, value in cfg.items():
        if key.startswith("env_"):
            key = key[4:].upper()
            if isinstance(value, list):
                value = ','.join(value)
            env_vars[key] = value
    return env_vars


def stripout_conda_env(t, env_dict=None):
    """Remove conda env from PATH, LD_LIBRARY_PATH and C_INCLUDE_PATH."""
    if env_dict is None:
        env_dict = t.sh.environ
    for name, subdir in (
            ("PATH", "bin"),
            ("LD_LIBRARY_PATH", "lib"),
            ("LIBRARY_PATH", "lib"),
            ("INCLUDE_PATH", "include"),
            ("C_INCLUDE_PATH", "include")):
        if name in env_dict:
            paths = env_dict[name].split(':')
            path = t.sh.path.join(sys.prefix, subdir)
            if path in paths:
                paths.remove(path)
            env_dict[name] = ":".join(paths)
