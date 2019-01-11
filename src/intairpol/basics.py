#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TODO: Module documentation
"""

from __future__ import absolute_import, print_function, division, unicode_literals

import footprints

import vortex
from vortex.syntax.stdattrs import DelayedEnvValue

from bronx.fancies import loggers
from bronx.fancies.fscrawler import upfirst
from bronx.stdtypes.date import now

logger = loggers.getLogger(__name__)

#: Recognition of package name
ALTNAMES = ('intairpol', 'airpol', 'airtools')


class AirTool(footprints.FootprintBase):

    _abstract  = True
    _collector = ('airtool',)
    _footprint = dict(
        info = 'Abstract Miscellaneous Tool from the intairpol package',
        attr = dict(
            kind = dict(),
            family = dict(),
            label = dict(
                optional = True,
                default  = 'default',
            ),
            stamp = dict(
                optional = True,
                default  = now().compact(),
            ),
            release = dict(
                optional = True,
                default  = 'oper',
            ),
            loglevel = dict(
                optional = True,
                default  = 'warning',
            ),
            verbose = dict(
                optional = True,
                type     = bool,
                default  = False,
            ),
            rootpath = dict(
                optional = True,
                default  = DelayedEnvValue('INTAIRPOL_ROOT_PATH', vortex.sh().pwd()),
            ),
            cfgpath = dict(
                optional = True,
                default  = '[rootpath]/conf',
            ),
            cfgfile = dict(
                optional = True,
                default  = '[family]-conf.json',
            ),
            workdir = dict(
                optional = True,
                default  = DelayedEnvValue('INTAIRPOL_WORK_PATH', vortex.sh().pwd()),
            ),
            bkup_path = dict(
                optional = True,
                default  = DelayedEnvValue('INTAIRPOL_BKUP_PATH', upfirst('bkup') or vortex.sh().env['HOME'] + '/bkup'),
            ),
        )
    )

    def __init__(self, *args, **kw):
        """Setup actual cfg file."""
        super(AirTool, self).__init__(*args, **kw)
        self._actualcfg = None
        logger.info('Set <loglevel:%s>', self.loglevel)
        self.ticket.setloglevel(self.loglevel)
        logger.debug('Raw options %s', self.footprint_as_dict())
        if self.verbose:
            self.sh.trace = True
        self.config = self.sh.blind_load(self.actualcfg)

    @property
    def realkind(self):
        return 'airtool'

    @property
    def ticket(self):
        return vortex.ticket()

    @property
    def sh(self):
        return self.ticket.sh

    @property
    def env(self):
        return self.ticket.env

    def get_family_tag(self):
        return self.family

    @property
    def xtag(self):
        return '-'.join((self.kind, self.stamp, self.get_family_tag(), self.release, self.label))

    @property
    def actualcfg(self):
        if self._actualcfg is None:
            if self.sh.path.isdir(self.cfgpath):
                self._actualcfg  = self.sh.path.join(self.cfgpath, self.cfgfile)
            else:
                self._actualcfg = self.sh.abspath(self.cfgfile)
        return self._actualcfg
