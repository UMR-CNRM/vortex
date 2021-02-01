# -*- coding:Utf-8 -*-

"""
This module contains "fake" storage tools for demonstration purposes.
"""

from vortex.tools.storage import MtoolCache, Archive
from vortex import sessions


class MtoolDemoCache(MtoolCache):
    """A MTOOL like cache for demo purposes.

    The cache will be located ``in ~/.vortexrc/democache``.
    """

    _footprint = dict(
        info = 'MTOOL like cache for demo purposes',
        attr = dict(
            kind = dict(
                values   = ['mtool-demo'],
            ),
        )
    )

    @property
    def entry(self):
        """Tries to figure out what could be the actual entry point for cache space."""
        sh = self.sh
        if self.rootdir == 'auto':
            e = self.sh.env
            if 'VORTEX_DEMO_CACHE_PARENTDIR' in e:
                sweethome = sh.path.join(e.VORTEX_DEMO_CACHE_PARENTDIR, 'democache')
            else:
                gl = sessions.current().glove
                sweethome = sh.path.join(gl.configrc, 'democache')
            sh.mkdir(sweethome)
        else:
            sweethome = self.actual_rootdir
        return sh.path.join(sweethome, self.actual_headdir)


class DemoArchive(Archive):
    """The default class to handle demo storage.

    The data are retrieved/stored in the ``examples/demoarchive`` subdirectory
    of the Vortex code package.
    """

    _footprint = dict(
        info = 'Demo archive description',
        attr = dict(
            inifile = dict(
                optional = True,
                default  = '@demoarchive-[storage].ini',
            ),
            storage = dict(
                optional = True,
                default  = 'localhost',
                values   = ['localhost', ]
            ),
            tube = dict(
                values   = ['demo', ],
            ),
        )
    )

    def __init__(self, *kargs, **kwargs):
        super(DemoArchive, self).__init__(*kargs, **kwargs)
        self._entry = None

    @property
    def entry(self):
        """Tries to figure out what could be the actual entry point for cache space."""
        if self._entry is None:
            gl = sessions.current().glove
            self._entry = self.sh.path.join(gl.siteroot, 'examples', 'demoarchive')
        return self._entry

    def _demo_actual_location(self, item):
        """Compute the fullpath within the demo repository."""
        return self.sh.path.join(self.entry, item)

    def _demofullpath(self, item, **kwargs):
        """Actual _fullpath."""
        rc = '{:s}:{:s}'.format(self.actual_storage, self._demo_actual_location(item))
        return rc, dict()

    def _demoprestageinfo(self, item, **kwargs):
        """Actual _prestageinfo."""
        baseinfo = dict(storage=self.actual_storage,
                        location=self._demo_actual_location(item))
        return baseinfo, dict()

    def _democheck(self, item, **kwargs):
        """Actual _check."""
        path = self._demo_actual_location(item)
        if path is None:
            return None, dict()
        try:
            st = self.sh.stat(path)
        except OSError:
            st = None
        return st, dict()

    def _demolist(self, item, **kwargs):
        """Actual _list using ftp."""
        path = self._demo_actual_location(item)
        if path is not None and self.sh.path.exists(path):
            if self.sh.path.isdir(path):
                return self.sh.listdir(path), dict()
            else:
                return True, dict()
        else:
            return None, dict()

    def _demoretrieve(self, item, local, **kwargs):
        """Actual _retrieve."""
        intent = kwargs.get("intent", "in")
        fmt = kwargs.get("fmt", "foo")
        silent = kwargs.get("silent", False)
        source = self._demo_actual_location(item)
        rc = self.sh.cp(source, local, intent=intent, fmt=fmt, silent=silent)
        return rc, dict(intent=intent, fmt=fmt)

    def _demoinsert(self, item, local, **kwargs):
        """Actual _insert using ftp."""
        intent = kwargs.get("intent", "in")
        fmt = kwargs.get("fmt", "foo")
        tpath = self._demo_actual_location(item)
        rc = self.sh.cp(local, tpath, intent=intent, fmt=fmt)
        return rc, dict(intent=intent, fmt=fmt)

    def _demodelete(self, item, **kwargs):
        """Actual _delete using ftp."""
        fmt = kwargs.get("fmt", "foo")
        tpath = self._demo_actual_location(item)
        rc = self.sh.rm(tpath, fmt=fmt)
        return rc, dict(fmt=fmt)
