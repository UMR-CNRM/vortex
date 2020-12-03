#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilities about configurations
"""


def config_to_env_vars(cfg):
    """Extract from a ConfigSet options that starts with `env_`"""
    env_vars = {}
    for key, value in cfg.items():
        if key.startswith("env_"):
            key = key[4:].upper()
            if isinstance(value, list):
                value = ','.join(value)
            env_vars[key] = value
    return env_vars
