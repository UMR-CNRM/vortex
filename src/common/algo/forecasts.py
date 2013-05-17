#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []


from vortex.autolog import logdefault as logger

from vortex.algo.components import Parallel


class IFSModelParallel(Parallel):
    """Abstract IFSModel parallel algo components."""

    _abstract = True
    _footprint = dict(
        attr = dict(
            conf = dict(
                optional = True,
            ),
            timescheme = dict(
                optional = True,
                default = 'sli',
                values = [ 'eul', 'eulerian', 'sli', 'semilag' ],
                remap = dict(
                    eulerian = 'eul',
                    semilag = 'sli'
                )
            ),
            timestep = dict(
                optional = True,
                default = 600,
                type = int
            ),
            fcterm = dict(
                optional = True,
                default = 0,
                type = int
            ),
            fcunit = dict(
                optional = True,
                default = 'h',
                values = [ 'h', 'hour', 't', 'step' ],
                remap = dict(
                    hour = 'h',
                    step = 't'
                )
            ),
            xpname = dict(
                optional = True,
                default = 'XPVT'
            )
        )
    )

    def valid_executable(self, rh):
        try:
            return bool(rh.resource.realkind == 'ifsmodel')
        except:
            return False

    def spawn_command_options(self):
        return dict(
            name       = (self.xpname + 'xxxx')[:4].upper(),
            timescheme = self.timescheme,
            timestep   = self.timestep,
            fcterm     = self.fcterm,
            fcunit     = self.fcunit,
        )


class Forecast(IFSModelParallel):
    """Forecast for IFS-like Models."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'forecast', 'fc' ],
                remap = dict( forecast = 'fc' )
            ),
            xpname = dict(
                default = 'FCST'
            ),
            conf = dict(
                default = 1,
            )
        )
    )

    def prepare(self, rh, ctx, opts):
        """Default pre-link for the initial condition file"""
        initrole = 'InitialCondition'
        initname = 'ICMSH{0:s}INIT'.format(self.xpname)
        initrh = [x.rh for x in ctx.sequence.effective_inputs(role=initrole)]
        if not initrh:
            logger.warning('Could not find logical %s - assuming already renamed', initrole)
        if len(initrh) > 1:
            logger.warning('More than one %s - using the first one', initrole)
        for l in [x.container.localpath() for x in initrh]:
            if not self.system.path.exists(initname):
                self.system.symlink(l, initname)


class LAMForecast(Forecast):
    """Forecast for IFS-like Limited Area Models."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'fclam' ],
            ),
        )
    )

    def spawn_command_options(self):
        return dict(
            name       = (self.xpname+'xxxx')[:4].upper(),
            timescheme = self.timescheme,
            timestep   = self.timestep,
            fcterm     = self.fcterm,
            fcunit     = self.fcunit,
            model      = 'aladin',
        )

    def prepare(self, rh, ctx, opts):
        """Default pre-link for boundary conditions files."""
        cplrh = [ x.rh for x in ctx.sequence.effective_inputs(role='BoundaryCondition', kind='elscf') ]
        cplrh.sort(lambda a, b: cmp(a.resource.term, b.resource.term))
        llocal = [x.container.localpath() for x in cplrh]

        i = 0
        for l in llocal:
            self.system.symlink(l, 'ELSCF{0:s}ALBC{1:03d}'.format(self.xpname, i))
            i=i+1

        # Default pre-link for the initial condition file
        initname = 'ICMSH{0:s}INIT'.format(self.xpname)
        initrh = [x.rh for x in ctx.sequence.effective_inputs(role='InitialCondition')]
        for l in [x.container.localpath() for x in initrh]:
            self.system.symlink(l,initname)


class DFIForecast(LAMForecast):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'fcdfi' ],
            ),
        )
    )

    def prepare(self, rh, ctx, opts):
        """Default pre-link for the initial condition file."""
        initname = 'ICMSH{0:s}INIT'.format(self.xpname)
        initrh =  [x.rh for x in ctx.sequence.effective_inputs(role='InitialCondition')]
        for l in [x.container.localpath() for x in initrh]:
            self.system.symlink(l, initname)

        # Pre-link boundary conditions as special DFI files
        for pseudoterm in (999, 0, 1):
            self.system.symlink(initname, 'ELSCF{0:s}ALBC{1:03d}'.format(self.xpname, pseudoterm))
