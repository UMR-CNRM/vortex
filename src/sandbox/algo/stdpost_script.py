#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module contains example AlgoComponents that deal with a list of gridpoint
input files (like a real post-procesing task would do).

The AlgoComponents defined here are very similar to the one defined in
:mod:`sandbox.algo.stdpost`. However, in this module, an external external
script is used to do the actual processing.
"""

from __future__ import print_function, absolute_import, unicode_literals, division
import six

import collections
import io
import time

from bronx.fancies import loggers

import footprints as fp

from vortex.algo.components import Expresso, ParaExpresso, AlgoComponentDecoMixin
from vortex.layout.monitor import BasicInputMonitor
from vortex.tools.parallelism import VortexWorkerBlindRun

from .stdpost import GribInfosKey

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class GribInfosScriptMixin(AlgoComponentDecoMixin):
    """Gather some traits that are shared between AlgoComponents of this module.

    The :class:`GribInfosScript` and :class:`GribInfosParaScript` classes that
    need the content of this mixin class, must inherit from to different base classes
    to achieve their goal (resp. :class:`~vortex.algo.components.Expresso` and
    :class:`~vortex.algo.components.ParaExpresso`). That's why the usual
    "inheritance" mechanism is not usable. Instead, we use the mixin class
    mechanism that was especially designed for AlgoComponent classes
    (see the :class:`~vortex.algo.components.AlgoComponentDecoMixin` class
    documentation for more details). Such mixin classes act as plugins "on top"
    of any AlgoComponent class.
    """

    _MIXIN_EXTRA_FOOTPRINTS = [
        fp.Footprint(
            attr=dict(
                engine=dict(
                    default='exec',
                    optional=True,
                ),
                jsonoutput=dict(
                    optional=True,
                    default='grib_infos.json'
                ),
            ),
        ),
    ]

    @staticmethod
    def _gribkey(rh):
        """The dictionary key describing a grib file."""
        return GribInfosKey(rh.provider.vapp, rh.provider.vconf,
                            int(rh.provider.member), rh.resource.geometry.area)

    def _write_jsonoutput(self, rh, opts):
        """Create a list of dictionaries and dump it in the JSON output file."""
        dumpable = list()
        for gribk, v in sorted(self._gribstack.items()):
            entry = gribk._asdict()
            entry['terms'] = v
            dumpable.append(entry)
        self.system.json_dump(dumpable, self.jsonoutput, indent=2)

    # Tells the mixin class that the :meth:`_write_jsonoutput` method must b
    # executed just after the ``postfix`` method.
    _MIXIN_POSTFIX_HOOKS = (_write_jsonoutput, )


class GribInfosScript(Expresso, GribInfosScriptMixin):
    """Loop on available grib files to compute their size and MD5 sum.

    The result is written in a JSON file and individual md5 file are produced.

    In this version:

    * The input data may have been promised by another task (thus
      allowing on the fly processing);
    * The input data are processed as soon as they are available (e.g.
      if there are several members, data with term 06h of member 2 may be
      available before term 03h of member 1);
    * Additionaly, if they have been promised, the individual md5 files
      are stored in cache.
    * An external script is used to compute the md5 sum (have a look at the
      :class:`sandbox.data.executables.StdpostScript` resource.
    """

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['gribscript'],
            ),
        ),
    ),

    def __init__(self, *kargs, **kwargs):
        super(GribInfosScript, self).__init__(*kargs, **kwargs)
        self._current_path = 'unspecified'
        self._gribstack = collections.defaultdict(dict)

    def spawn_command_options(self):
        """Add the name of the file currently being processed to the command line."""
        return dict(todo=self._current_path)

    def execute(self, rh, opts):
        """Loop on the various Grib files and launch the Grib file."""

        # Monitor for the input files
        bm = BasicInputMonitor(self.context,
                               caching_freq=5,  # In a background task, refresh
                                                # the input file list every 5s
                               role='Gridpoint')
        with bm:
            while not bm.all_done or len(bm.available) > 0:

                # Deal with available sections
                while bm.available:
                    my_rh = bm.pop_available().section.rh

                    # Record the current filename for command line generation
                    self._current_path = my_rh.container.localpath()
                    logger.info('Processing < %s >', self._current_path)

                    # Actually launch the script
                    super(GribInfosScript, self).execute(rh, opts)

                    # Gather the information for later use
                    with io.open(self._current_path + '.md5', 'r',
                                 encoding='utf-8', errors='ignore') as fhmd:
                        md5sum = fhmd.readline().split()[0]
                    self._gribstack[self._gribkey(my_rh)][my_rh.resource.term.fmthm] = dict(
                        filesize=my_rh.container.totalsize,
                        md5sum=md5sum
                    )

                # Various sanity checks
                if not (bm.all_done or len(bm.available) > 0):
                    # Timeout ? (wait at most self.timeout seconds)
                    tmout = bm.is_timedout(self.timeout)
                    if tmout:
                        break
                    # Wait a little bit to limit the CPU usage :-)
                    time.sleep(1)
                    # Display a nice log message every 30s to explain the
                    # situation
                    bm.health_check(interval=30)


class GribInfosParaScriptWorker(VortexWorkerBlindRun):
    """Worker class for ``taylorism`` that processes a Grib file."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['gribscript_para']
            ),
            progargs = dict(
                # We will need to modify the command line arguments in order to
                # "publish" the Grib file name
                access = 'rwx',
            ),
            inputfile = dict(),
            outputfile = dict(),
        )
    )

    def vortex_task(self, **kwargs):

        rdict = dict(rc=True)

        # Tweak the command line
        for i in range(len(self.progargs)):
            if isinstance(self.progargs[i], six.string_types):
                self.progargs[i] = self.progargs[i].format(inputfile=self.inputfile)
        # Launch the post-processing scripts
        self.local_spawn(stdoutfile=self.inputfile + '.log')

        # Deal with promises
        allpromises = [x for x in self.context.sequence.outputs()
                       if x.rh.provider.expected]
        expected = [x for x in allpromises
                    if x.rh.container.localpath() == self.outputfile]
        for thispromise in expected:
            logger.info('A promised was found < %s >',
                        thispromise.rh.container.localpath())
            thispromise.put(incache=True)

        # Gather information
        with io.open(self.outputfile, 'r',
                     encoding='utf-8', errors='ignore') as fhmd:
            md5sum = fhmd.readline().split(' ')[0]
        rdict['infodict'] = dict(
            md5sum=md5sum,
            filesize=self.system.stat(self.inputfile).st_size
        )

        return rdict


class GribInfosParaScript(ParaExpresso, GribInfosScriptMixin):
    """Deal with grib files to compute their size and MD5 sum.

    The result is written in a JSON file and individual md5 file are produced.

    In this version:

    * The input data may have been promised by another task (thus
      allowing on the fly processing);
    * The input data are processed as soon as they are available (e.g.
      if there are several members, data with term 06h of member 2 may be
      available before term 03h of member 1);
    * The various available Grib files are dealt with in parallel (using the
      taylorism package)
    * Additionaly, if they have been promised, the individual md5 files
      are stored in cache.
    * An external script is used to compute the md5 sum (have a look at the
      :class:`sandbox.data.executables.StdpostScript` resource.
    """

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['gribscript_para'],
            ),
        ),
    )

    def __init__(self, *kargs, **kwargs):
        super(GribInfosParaScript, self).__init__(*kargs, **kwargs)
        self._gribstack = collections.defaultdict(dict)
        self._gribkeys_cache = dict()
        self._termkeys_cache = dict()

    def spawn_command_options(self):
        """Add the name of the file currently being processed to the command line."""
        return dict(todo='{inputfile:s}')

    def _default_rc_action(self, rh, opts, report, rc):
        """Process the worker's result in order to gather information about Grib files."""
        super(GribInfosParaScript, self)._default_rc_action(rh, opts, report, rc)
        if rc:
            gribkey = self._gribkeys_cache[report['name']]
            termkey = self._termkeys_cache[report['name']]
            self._gribstack[gribkey][termkey] = report['report']['infodict']

    def execute(self, rh, opts):
        """Loop on the various Grib files."""

        # Initialise taylorism
        self._default_pre_execute(rh, opts)
        common_i = self._default_common_instructions(rh, opts)
        # Monitor for the input files
        bm = BasicInputMonitor(self.context,
                               caching_freq=5,  # In a background task, refresh
                                                # the input file list every 5s
                               role='Gridpoint')
        with bm:
            while not bm.all_done or len(bm.available) > 0:
                # Deal with available sections
                while bm.available:
                    my_rh = bm.pop_available().section.rh
                    current_path = my_rh.container.localpath()
                    current_path_out = current_path + '.md5'
                    logger.info('Starting processing of < %s >', current_path)

                    # Send instructions to taylorism (the :class:`GribInfosParaScriptWorker`
                    # worker class will be used)
                    self._gribkeys_cache[current_path] = self._gribkey(my_rh)
                    self._termkeys_cache[current_path] = my_rh.resource.term.fmthm
                    self._add_instructions(common_i, dict(name=[current_path],
                                                          inputfile=[current_path],
                                                          outputfile=[current_path_out]))

                # Various sanity checks
                if not (bm.all_done or len(bm.available) > 0):
                    # Timeout ? (wait at most self.timeout seconds)
                    tmout = bm.is_timedout(self.timeout)
                    if tmout:
                        break
                    # Wait a little bit to limit the CPU usage :-)
                    time.sleep(1)
                    # Display a nice log message every 30s to explain the
                    # situation
                    bm.health_check(interval=30)

        self._default_post_execute(rh, opts)
