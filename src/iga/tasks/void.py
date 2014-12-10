#!/usr/bin/env python
# -*- coding:Utf-8 -*-

__all__ = []

from iga.tools.apps import OpTask


def setup(t, verbose=False):
    return [ Application(t, tag='void') ]


def broadcast(t, **kw):
    """Fake function... just not to forget."""
    t.env.update(
        ARPEGE_CYCLE='cy38t1_op1.14',
        AROME_CYCLE='al38t1_arome-op1.09',
    )
