#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re

from vortex.tools import date

from .ifsroot import IFSParallel


class Coupling(IFSParallel):
    """Coupling for IFS-like LAM Models."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'coupling' ],
            ),
            xpname = dict(
                default = 'FPOS'
            ),
            conf = dict(
                default = 1,
            )
        )
    )

    @property
    def realkind(self):
        return 'coupling'

    def prepare(self, rh, opts):
        """Default pre-link for climatological files"""
        super(Coupling, self).prepare(rh, opts)
        namrh = self.setlink(initrole='Namelist', initkind='namelist', initname='fort.4')
        for nam in [ x for x in namrh if 'NAMFPC' in x.contents ]:
            self.system.stderr(['Substitute "AREA" to CFPDOM namelist entry'])
            nam.contents['NAMFPC']['CFPDOM'] = 'AREA'
            nam.save()

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""
        cplrh = [ x.rh for x in self.context.sequence.effective_inputs(
            role = ('InitialCondition', 'CouplingSource'),
            kind = 'historic'
        ) ]
        cplrh.sort(lambda a, b: cmp(a.resource.term, b.resource.term))
        for r in cplrh:
            self.system.title('Loop on {0:s}'.format(str(r.resource)))

            # Set a local storage place
            runstore = 'RUNOUT' + r.resource.term.fmtraw
            self.system.mkdir(runstore)

            # Find out actual monthly climatological resource
            actualmonth = date.Month(r.resource.date + r.resource.term)

            def checkmonth(actualrh):
                return bool(actualrh.resource.month == actualmonth)
            self.system.remove('Const.Clim')
            self.setlink(initrole='GlobalClim', initkind='clim_model',
                         initname='Const.Clim', inittest=checkmonth)
            self.system.remove('const.clim.AREA')
            self.setlink(initrole='LocalClim', initkind='clim_model',
                         initname='const.clim.AREA', inittest=checkmonth)

            # Finaly set the actual init file
            self.system.remove('ICMSHFPOSINIT')
            self.system.softlink(r.container.localpath(), 'ICMSHFPOSINIT')

            # Standard execution
            super(Coupling, self).execute(rh, opts)

            # Freeze the current output
            for posfile in [ x for x in self.system.glob('PFFPOSAREA+*')
                             if re.match(r'PFFPOSAREA\+\d+(?:\d+)$', x) ]:
                self.system.move(
                    posfile,
                    self.system.path.join(runstore, 'CPLOUT+' + r.resource.term.fmthm)
                )
            for logfile in self.system.glob('NODE.*', 'std*'):
                self.system.move(logfile, self.system.path.join(runstore, logfile))

            # Some cleaning
            self.system.rmall('PXFPOS*', 'ncf927', 'dirlst')

    def postfix(self, rh, opts):
        """Post coupling cleaning."""
        super(Coupling, self).postfix(rh, opts)
        self.system.mvglob('RUNOUT*/CPLOUT*', '.')
        self.system.cat('RUNOUT*/NODE.001_01', output='NODE.all')
        self.system.dir(output=False)

