#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

from collections import defaultdict

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.layout import contexts
from vortex.tools.env import Environment
from vortex.tools.systems import OSExtended


class Addon(footprints.FootprintBase):
    """Root class for any :class:`Addon` system subclasses."""

    _abstract  = True
    _collector = ('addon',)
    _footprint = dict(
        info = 'Default add-on',
        attr = dict(
            kind = dict(),
            sh = dict(
                type     = OSExtended,
                alias    = ('shell',),
                access   = 'rwx-weak',
            ),
            env = dict(
                type     = Environment,
                optional = True,
                default  = None,
                access   = 'rwx',
                doc_visibility = footprints.doc.visibility.ADVANCED
            ),
            cfginfo = dict(
                optional = True,
                default  = '[kind]',
                doc_visibility = footprints.doc.visibility.ADVANCED
            ),
            cmd = dict(
                optional = True,
                default  = None,
                access   = 'rwx',
            ),
            path = dict(
                optional = True,
                default  = None,
                access   = 'rwx',
            ),
            cycle = dict(
                optional = True,
                default  = None,
                access   = 'rwx',
            ),
            toolkind = dict(
                optional = True,
                default  = None
            ),
        )
    )

    def __init__(self, *args, **kw):
        """Abstract Addon initialisation."""
        logger.debug('Abstract Addon init %s', self.__class__)
        super(Addon, self).__init__(*args, **kw)
        self.sh.extend(self)
        self._context_cache = defaultdict(dict)
        if self.env is None:
            self.env = Environment(active=False, clear=True)
        clsenv = self.__class__.__dict__
        for k in [ x for x in clsenv.keys() if x.isupper() ]:
            self.env[k] = clsenv[k]
        if self.path is None:
            for prefix in [ x for x in (self.kind, self.cfginfo) if x is not None ]:
                kpath = prefix + 'path'
                if kpath in self.sh.env:
                    self.path = self.sh.env.get(kpath)
                    break
            if self.path is None and self.cfginfo is not None:
                tg = self.sh.default_target
                addon_rootdir = self.sh.env.get(
                    self.cfginfo + 'root',
                    tg.get(self.cfginfo + ':rootdir', None)
                )
                if self.cycle is None:
                    self.cycle = self.sh.env.get(
                        self.cfginfo + 'cycle',
                        tg.get(self.cfginfo + ':' + self.cfginfo + 'cycle')
                    )
                if addon_rootdir is not None and self.cycle is not None:
                    self.path = addon_rootdir + '/' + self.cycle

    @classmethod
    def in_shell(cls, shell):
        """Grep any active instance of that class in the specified shell."""
        lx = [x for x in shell.search if isinstance(x, cls)]
        return lx[0] if lx else None

    def _query_context(self):
        """Return the path and cmd for the current context.

        Results are cached so that the context's localtracker is explored only once.

        .. note:: We use the localtracker instead of the sequence because, in
            multistep jobs, the localtracker is preserved between steps. It's
            less elegant but it plays nice with MTOOL.
        """
        ctxtag = contexts.Context.tag_focus()
        if (ctxtag not in self._context_cache and self.toolkind is not None):
            ltrack = contexts.current().localtracker
            # NB: 'str' is important because local might be in unicode...
            candidates = [str(self.sh.path.realpath(local))
                          for local, entry in ltrack.iteritems()
                          if (entry.latest_rhdict('get').get('resource', dict()).get('kind', '') ==
                              self.toolkind)]
            if candidates:
                realpath = candidates.pop()
                self._context_cache[ctxtag] = dict(path=self.sh.path.dirname(realpath),
                                                   cmd=self.sh.path.basename(realpath))
        return self._context_cache[ctxtag]

    @property
    def actual_path(self):
        """The path that should be used in the current context."""
        infos = self._query_context()
        ctxpath = infos.get('path', None)
        return self.path if ctxpath is None else ctxpath

    @property
    def actual_cmd(self):
        """The cmd that should be used in the current context."""
        infos = self._query_context()
        ctxcmd = infos.get('cmd', None)
        return self.cmd if ctxcmd is None else ctxcmd

    def _spawn_commons(self, cmd, **kw):
        """Internal method setting local environment and calling standard shell spawn."""

        # Is there a need for an interpreter ?
        if 'interpreter' in kw:
            cmd.insert(0, kw.pop('interpreter'))

        # Overwrite global module env values with specific ones
        with self.sh.env.clone() as localenv:

            localenv.verbose(True, self.sh)
            localenv.update(self.env)

            # Check if a pipe is requested
            inpipe = kw.pop('inpipe', False)

            # Ask the attached shell to run the addon command
            if inpipe:
                kw.setdefault('stdout', True)
                rc = self.sh.popen(cmd, **kw)
            else:
                rc = self.sh.spawn(cmd, **kw)

        return rc

    def _spawn(self, cmd, **kw):
        """Internal method setting local environment and calling standard shell spawn."""

        # Insert the actual tool command as first argument
        cmd.insert(0, self.actual_cmd)
        if self.actual_path is not None:
            cmd[0] = self.actual_path + '/' + cmd[0]

        return self._spawn_commons(cmd, **kw)

    def _spawn_wrap(self, cmd, **kw):
        """Internal method setting local environment and calling standard shell spawn."""

        # Insert the tool path before the first argument
        if self.actual_path is not None:
            cmd[0] = self.actual_path + '/' + cmd[0]

        return self._spawn_commons(cmd, **kw)


class FtrawEnableAddon(Addon):
    """Root class for any :class:`Addon` system subclasses that needs to override rawftput."""

    _abstract  = True
    _footprint = dict(
        info = 'Default add-on with rawftput support.',
        attr = dict(
            rawftshell = dict(
                info     = "Path to ftserv's concatenation shell",
                optional = True,
                default  = None,
                access   = 'rwx',
                doc_visibility = footprints.doc.visibility.GURU,
            ),
        )
    )

    def __init__(self, *args, **kw):
        """Abstract Addon initialisation."""
        logger.debug('Abstract Addon init %s', self.__class__)
        super(FtrawEnableAddon, self).__init__(*args, **kw)
        # If needed, look in the config file for the rawftshell
        if self.rawftshell is None:
            tg = self.sh.default_target
            self.rawftshell = tg.get(self.cfginfo + ':rawftshell', None)
