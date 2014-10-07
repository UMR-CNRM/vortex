#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []


import weakref

import footprints

from vortex.autolog import logdefault as logger
from vortex.tools.env import Environment
from vortex.tools.systems import System


class Addon(footprints.FootprintBase):
    """Root class for any :class:`Addon` system subclasses."""

    _abstract  = True
    _collector = ('addon',)
    _footprint = dict(
        info = 'Default add-on',
        attr = dict(
            kind = dict(),
            sh = dict(
                type = System,
                alias = ('shell',),
                access = 'rwx-weak',
            ),
            env = dict(
                type = Environment,
                optional = True,
                default = None,
                access = 'rwx',
            ),
            cfginfo = dict(
                optional = True,
                default = '[kind]',
            ),
            cmd = dict(
                optional = True,
                default = None,
                access = 'rwx',
            ),
            path = dict(
                optional = True,
                default = None,
                access = 'rwx',
            )
        )
    )

    def __init__(self, *args, **kw):
        """Abstract Addon initialisation."""
        logger.debug('Abstract Addon init %s', self.__class__)
        super(Addon, self).__init__(*args, **kw)
        self.sh.extend(self)
        if self.env is None:
            self.env = Environment(active=False, clear=True)
        clsenv = self.__class__.__dict__
        for k in [ x for x in clsenv.keys() if x.isupper() ]:
            self.env[k] = clsenv[k]
        if self.path is None and self.cfginfo is not None:
            kpath = self.kind + 'path'
            if kpath in self.sh.env:
                self.path = self.sh.env.get(kpath)
            else:
                tg = self.sh.target()
                addon_rootdir = tg.get(self.cfginfo + ':rootdir', None)
                addon_opcycle = self.sh.env.get(
                    self.cfginfo + 'cycle',
                    tg.get(self.cfginfo + ':' + self.cfginfo + 'cycle')
                )
                if addon_rootdir and addon_opcycle:
                    self.path = addon_rootdir + '/' + addon_opcycle

    @property
    def realkind(self):
        return 'addon'

    @classmethod
    def in_shell(cls, shell):
        """Grep any active instance of that class in the specified shell."""
        lx = [x for x in shell.search if isinstance(x, cls)]
        return lx[0] if lx else None

    def _spawn(self, cmd, **kw):
        """Internal method setting local environment and calling standard shell spawn."""

        # Insert the actual tool command as first argument
        cmd.insert(0, self.cmd)
        if self.path is not None:
            cmd[0] = self.path + '/' + cmd[0]

        # Overwrite global module env values with specific ones
        localenv = self.sh.env.clone()
        localenv.active(True)
        localenv.verbose(True, self.sh)
        localenv.update(self.env)

        # Check if a pipe is requested
        inpipe = kw.pop('pipe', False)

        # Ask the attached shell to run the addon command
        if inpipe:
            rc = self.sh.popen(cmd, **kw)
        else:
            rc = self.sh.spawn(cmd, **kw)
        localenv.active(False)
        return rc
