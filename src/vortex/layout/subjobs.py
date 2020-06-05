#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines classes in charge of launching sub-jobs. This allow for a
rough parallelisation at job's level.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import collections
import contextlib
import io
import locale
import re
import sys
import time

from bronx.datagrip import datastore
from bronx.fancies import loggers
from bronx.syntax.parsing import xlist_strings
import footprints as fp

logger = loggers.getLogger(__name__)

_LOG_CAPTURE_START = '>>>> subjob stdeo start <<<<\n'
_LOG_CAPTURE_END = '>>>> subjob stdeo end <<<<\n'

_DSTORE_IN = '{:s}_datastore.in'
_DSTORE_OUT = '{:s}_{:s}_datastore.out'
_JOB_STDEO = '{:s}_{:s}.stdeo'


@contextlib.contextmanager
def subjob_output_markup(do_marking_up):
    """Insert markup strings in stdout in order to frame its "usefull" part."""
    if do_marking_up:
        sys.stdout.write(_LOG_CAPTURE_START)
        sys.stdout.flush()
    try:
        yield
    finally:
        if do_marking_up:
            sys.stdout.write(_LOG_CAPTURE_END)
            sys.stdout.flush()


class SubJobLauncherError(Exception):
    """Raise whenever an error occurred in at least on of the subjobs."""
    pass


class AbstractSubJobLauncher(fp.FootprintBase):
    """Abstract subjob launcher class."""

    _collector = ('subjobslauncher',)
    _abstract = True
    _footprint = dict(
        info = 'Abstract SubJob launcher.',
        attr = dict(
            kind = dict(
            ),
            limit = dict(
                type = int,
                optional = True
            ),
            scriptpath = dict(
            )
        ),
    )

    def __init__(self, *kargs, **kwargs):
        super(AbstractSubJobLauncher, self).__init__(*kargs, **kwargs)
        self._ticket = None
        self._watermark = 0
        self._running = dict()
        logger.info('"%s" subjob launcher created (limit=%s, scriptpath=%s)',
                    self.kind, str(self.limit), self.scriptpath)

    @property
    def actual_limit(self):
        """The maximum number of subjobs allowed in parallel."""
        return self.limit

    def _new_ticket_hook(self, t):
        """Any additional actions to be performed when a next session ticket is provided."""
        pass

    def _set_ticket(self, t):
        self._ticket = t
        self.fsid = self.ticket.sh.path.join(self.ticket.sh.pwd(), 'sjob_fs')
        self._ticket.datastore.pickle_dump(_DSTORE_IN.format(self.fsid))
        self._new_ticket_hook(t)

    def _get_ticket(self):
        assert self._ticket is not None
        return self._ticket

    ticket = property(_get_ticket, _set_ticket, doc="The current Session's ticket")

    def __call__(self, tag, subtags):
        """Launch the subjob that will be in charge of processing the **tag** node."""
        if self.actual_limit is not None and self._watermark == self.actual_limit:
            logger.info("The subjobs limit is reached (%d). Waiting for some subjobs to finish.",
                        self.actual_limit)
            self.wait()
        self._running[tag] = subtags
        self._watermark += 1
        with self.ticket.env.delta_context(VORTEX_SUBJOB_ACTIVATED='{:s}:{:s}'.format(tag, self.fsid)):
            logger.info("Launching subjob with VORTEX_SUBJOB_ACTIVATED='%s'",
                        self.ticket.env.VORTEX_SUBJOB_ACTIVATED)
            self._actual_launch(tag)

    def wait(self):
        """Wait for at least one subjob to complete."""
        done = self._actual_wait()
        for tag in done:
            self._stdeo_dump(tag, 'succeeded')
            self._update_context(tag)
            del self._running[tag]
            self._watermark -= 1

    def waitall(self):
        """Wait for all subjob to complete."""
        logger.info("Waiting for all subjobs to terminate.")
        while self._running:
            self.wait()

    def _stdeo_dump(self, tag, outcome='succeeded', ignore_end=False):
        """Dump the standard output of the subjob refered by **tag**.

        :param tag: The subjob's tag
        :param outcome: Some indication on how the subjob ended
        :param ignore_end: Print the entire standard output (usefull for debuging)
        """
        plocale = locale.getdefaultlocale()[1] or 'ascii'
        self.ticket.sh.title('subjob "{:s}" {:s}. Here is the output:'.format(tag, outcome))
        with io.open(_JOB_STDEO.format(self.fsid, tag), mode='rt', encoding=plocale) as fhst:
            started = False
            for lst in fhst:
                if started:
                    if lst == _LOG_CAPTURE_END:
                        if not ignore_end:
                            break
                    else:
                        sys.stdout.write(lst)
                else:
                    started = lst == _LOG_CAPTURE_START
        print()
        print('Full Log available at: {:s}_{:s}.stdeo'.format(self.fsid, tag))
        print()

    def _update_context(self, tag):
        """Update the context using the **tag** subjob datastore's dump."""
        stags = self._running[tag]
        ds = datastore.DataStore()
        ds.pickle_load(_DSTORE_OUT.format(self.fsid, tag))
        for k in ds.keys():
            if re.match('context_', k.kind):
                xpath = k.extras.get('path', '').split('/')
                for stag in stags:
                    # Only update relevant entries
                    if xpath[-1] == stag:
                        logger.info('Updating "%s, path=%s" in the datastore',
                                    k.kind, '/'.join(xpath))
                        curv = self.ticket.datastore.get(k.kind, k.extras)
                        if hasattr(curv, 'datastore_inplace_overwrite'):
                            curv.datastore_inplace_overwrite(ds.get(k.kind, k.extras))
                        else:
                            self.ticket.datastore.insert(k.kind, k.extras,
                                                         ds.get(k.kind, k.extras))
                        break

    def _actual_launch(self, tag):
        """Launch the **tag** subjob: to be overwritten in the subclass!"""
        raise NotImplementedError()

    def _actual_wait(self):
        """Wait for the **tag** subjob: to be overwritten in the subclass!"""
        raise NotImplementedError()


class SpawnSubJobLauncher(AbstractSubJobLauncher):
    """A very simple subjob launcher: just starts a new process."""

    _footprint = dict(
        attr = dict(
            kind =dict(
                values = ['spawn', ]
            )
        )
    )

    def __init__(self, *kargs, **kwargs):
        super(SpawnSubJobLauncher, self).__init__(*kargs, **kwargs)
        self._outfhs = dict()
        self._processes = dict()
        self._nvcores = None

    @property
    def actual_limit(self):
        """The maximum number of subjobs allowed in parallel."""
        if self.limit is not None:
            return self.limit
        elif self.limit is None and self._nvcores is not None:
            return self._nvcores
        else:
            raise ValueError('No limit could be found for the number of subprocesses.')

    def _new_ticket_hook(self, t):
        """Tries to find out the number of virtual cores available."""
        super(SpawnSubJobLauncher, self)._new_ticket_hook(t)
        if self.limit is None and t.sh.cpus_info is not None:
            self._nvcores = t.sh.cpus_info.nphysical_cores
            logger.info('"spawn" subjob launcher set to %d (i.e the number of virtual cores)',
                        self._nvcores)

    def _actual_launch(self, tag):
        """Just launch the subjob using a subprocess... easy!"""
        sh = self.ticket.sh
        ofh = io.open(_JOB_STDEO.format(self.fsid, tag), mode='wb')
        p = sh.popen([sys.executable, self.scriptpath], stdout=ofh, stderr=ofh)
        self._outfhs[tag] = ofh
        self._processes[tag] = p

    def _actual_wait(self):
        """Wait for at least one subprocess to terminate.

        If none of the subjob failed, returns the list of tags of the successful
        subjobs. If at least one of the subjob fails, wait for every process to
        terminate and raise a :class:`SubJobLauncherError` exception.
        """
        sh = self.ticket.sh
        oktags = list()
        kotags = list()
        while self._processes and (not oktags or kotags):
            for tag, p in self._processes.items():
                if p.poll() is not None:
                    if sh.pclose(p):
                        oktags.append(tag)
                    else:
                        kotags.append(tag)
                        self._stdeo_dump(tag, 'failed', ignore_end=True)
            for tag in oktags + kotags:
                if tag in self._processes:
                    del self._processes[tag]
                    del self._outfhs[tag]
            time.sleep(1)
        if kotags:
            raise SubJobLauncherError("Execution failed for some subjobs: {:s}"
                                      .format(','.join(kotags)))
        return oktags


class AbstractSshSubJobLauncher(AbstractSubJobLauncher):
    """Use SSH to launch a remote subjob."""

    _abstract = True
    _footprint = dict(
        attr = dict(
            taskspn = dict(
                type = int,
                default = 1,
                optional = True,
            ),
        )
    )

    def __init__(self, *kargs, **kwargs):
        super(AbstractSshSubJobLauncher, self).__init__(*kargs, **kwargs)
        self.nodes = list()
        self._avnodes = collections.deque()
        self._outfhs = dict()
        self._hosts = dict()
        self._processes = dict()

    @property
    def actual_limit(self):
        """The maximum number of subjobs allowed in parallel."""
        if self.limit is None:
            return len(self.nodes)
        else:
            return self.limit

    def _find_raw_nodes_list(self, t):
        """This method should be overwritten and return a list of target hostnames."""
        raise NotImplementedError()

    def _env_variables_iterator(self, t):
        """Return the environment variables that will be used."""
        return t.topenv.items()

    def _new_ticket_hook(self, t):
        """Common initialisations."""
        super(AbstractSshSubJobLauncher, self)._new_ticket_hook(t)
        self.nodes = self._find_raw_nodes_list(t)
        # Several tasks may be launched on a single node
        self.nodes = self.nodes * self.taskspn
        if self.limit is not None and len(self.nodes) < self.limit:
            raise RuntimeError('The are not enough compute nodes (available:{:s}/requested={:d})'
                               .format(len(self.nodes), self.limit))
        # Summary
        logger.info("%d task(s) per node will be launched. Nodes list: %s",
                    self.taskspn, ",".join(sorted(set(self.nodes))))
        # Available nodes
        self._avnodes = collections.deque(self.nodes)
        # Freeze the root environment in a wrapper
        self._lwrapper = '{:s}.wrap.sh'.format(self.fsid)
        with io.open(self._lwrapper, 'w', encoding='utf-8') as fhwrap:
            fhwrap.write('#! /bin/bash\n')
            fhwrap.write('set -x\n')
            fhwrap.write('set -e\n')
            fhwrap.write('echo "I am running on $(hostname) !"\n')
            for k, v in self._env_variables_iterator(t):
                if re.match(r'[-_\w]+$', k):  # Get rid of weird variable names
                    fhwrap.write("export {:s}='{!s}'\n".format(k.upper(), v))
            fhwrap.write('exec $*\n')
        t.sh.xperm(self._lwrapper, force=True)
        # Put the script on the parallel file-system (otherwise it won't be accessible
        # from other nodes)
        self._pfs_scriptpath = '{:s}.script.py'.format(self.fsid)
        t.sh.cp(self.scriptpath, self._pfs_scriptpath)

    def _env_lastminute_update(self, tag, thost):
        """Add some lastminute environment variables."""
        return dict().items()

    def _actual_launch(self, tag):
        """Just launch the subjob using an SSH command."""
        sh = self.ticket.sh
        thost = self._avnodes.popleft()
        logger.info('"%s" will be used (through SSH).', thost)
        ofh = io.open(_JOB_STDEO.format(self.fsid, tag), mode='wb')
        cmd = "export VORTEX_SUBJOB_ACTIVATED='{:s}'; ".format(sh.env.VORTEX_SUBJOB_ACTIVATED)
        cmd += ' '.join(["export {:s}='{!s}'; ".format(k, v)
                         for k, v in self._env_lastminute_update(tag, thost)])
        cmd += ' '.join([self._lwrapper, sys.executable, self._pfs_scriptpath])
        print(cmd)
        p = sh.ssh(thost).background_execute(cmd, sshopts='-o CheckHostIP=no',
                                             stdout=ofh, stderr=ofh)
        self._outfhs[tag] = ofh
        self._hosts[tag] = thost
        self._processes[tag] = p

    def _actual_wait(self):
        """Wait for at least one subprocess to terminate.

        If none of the subjob failed, returns the list of tags of the successful
        subjobs. If at least one of the subjob fails, wait for every process to
        terminate and raise a :class:`SubJobLauncherError` exception.
        """
        sh = self.ticket.sh
        oktags = list()
        kotags = list()
        while self._processes and (not oktags or kotags):
            for tag, p in self._processes.items():
                if p.poll() is not None:
                    if sh.pclose(p):
                        oktags.append(tag)
                    else:
                        kotags.append(tag)
                        self._stdeo_dump(tag, 'failed', ignore_end=True)
            for tag in oktags + kotags:
                if tag in self._processes:
                    self._avnodes.append(self._hosts.pop(tag))
                    del self._processes[tag]
                    del self._outfhs[tag]
            time.sleep(1)
        if kotags:
            raise SubJobLauncherError("Execution failed for some subjobs: {:s}"
                                      .format(','.join(kotags)))
        return oktags


class SlurmSshSubJobLauncher(AbstractSshSubJobLauncher):
    """
    Find the list of availlable compute nodes thanks to SLURM and use SSH to
    launch subjobs.
    """

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['slurm:ssh', ]
            ),
        )
    )

    def _env_variables_iterator(self, t):
        """Return the environment variables that will be used."""
        blacklist = set(["SLURM_{:s}".format(s)
                         for s in ('NNODES', 'JOB_NNODES', 'JOB_NUM_NODES',
                                   'NODELIST', 'JOB_NODELIST')])
        slurmnodes_ids = re.compile(r'(\(x\d+\))$')
        for k, v in t.topenv.items():
            if k not in blacklist:
                if k.startswith('SLURM') and slurmnodes_ids.search(v):
                    yield k, slurmnodes_ids.sub('(x1)', v)
                else:
                    yield k, v
        for k in ('SLURM_NNODES', 'SLURM_JOB_NNODES', 'SLURM_JOB_NUM_NODES'):
            yield k, "1"

    def _env_lastminute_update(self, tag, thost):  # @UnusedVariable
        """Add some lastminute environment variables."""
        return dict(SLURM_NODELIST=thost,
                    SLURM_JOB_NODELIST=thost).items()

    def _find_raw_nodes_list(self, t):
        """Find out what is the nodes list.

        To do so, the SLURM_JOB_NODELIST environment variable is processed.
        """
        # Process SLURM's nodes list
        nlist = t.env.get('SLURM_JOB_NODELIST',
                          t.env.get('SLURM_NODELIST', None))
        if nlist:
            return xlist_strings(nlist)
        else:
            raise RuntimeError('The "SLURM_JOB_NODELIST" environment variable is not defined.')
