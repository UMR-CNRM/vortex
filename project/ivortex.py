# -*- coding: utf-8 -*-
from __future__ import print_function

import atexit
import importlib
import logging
import os
import shlex
import shutil
import sys
import tempfile

from IPython.core.magic import (Magics, magics_class, line_magic)

#: No automatic export
__all__ = []

#: The list of addons to be loaded
_IVORTEX_ADDONS = [('vortex.tools.folder', ('allfolders',)),
                   ('vortex.tools.grib', ('grib', )),
                   ('common.tools.gribdiff', ('gribapi', )),
                   ('vortex.tools.listings', ('arpifs_listings', )), ]
#: The path to the default basedir
_IVORTEX_BASEDIR_DEFAULT = os.path.join(os.environ.get('HOME', '/tmp'),
                                        'vortex-workdir')


@magics_class
class VortexMagics(Magics):
    """Provides the %vortex magic to an IPython shell."""

    def __init__(self, shell):
        """Compute the _basedir and initialise things."""
        super(VortexMagics, self).__init__(shell)
        self._basedir = os.environ.get('IVORTEX_BASEDIR', _IVORTEX_BASEDIR_DEFAULT)
        self._shell = shell
        self._rundir = None
        self._session = None
        self._version = None

    @staticmethod
    def _load_addons(fpx, sh, module, addons):
        """Internal: load a given module and the associated addons."""
        importlib.import_module(module)
        fpx.addons.non_ambiguous_loglevel = logging.DEBUG
        for addon in addons:
            fpx.addon(kind=addon, shell=sh, verboseload=False)

    @line_magic
    def vortex(self, line):
        """Called by the %vortex magic: it redirects the request to the appropriate methods."""
        if line:
            # The first element on the command line gives the action to perform
            line_list = shlex.split(line)
            cmd = line_list.pop(0)
            # If the appropriate method exists, call it
            if hasattr(self, '_vortex_' + cmd):
                return getattr(self, '_vortex_' + cmd)(line_list)
            else:
                raise AttributeError("Command not found")
        else:
            # If no action is provided "just" load vortex
            return self._vortex_base(line)

    def _vortex_base(self, line, verbose=True):
        """%vortex imports the vortex package and setup some usefull shortcuts."""
        if self._session is None:
            import bronx.stdtypes.date
            import footprints
            import vortex
            try:
                # Reset the flush interval to a value compatible by IPython
                sys.stdout.flush_interval = 2
            except AttributeError:
                sys.stderr.write('Unable to set an unbuffered stdout stream.')
            import common  # @UnusedImport
            import olive  # @UnusedImport
            fpx = footprints.proxy
            self._version = vortex.__version__
            self._session = vortex.ticket()
            # Shortcuts
            self._shell.push(dict(fp=footprints, fpx=fpx,
                                  vortex=vortex, toolbox=vortex.toolbox,
                                  date=bronx.stdtypes.date,
                                  t=self._session, e=self._session.env,
                                  sh=self._session.sh))
            self._session.sh.trace = False
            # Load various addons
            for module, addons in _IVORTEX_ADDONS:
                self._load_addons(fpx, self._session.sh, module, addons)
        else:
            if verbose:
                print("Vortex was already loaded: nothing to do")

    def _vortex_info(self, line):
        """%vortex info prints details about the current vortex session."""
        if self._session is None:
            print("Vortex is not loaded: type 'vortex' to do so.")
        else:
            fmt = '{:16s}: {:s}'
            print(fmt.format("Vortex's version", self._version))
            print(fmt.format("Vortex's session", self._session))
            print(fmt.format("Vortex's root", self._session.glove.siteroot))
            print(fmt.format("Vortex's basedir", self._basedir))
            print(fmt.format("Session's rundir", self._rundir))

    def _vortex_basedir(self, line):
        """%vortex basedir retrieve/set the basedir for vortex's cocoons.

        %vortex basedir        will return the basedir
        %vortex basedir ~/tmp  will attempt to set the basedir and return it

        After %vortex cocoon or %vortex tmpcocoon is called, it's not possible
        to alter the basedir.
        """
        if line and line[0]:
            if self._rundir is not None:
                raise RuntimeError("It's too late to setup the basedir")
            self._basedir = os.path.abspath(os.path.normpath(os.path.expanduser(line[0])))
        return self._basedir

    def _actual_vortex_cocoon(self, line, newrundir):
        """Internal: Set the vortex's session rundir and cocoon the current context

        If necessary, vortex is initialised.
        """
        if newrundir is not None:
            if self._rundir is None:
                # Load vortex if needed
                self._vortex_base(line, verbose=False)
                # Define the rundir
                self._rundir = newrundir
                self._session.rundir = newrundir
                self._session.context.cocoon()
                print("The working directory is now: {}".format(self._session.system().pwd()))
            else:
                print("Session's rundir is already set-up: {}".format(self._rundir))
        return self._rundir

    def _vortex_cocoon(self, line):
        """%vortex cocoon retrieve/set the vortex's session rundir.
        %vortex cocoon       will return the current rundir (may be None)
        %vortex cocoon test1 will set the rundir (basedir/test1)

        The rundir cannot be set twice.
        """
        # Find out what should be the rundir
        myrundir = None
        if self._rundir is None and line and line[0]:
            myrundir = os.path.join(self._basedir, line[0])
            if not os.path.exists(myrundir):
                os.makedirs(myrundir)
        return self._actual_vortex_cocoon(line, myrundir)

    def _vortex_tmpcocoon(self, line):
        """%vortex tmpcocoon generates a temporary directory for the vortex's session rundir.

        The temporary directory will be automatically destroyed when the
        IPython shell exits.
        """
        # Find out what should be the rundir
        myrundir = None
        if self._rundir is None:
            myrundir = os.path.join(self._basedir)
            if not os.path.exists(myrundir):
                os.makedirs(myrundir)
            myrundir = tempfile.mkdtemp(prefix='auto_cocoon_', dir=myrundir)

            # Delete the temp directory on exit
            def delete_temp_cocoon():
                os.chdir(self._basedir)
                shutil.rmtree(myrundir)
                print("Deleting the temporary rundir: {}".format(myrundir))
            atexit.register(delete_temp_cocoon)
        return self._actual_vortex_cocoon(line, myrundir)


def load_ipython_extension(ip):
    """Load the ivortex extension in IPython."""
    ip.register_magics(VortexMagics)
