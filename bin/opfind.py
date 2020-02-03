#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TODO: Binary documentation.
"""

from __future__ import absolute_import, print_function, unicode_literals, division

import locale
import sys

locale.setlocale(locale.LC_ALL, os.environ.get('VORTEX_DEFAULT_ENCODING', str('en_US.UTF-8')))

# Let's use standard footprints logging facilities
import footprints
footprints.setup.extended = True
logger = footprints.loggers.getLogger(__name__)

# A proper path should be defined in PYTHONPATH
import vortex
import gco.tools.diggers

# Meteo modules
import common
from common.util import usepygram
import olive
import iga

from bronx.stdtypes import date
from bronx.fancies.arguments import CfgMeteoArgumentParser
from bronx.fancies.colors import termcolors
from bronx.fancies.dispatch import ExtendedCmdLiner
from bronx.fancies.wrapcmd import WrapCmdLineArgs
import bronx.fancies.multicfg

t = vortex.ticket()
t.setloglevel('warning')


FULL_OPTS = ('xdate', 'model', 'cutoff', 'term', 'notterm', 'location', 'step', 'suite', 'kind', 'namespace')


class OpFindArgs(CfgMeteoArgumentParser):
    """TODO: Class documentation."""

    _footprint = dict(
        priority = dict(
            level = footprints.priorities.top.TOOLBOX,
        ),
    )

    def refine_defined_cfgroot(self):
        """Set site conf directory as default."""
        return dict(
            default=t.glove.siteconf,
        )

    def refine_defined_xdate(self):
        """Set the last synoptic hour as default, UTC."""
        return dict(
            default=date.lastround(base=date.utcnow(), rh=3).ymdhm,
        )

    def add_defined_notterm(self):
        """Terms that should be excluded from the selection."""
        return dict(
            options='--notterm',
            help='Discarded terms',
            metavar='terms',
            default=None,
            callback=self.mktimelist,
        )

    def add_defined_location(self):
        """Location of the expected resources (e.g.: archive or inline)."""
        return dict(
            options='--location',
            help='Nickname for location providers',
            metavar='location-name',
            nargs='+',
            choices=('disk', 'arch'),
            default=['disk', 'arch'],
            callback=self.mktuple,
        )

    def add_defined_check(self):
        """Actually check the physical availability of the expected resource."""
        return dict(
            options='--check',
            help='Activate effective check of files',
            action='store_true',
        )


class OpFindCmd(ExtendedCmdLiner):
    """TODO: Class documentation."""

    @WrapCmdLineArgs('cfgname', 'cfgtag', 'cfgdir', 'cfgroot', 'cfgfile', 'suite', 'loglevel')
    def do_setcfg(self, **opts):
        """
        Defines a new basis for configuration files inquiry.
        Default cfgname : optables
        Default cfgtag  : None
        """
        if opts['cfgtag'] is None:
            opts['cfgtag'] = opts['suite']
        opts.pop('loglevel')
        opts.pop('suite')
        self.setcfg(**opts)

    @WrapCmdLineArgs('mine', 'loglevel')
    def do_setjob(self, **opts):
        """
        Defines a auxilary op digger.
        Default mine : op
        """
        opts.pop('loglevel')
        self.setjob(**opts)

    @WrapCmdLineArgs(strict=True)
    def do_maxterm(self, **opts):
        """Return maximum time value for exploration depth."""
        self.stdlog(self.cfg.maxterm)

    @WrapCmdLineArgs('discard', 'grep')
    def do_models(self, **opts):
        """Return defined models in current configuration."""
        self.stdlog(self.nicelist(self.cfg.models(), **opts))

    @WrapCmdLineArgs('discard', 'grep')
    def do_vapps(self, **opts):
        """Return defined vortex apps in current configuration."""
        self.stdlog(self.nicelist(self.cfg.vapps(), **opts))

    @WrapCmdLineArgs('discard', 'grep')
    def do_cutoffs(self, **opts):
        """Return defined cutoffs in current configuration."""
        self.stdlog(self.nicelist(self.cfg.cutoffs(), **opts))

    @WrapCmdLineArgs('discard', 'grep')
    def do_locations(self, **opts):
        """Return defined locations in current configuration."""
        self.stdlog(self.nicelist(self.cfg.locations(), **opts))

    @WrapCmdLineArgs(FULL_OPTS, strict=True)
    def do_candidates(self, **opts):
        """
        Return expected candidates for the specified resource as a nice dump.
        Default kind : historic
        Default namespace : None
        """
        self.stdlog(footprints.dump.fulldump(self.job.candidates(**opts)))

    @WrapCmdLineArgs(FULL_OPTS, 'datacheck', 'check', strict=True)
    def do_lookup(self, **opts):
        """
        Give a look to the expected candidates for the specified resource.
        Default kind : historic
        Default namespace : None
        Default datacheck : False
        """
        self.stdlog(self.job.lookup(**opts), raw=True)

    @WrapCmdLineArgs(FULL_OPTS, 'datacheck', strict=True)
    def do_best(self, **opts):
        """
        Return the best candidate for the specified resource as a nice dump.
        Default kind : historic
        Default namespace : None
        Default datacheck : None
        """
        for d, v in self.job.best(**opts).items():
            self.stdlog(termcolors.critical('  * ' + d), raw=True)
            self.stdlog('    Real term   :', termcolors.ok(v['term']), raw=True)
            self.stdlog('    Description :', termcolors.warning(v['description']), raw=True)
            self.stdlog(v['handler'].idcard(indent=4), raw=True)

    @WrapCmdLineArgs(FULL_OPTS, '-term', '+xterm', 'datacheck', 'check', strict=True)
    def do_ontime(self, **opts):
        """
        Give a look to the expected candidates for the specified resource.
        Default kind : historic
        Default namespace : None
        Default datacheck : False
        """
        self.stdlog(self.job.ontime(**opts), raw=True)


if __name__ == "__main__":

    todo = OpFindCmd(name='opfind', prompt='opdigger')

    if len(sys.argv) > 1:
        todo.onecmd('setcfg ' + ' '.join(sys.argv[2:]))
        todo.onecmd('setjob ' + ' '.join(sys.argv[2:]))
        todo.onecmd(' '.join(sys.argv[1:]))
        todo.onecmd('quit')
    else:
        todo.onecmd('setcfg')
        todo.onecmd('setjob')
        todo.cmdloop()
