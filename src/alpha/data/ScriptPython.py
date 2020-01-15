#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers

from vortex.data.executables import Script, BlackBox

import iga.util.bpnames as bp

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)

class ScriptPython(Script):

    _footprint = dict (
        attr = dict(
            kind = dict(values = ['script_python']),

        )
    )
    
    def command_line(self, **kw):
	return kw['command_line']



