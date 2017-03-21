#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from operator import attrgetter

#: Automatic export off
__all__ = []


import footprints
logger = footprints.loggers.getLogger(__name__)

from common.algo.ifsroot import IFSParallel


class CovB(IFSParallel):
    """Operations around the background error covariance matrix."""

    _footprint = dict(
        info='Operations around the background error covariance matrix',
        attr=dict(
            kind=dict(
                values=['covb', 'infl_factor', 'infl', 'mean', 'pert', 'femars'],
            ),
            nbmember = dict(
                type = int,
                optional = True,
            ),
            rawfiles = dict(
                type = bool,
                optional = True,
                default = False,
            ),
            nblag = dict(
                type = int,
                optional = True,
            ),
        )
    )

    def prepare_namelist_delta(self, rh, namcontents, namlocal):
        nam_updated = super(CovB, self).prepare_namelist_delta(rh, namcontents, namlocal)
        if self.nbmember is not None:
            namcontents.setmacro('NBE', self.nbmember)
            logger.info('Setup macro NBE=%s in %s', self.nbmember, namlocal)
            nam_updated = True
        if self.nblag is not None:
            namcontents.setmacro('NRESX', self.nblag)
            logger.info('Setup macro NRESX=%s in %s', self.nblag, namlocal)
            nam_updated = True
        return nam_updated

    def prepare(self, rh, opts):
        """Default pre-link for the initial condition file"""
        super(CovB, self).prepare(rh, opts)

        for num, sec in enumerate(sorted(self.context.sequence.effective_inputs(role = 'Rawfiles'),
                                         key = attrgetter('rh.resource.date', 'rh.provider.member')), start = 1):
            repname = sec.rh.container.localpath()
            radical = repname.split('_')[0] + '_D{:03d}_L{:s}'
            for filename in self.system.listdir(repname):
                level = re.search('_L(\d+)$', filename)
                if level is not None:
                    self.system.softlink(self.system.path.join(repname, filename), radical.format(num, level.group(1)))

    def postfix(self, rh, opts):
        """Find out if any special resources have been produced."""

        sh = self.system
        # Gather rawfiles in folders
        if self.rawfiles:
            flist = sh.glob('tmprawfile_D000_L*')
            dest = 'rawfiles'
            logger.info('Creating a rawfiles pack: %s', dest)
            sh.mkdir(dest)
            for fic in flist:
                sh.mv(fic, dest, fmt='grib')

        super(CovB, self).postfix(rh, opts)
