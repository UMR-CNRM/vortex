#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Common interest classes to help setup the RTTOV/IFS environment.
"""

from __future__ import print_function, absolute_import, division, unicode_literals

import re

from bronx.fancies import loggers

from vortex.algo.components import AlgoComponentDecoMixin, algo_component_deco_mixin_autodoc

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


@algo_component_deco_mixin_autodoc
class SatRadDecoMixin(AlgoComponentDecoMixin):
    """RTTOV settings + Satellites related stuffs.

    This mixin class is intended to be used with AlgoComponnent classes. It will
    automatically set up the path to RTTOV coefficient files
    (:meth:`_satrad_coeffdir_setup`).

    In addition it provides the :meth:`setchannels` utility method (that have to
    be called manually if needed).
    """

    def _satrad_coeffdir_setup(self, rh, opts):  # @UnusedVariable
        """Look for RTTOV coefficient files and act on it."""
        rtcoefs = self.context.sequence.effective_inputs(role='RtCoef', kind='rtcoef')
        if rtcoefs:
            sh = self.system
            rtpath = sh.path.dirname(sh.path.realpath(rtcoefs[0].rh.container.localpath()))
            logger.info('Setting %s = %s', 'RTTOV_COEFDIR', rtpath)
            self.env['RTTOV_COEFDIR'] = rtpath

    _MIXIN_PREPARE_HOOKS = (_satrad_coeffdir_setup, )

    def setchannels(self):
        """Look up for channels namelists in effective inputs."""
        namchan = [
            x.rh for x in self.context.sequence.effective_inputs(kind = 'namelist')
            if 'channel' in x.rh.options
        ]
        for thisnam in namchan:
            thisloc = re.sub(r'\d+$', '', thisnam.options['channel']) + 'channels'
            if thisloc != thisnam.container.localpath():
                logger.info('Linking < %s > to < %s >', thisnam.container.localpath(), thisloc)
                self.system.softlink(thisnam.container.localpath(), thisloc)
