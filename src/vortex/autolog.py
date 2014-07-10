#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Fake module for automatic import of a logger.

#: No automatic export
__all__ = []

import logging

logdefault = logging.getLogger()


def logmodule(modname):
    return logging.getLogger(modname)
