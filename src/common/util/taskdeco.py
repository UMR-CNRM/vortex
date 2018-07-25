#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A collection of Tasks decorators.
"""

from __future__ import print_function, absolute_import, division, unicode_literals

import footprints
from vortex import toolbox

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


def process_needs_lfi_stuff(cls):
    """Decorator for Task: get LFI stuff before calling process."""
    original_process = getattr(cls, 'process', None)
    if original_process is not None:
        def process(self, *args, **kwargs):
            _get_lfi_stuff(self)
            original_process(self, *args, **kwargs)
        process.__doc__ = original_process.__doc__
        cls.process = process
        return cls


def _get_lfi_stuff(self):
    """Get LFI stuff."""
    if 'early-fetch' in self.steps or 'fetch' in self.steps:
        self.sh.title('Toolbox input tblfiscripts')
        tblfiscripts = toolbox.input(role='LFIScripts',
                                     genv=self.conf.cycle,
                                     kind='lfiscripts',
                                     local='usualtools/tools.lfi.tgz'
                                     )
        self.sh.title('Toolbox input tbiopoll')
        tblfitools = toolbox.input(role='IOPoll',
                                   format='unknown',
                                   genv=self.conf.cycle,
                                   kind='iopoll',
                                   language='perl',
                                   local='usualtools/io_poll',
                                   )
        self.sh.title('Toolbox input tblfitools')
        tblfitools = toolbox.input(role='LFITOOLS',
                                   genv=self.conf.cycle,
                                   kind='lfitools',
                                   local='usualtools/lfitools'
                                   )
