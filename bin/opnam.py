#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals, division

import locale
import sys
import argparse

locale.setlocale(locale.LC_ALL, os.environ.get('VORTEX_DEFAULT_ENCODING', str('en_US.UTF-8')))

# Let's use standard footprints logging facilities
import footprints
footprints.setup.extended = True
logger = footprints.loggers.getLogger(__name__)

# A proper path should be defined in PYTHONPATH
import vortex
import gco.tools.diggers

# Meteo stuf
import common

from bronx.stdtypes import date
from bronx.fancies.arguments import CfgMeteoArgumentParser
from bronx.fancies.colors import termcolors
import bronx.fancies.multicfg

t  = vortex.ticket()
t.setloglevel('warning')


class OpNamArgs(CfgMeteoArgumentParser):

    _footprint = dict(
        priority = dict(
            level = footprints.priorities.top.TOOLBOX,
        ),
    )

    def refine_defined_cfgroot(self):
        return dict(
            default = t.glove.siteconf,
        )


from bronx.fancies.wrapcmd import WrapCmdLineArgs
from bronx.fancies.dispatch import ExtendedCmdLiner

FULL_OPTS = ('xdate', 'model', 'cutoff', 'term', 'notterm', 'location', 'step', 'suite', 'kind', 'namespace')


class OpNamCmd(ExtendedCmdLiner):

    @WrapCmdLineArgs('cfgname', 'cfgtag', 'cfgdir', 'cfgroot', 'cfgfile', 'suite', 'loglevel')
    def do_setcfg(self, **opts):
        """
        Defines a new basis for configuration files inquiry.
        Default cfgname : opnam
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
        Default mine : namelist
        """
        opts.pop('loglevel')
        self.setjob(**opts)

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

    @WrapCmdLineArgs('model', 'kind', '+remote', 'filename', 'incore', 'term')
    def do_load(self, **opts):
        """
        Load a namelist.
        Default model : arpege
        Default incore : True
        Default kind : None
        Default term : 0
        """
        if opts['kind'] is None and 'select' in opts['remote']:
            opts['kind'] = 'namselect'
        if opts['kind'] is None and 'fp' in opts['remote']:
                opts['kind'] = 'namelistfp'
        if opts['kind'] is None:
            opts['kind'] = 'namelist'
        self.stdlog(self.job.load( **opts))

    @WrapCmdLineArgs()
    def do_cat(self, **opts):
        """
        Select domains names.
        """
        self.stdlog(self.job.cat(**opts))

    @WrapCmdLineArgs('discard', 'grep')
    def do_blocks(self, **opts):
        """
        Display names of blocks defined in the current namelist.
        """
        self.stdlog(self.nicelist(self.job.blocks(), **opts))

    @WrapCmdLineArgs('discard', 'grep')
    def do_domains(self, **opts):
        """
        Select domains names.
        """
        self.stdlog(self.nicelist(self.job.domains, **opts))

    @WrapCmdLineArgs('discard', 'grep', 'only')
    def do_setdom(self, **opts):
        """
        Select domains names.
        """
        opts.pop('report')
        self.job.set_domains(**opts)
        self.stdlog(self.nicelist(self.job.domains, **opts))

    @WrapCmdLineArgs(strict=True)
    def do_save(self, **opts):
        """
        Save actual state of the namelist.
        """
        self.stdlog(self.job.save())


if __name__ == "__main__":

    todo = OpNamCmd(name='opnam')

    if len(sys.argv) > 1:
        todo.onecmd('setcfg ' + ' '.join(sys.argv[2:]))
        todo.onecmd('setjob ' + ' '.join(sys.argv[2:]))
        todo.onecmd(' '.join(sys.argv[1:]))
        todo.onecmd('quit')
    else:
        todo.onecmd('setcfg')
        todo.onecmd('setjob')
        todo.cmdloop()
