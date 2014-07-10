#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []


from vortex.autolog import logdefault as logger

from vortex.algo.components import Parallel


class IFSParallel(Parallel):
    """Abstract IFSModel parallel algo components."""

    _abstract = True
    _footprint = dict(
        attr = dict(
            kind = dict(
                default = 'ifsrun',
            ),
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
                default = 600.,
                type = float
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

    def fstag(self):
        """Extend default tag with ``kind`` value."""
        return super(IFSParallel, self).fstag() + '.' + self.kind

    def valid_executable(self, rh):
        """Be sure that the specifed executable is ifsmodel compatible."""
        try:
            return bool(rh.resource.realkind == 'ifsmodel')
        except:
            return False

    def spawn_hook(self):
        """Usually a good habit to dump the fort.4 namelist."""
        super(IFSParallel, self).spawn_hook()
        if self.system.path.exists('fort.4'):
            self.system.subtitle('{0:s} : dump namelist <fort.4>'.format(self.realkind))
            self.system.cat('fort.4', output=False)

    def spawn_command_options(self):
        """Dictionary provided for command line factory."""
        return dict(
            name       = (self.xpname + 'xxxx')[:4].upper(),
            timescheme = self.timescheme,
            timestep   = self.timestep,
            fcterm     = self.fcterm,
            fcunit     = self.fcunit,
        )

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(IFSParallel, self).prepare(rh, opts)
        for optpack in ('drhook', 'gribapi'):
            self.export(optpack)

    def setlink(self, initrole=None, initkind=None, initname=None, inittest=lambda x: True):
        """Set a symbolic link for actual resource playing defined role."""
        initrh = [ x.rh for x in self.context.sequence.effective_inputs(role=initrole, kind=initkind) if inittest(x.rh) ]
        if not initrh:
            logger.warning('Could not find logical role %s with kind %s - assuming already renamed', initrole, initkind)
        if len(initrh) > 1:
            logger.warning('More than one role %s with kind %s %s', initrole, initkind, initrh)
        if initname != None:
            for l in [ x.container.localpath() for x in initrh ]:
                if not self.system.path.exists(initname):
                    self.system.symlink(l, initname)
                    break
        return initrh

    def execute(self, rh, opts):
        """Standard IFS-Like execution parallel execution."""
        self.system.ls(output='dirlst')
        super(IFSParallel, self).execute(rh, opts)

