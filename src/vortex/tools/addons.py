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
    """
    Root class for any :class:`Addon` system subclasses.
    """

    _abstract  = True
    _collector = ('addon',)
    _footprint = dict(
        info = 'Default add-on',
        attr = dict(
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

    @property
    def realkind(self):
        return 'addon'

    def _get_sh(self):
        return self._sh

    def _set_sh(self, value):
        self._sh = weakref.proxy(value)

    sh = property(_get_sh, _set_sh, None, None)

    @property
    def env(self):
        return self._env

    def _get_actual(self, item):
        try:
            actual_item = [a for a in self.attributes() if a.endswith('_' + item)][0]
        except IndexError:
            raise AttributeError('Could not find any ' + item + ' attribute in current addon')
        else:
            return getattr(self, actual_item)

    @property
    def cmd(self):
        return self._get_actual('cmd')

    @property
    def path(self):
        return self._get_actual('path')

    def _spawn(self, cmd, **kw):
        """Internal method setting local environment and calling standard shell spawn."""

        # Insert the actual tool command as first argument
        cmd.insert(0, self.cmd)
        if self.path is not None:
            cmd[0] = self.path + '/' + cmd[0]

        # Set global module env variable to a local environement object
        # activated temporarily for the curren spawned command.
        g = globals()
        localenv = self.sh.env.clone()
        for k in [ x for x in g.keys() if x.isupper() ]:
            localenv[k] = g[k]

        # Overwrite global module env values with specific ones
        localenv.update(self._env)

        # Check if a pipe is requested
        inpipe = kw.pop('pipe', False)

        # Ask the attached shell to run the addon command
        localenv.active(True)
        if inpipe:
            rc = self.sh.popen(cmd, **kw)
        else:
            rc = self.sh.spawn(cmd, **kw)
        localenv.active(False)
        return rc
