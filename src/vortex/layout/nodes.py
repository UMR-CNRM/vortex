#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
This modules defines the base nodes of the logical layout
for any :mod:`vortex` experiment.
"""

import re

import footprints

from vortex import toolbox, VortexForceComplete
from vortex.util.config import GenericConfigParser, AppConfigStringDecoder
from vortex.syntax.stdattrs import Namespace

logger = footprints.loggers.getLogger(__name__)

#: Export real nodes.
__all__ = ['Driver', 'Task', 'Family']


class NiceLayout(object):
    """Some nice method to share between layout items."""

    @property
    def sh(self):
        """Abstract property: have to be defined later on"""
        raise NotImplementedError

    def subtitle(self, *args, **kw):
        """Proxy to :meth:`~vortex.tools.systems.subtitle` method."""
        return self.sh.subtitle(*args, **kw)

    def header(self, *args, **kw):
        """Proxy to :meth:`~vortex.tools.systems.header` method."""
        return self.sh.header(*args, **kw)

    def nicedump(self, msg, **kw):
        """Simple dump of the dict contents with ``msg`` as header."""
        self.header(msg)
        if kw:
            maxlen = max([ len(x) for x in kw.keys() ])
            for k, v in sorted(kw.iteritems()):
                print ' +', k.ljust(maxlen), '=', str(v)
            print
        else:
            print " + ...\n"


class ConfigSet(footprints.util.LowerCaseDict):
    """Simple struct-like object which is also a lower case dictionary.

    Two syntax are available to add a new entry in a :class:`ConfigSet` object:

    * ``ConfigSetObject.key = value``
    * ``ConfigSetObject[key] = value``

    Prior to its assignment, ``value`` is always passed to a
    :class:`vortex.util.config.AppConfigStringDecoder` object. It allows to
    describe complex data types (see the :class:`vortex.util.config.AppConfigStringDecoder`
    class documentation).

    Some extra features are added on top of the :class:`vortex.util.config.AppConfigStringDecoder`
    capabilities:

    * If ``key`` ends with *_map*, ``value`` will be seen as a dictionary
    * If ``key`` contains the words *geometry* or *geometries*, ``value``
      will be converted to a :class:`vortex.data.geometries.Geometry` object
    * If ``key`` ends with *_range*, ``value`` will be passed to the
      :func:`footprints.util.rangex` function

    """

    def __init__(self, *kargs, **kwargs):
        super(ConfigSet, self).__init__(*kargs, **kwargs)
        self._confdecoder = AppConfigStringDecoder()

    def __getattr__(self, attr):
        if attr in self:
            return self.get(attr)
        else:
            raise AttributeError('No such parameter <' + attr + '>')

    def __setattr__(self, attr, value):
        self[attr] = value

    def __setitem__(self, key, value):
        if value is not None and isinstance(value, basestring):
            # Support for old style dictionaries (compatibility)
            if (key.endswith('_map') and not re.match(r'^dict\(.*\)$', value) and
                    not re.match(r'^\w+\(dict\(.*\)\)$', value)):
                key = key[:-4]
                if re.match(r'^\w+\(.*\)$', value):
                    value = re.sub(r'^(\w+)\((.*)\)$', r'\1(dict(\2))', value)
                else:
                    value = 'dict(' + value + ')'
            # Support for geometries
            if (('geometry' in key or 'geometries' in key) and
                    (not re.match(r'^geometry\(.*\)$', value, flags=re.IGNORECASE))):
                value = 'geometry(' + value + ')'
            # Process the values recursively
            value = self._confdecoder(value)
            # Special case for rangex
            if key.endswith('_range') and isinstance(value, list):
                key = key[:-6]
                value = footprints.util.rangex(* value)
            if key.endswith('_range') and isinstance(value, basestring):
                key = key[:-6]
                value = footprints.util.rangex(re.sub(r'\s', '', value))
        super(ConfigSet, self).__setitem__(key, value)


class Node(footprints.util.GetByTag, NiceLayout):
    """Base class type for any element in the logical layout."""

    def __init__(self, kw):
        logger.debug('Node initialisation %s', repr(self))
        self.play       = kw.pop('play', False)
        self._ticket    = kw.pop('ticket', None)
        self._locprefix = kw.pop('special_prefix', 'OP_').upper()
        self._cycle_cb  = kw.pop('register_cycle_prefix', None)
        j_assist        = kw.pop('jobassistant', None)
        if j_assist is not None:
            self._locprefix = j_assist.special_prefix.upper()
            self._cycle_cb = j_assist.register_cycle
        self._conf      = None
        self._contents  = list()
        self._aborted   = False

    @classmethod
    def tag_clean(cls, tag):
        """Lower case, space-free and underscore-free tag."""
        return tag.lower().replace(' ', '').replace('_', '')

    @property
    def ticket(self):
        return self._ticket

    @property
    def aborted(self):
        return self._aborted

    @property
    def conf(self):
        return self._conf

    @property
    def sh(self):
        return self.ticket.sh

    @property
    def env(self):
        return self.ticket.env

    @property
    def contents(self):
        return self._contents

    def clear(self):
        """Clear actual contents."""
        self._contents[:] = []

    def __iter__(self):
        for node in self.contents:
            yield node

    def build_context(self):
        """Build the context and subcontexts of the current node."""
        oldctx = self.ticket.context
        ctx = self.ticket.context.newcontext(self.tag, focus=True)
        ctx.cocoon()
        self._setup_context(ctx)
        oldctx.activate()

    def _setup_context(self, ctx):
        """Setup the newly created context."""
        pass

    def __enter__(self):
        """
        Enter a :keyword:`with` context, freezing the current env
        and joining a cocoon directory.
        """
        self._oldctx = self.ticket.context
        ctx = self.ticket.context.switch(self.tag)
        ctx.cocoon()
        logger.debug('Node context directory <%s>', self.sh.getcwd())
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit from :keyword:`with` context."""
        logger.debug('Exit context directory <%s>', self.sh.getcwd())
        self._oldctx.activate()
        self.ticket.context.cocoon()

    def setconf(self, conf_local, conf_global):
        """Build a new conf object for the actual node."""

        # The parent conf is the default configuration
        self._conf = ConfigSet()
        self._conf.update(conf_local)

        # This configuration is updated with any section with the current tag name
        updconf = conf_global.get(self.tag, dict())
        self.nicedump(' '.join(('Configuration for', self.realkind, self.tag)), **updconf)
        self.conf.update(updconf)

        # Then we broadcast the current configuration to the kids
        for node in self.contents:
            node.setconf(self.conf.copy(), conf_global)

    def localenv(self):
        """Dump the actual env variables."""
        self.header('ENV catalog')
        self.env.mydump()

    def local2conf(self):
        """Set some parameters if defined in environment but not in actual conf."""
        autoconf = dict()
        localstrip = len(self._locprefix)
        for localvar in sorted([ x for x in self.env.keys() if x.startswith(self._locprefix) ]):
            if localvar[localstrip:] not in self.conf:
                autoconf[localvar[localstrip:].lower()] = self.env[localvar]
        if autoconf:
            self.nicedump('Populate conf with local variables', **autoconf)
            self.conf.update(autoconf)

    def conf2io(self):
        """Abstract method."""
        pass

    def xp2conf(self):
        """Set the actual experiment value -- Could be the name of the op suite if any."""
        if 'xpid' not in self.conf:
            self.conf.xpid = self.conf.get('suite', self.env.VORTEX_XPID)
        if self.conf.xpid is None:
            raise ValueError('Could not set a proper experiment id.')
        logger.info('Experiment name is <%s>', self.conf.xpid)

    def register_cycle(self, cyclename):
        """Adds a new cycle to genv if a proper callback is defined."""
        if self._cycle_cb is not None:
            self._cycle_cb(cyclename)
        else:
            raise NotImplementedError()

    def cycles(self):
        """Update and register some configuration cycles."""

        # At least, look for the main cycle
        if 'cycle' in self.conf:
            self.register_cycle(self.conf.cycle)

        # Have a look to other cycles
        for other in [ x for x in self.conf.keys() if x.endswith('_cycle') ]:
            self.register_cycle(self.conf.get(other))

    def geometries(self):
        """Setup geometries according to actual tag."""
        thisgeo = self.tag + '_geometry'
        if thisgeo in self.conf:
            self.conf.geometry = self.conf.get(thisgeo)
        if 'geometry' not in self.conf:
            logger.error('No default geometry defined -- Probably a big mistake !')

    def defaults(self, extras):
        """Set toolbox defaults, extended with actual arguments ``extras``."""
        t = self.ticket
        toolbox.defaults(
            model     = t.glove.vapp,
            date      = self.conf.rundate,
            namespace = self.conf.get('namespace', Namespace('vortex.cache.fr')),
        )

        for optk in ('cutoff', 'geometry', 'cycle', 'model'):
            if optk in self.conf:
                toolbox.defaults[optk] = self.conf.get(optk)

        toolbox.defaults(**extras)
        toolbox.defaults.show()

    def setup(self, **kw):
        """A methodic way to build the conf of the node."""
        self.subtitle(self.realkind.upper() + ' setup')
        self.localenv()
        self.local2conf()
        self.conf2io()
        self.xp2conf()
        self.nicedump('Update conf with last minute arguments', **kw)
        self.conf.update(kw)
        self.cycles()
        self.geometries()
        self.header('Toolbox defaults')
        self.defaults(kw.get('defaults', dict()))

    def summary(self):
        """Dump actual parameters of the configuration."""
        self.nicedump('Complete parameters', **self.conf)

    def refill(self, **kw):
        """Populates the vortex cache with expected input flow data.

        The refill method is systematically called when a task is run. However,
        the refill is not always desirable hence the if statement that checks the
        self.steps attribute's content.
        """
        # This method acts as an example: if a refill is actually needed,
        # it should be overwritten.
        if 'refill' in self.steps:
            logger.warning("Refill should takes place here: please overwrite...")

    def process(self):
        """Abstract method: perform the task to do."""
        # This method acts as an example: it should be overwritten.

        if 'early-fetch' in self.steps or 'fetch' in self.steps:
            # In a multi step job (MTOOL, ...), this step will be run on a
            # transfer node. Consequently, data that may be missing from the
            # local cache must be fetched here. (e.g. GCO's genv, data from the
            # mass archive system, ...). Note: most of the data should be
            # retrieved here since the use of transfer node is costless.
            pass

        if 'fetch' in self.steps:
            # In a multi step job (MTOOL, ...), this step will be run, on a
            # compute node, just before the beginning of computations. It is the
            # appropriate place to fetch data produced by a previous task (the
            # so-called previous task will have to use the 'backup' step
            # (see the later explanations) in order to make such data available
            # in the local cache).
            pass

        if 'compute' in self.steps:
            # The actual computations... (usually a call to the run method of an
            # AlgoComponent)
            pass

        if 'backup' in self.steps or 'late-backup' in self.steps:
            # In a multi step job (MTOOL, ...), this step will be run, on a
            # compute node, just after the computations. It is the appropriate
            # place to put data in the local cache in order to make it available
            # to a subsequent step.
            pass

        if 'late-backup' in self.steps:
            # In a multi step job (MTOOL, ...), this step will be run on a
            # transfer node. Consequently, most of the data should be archived
            # here.
            pass

    def complete(self, aborted=False):
        """Some cleaning and completetion status."""
        self._aborted = aborted

    def run(self, nbpass=0):
        """Abstract method: the actual job to do."""
        pass

    def report_execution_error(self):
        """may be overwritten if a report needs to be sent."""
        pass

    def component_runner(self, tbalgo, tbx=(None, ), **kwargs):
        """Run the binaries listed in tbx using the tbalgo algo component.

        This is a helper method that maybe useful (its use is not mandatory).
        """
        # it may be necessary to setup a default value for OpenMP...
        env_update = dict()
        if ('openmp' not in self.conf or
                ('openmp' in self.conf and
                 not isinstance(self.conf.openmp, (list, tuple)))):
            env_update['OMP_NUM_THREADS'] = int(self.conf.get('openmp', 1))
        # If some mpiopts are in the config file, use them...
        mpiotps = dict()
        mpiopts_map = dict(nnodes='nn', ntasks='nnp', nprocs='np', proc='np')
        for stuff in [s for s in ('proc', 'nprocs', 'nnodes', 'ntasks', 'openmp',
                                  'prefixcommand') if s in self.conf]:
                mpiotps[mpiopts_map.get(stuff, stuff)] = self.conf[stuff]
        # Ensure that some of the mpiopts are integers
        for stuff in [s for s in ('nn', 'nnp', 'openmp', 'np') if s in mpiotps]:
            if isinstance(mpiotps[stuff], (list, tuple)):
                mpiotps[stuff] = [int(v) for v in mpiotps[stuff]]
            else:
                mpiotps[stuff] = int(mpiotps[stuff])
        # When multiple list of binaries are given (i.e several binaries are launched
        # by the same MPI command).
        if tbx and isinstance(tbx[0], (list, tuple)):
            tbx = zip(tbx)
        with self.env.delta_context(**env_update):
            for binary in tbx:
                try:
                    tbalgo.run(binary, mpiopts = mpiotps, **kwargs)
                except Exception:
                    self.report_execution_error()
                    raise


class Family(Node):
    """Logical group of :class:`Family` or :class:`Task`."""

    def __init__(self, **kw):
        logger.debug('Family init %s', repr(self))
        super(Family, self).__init__(kw)
        nodes = kw.pop('nodes', list())
        self.options = kw.copy()

        # Build the nodes sequence
        fcount = 0
        for x in nodes:
            if isinstance(x, Node):
                self._contents.append(x)
            else:
                fcount += 1
                self._contents.append(
                    Family(
                        tag    = '{0:s}.f{1:02d}'.format(self.tag, fcount),
                        ticket = self.ticket,
                        nodes  = x,
                        **kw
                    )
                )

    @property
    def realkind(self):
        return 'family'

    def _setup_context(self, ctx):
        """Build the contexts of all the nodes contained by this family."""
        for node in self.contents:
            node.build_context()

    def run(self, nbpass=0):
        """Execution driver: setup, run kids, complete."""
        self.setup(**self.options)
        self.summary()
        for node in self.contents:
            with node:
                node.run()
        self.complete()


class Task(Node):
    """Terminal node including a :class:`Sequence`."""

    def __init__(self, **kw):
        logger.debug('Task init %s', repr(self))
        super(Task, self).__init__(kw)
        self.__dict__.update(
            steps   = kw.pop('steps', tuple()),
            fetch   = kw.pop('fetch', 'fetch'),
            compute = kw.pop('compute', 'compute'),
            backup  = kw.pop('backup', 'backup'),
        )
        self.options = kw.copy()
        if isinstance(self.steps, basestring):
            self.steps = tuple(self.steps.replace(' ', '').split(','))

    @property
    def realkind(self):
        return 'task'

    @property
    def ctx(self):
        return self.ticket.context

    def build(self, **kw):
        """Switch to rundir and check the active steps."""

        t = self.ticket
        t.sh.title(' '.join(('Build', self.realkind, self.tag)))

        # Change actual rundir if specified
        rundir = kw.get('rundir', None)
        if rundir:
            t.env.RUNDIR = rundir
            t.sh.cd(rundir, create=True)
            t.rundir = t.sh.getcwd()
        print 'The current directory is: {}'.format(t.sh.getcwd())

        # Some attempt to find the current active steps
        if not self.steps:
            if self.env.get(self._locprefix + 'REFILL'):
                self.steps = ('refill',)
            elif self.play:
                self.steps = ('early-{:s}'.format(self.fetch), self.fetch,
                              self.compute,
                              self.backup, 'late-{:s}'.format(self.backup))
            elif int(self.env.get('SLURM_NPROCS', 1)) > 1:
                self.steps = (self.fetch, self.compute)
            else:
                self.steps = (self.fetch,)
        self.header('Active steps: ' + ' '.join(self.steps))

    def conf2io(self):
        """Broadcast IO SERVER configuration values to environment."""
        t = self.ticket
        t.sh.header('IOSERVER Environment')
        t.env.default(VORTEX_IOSERVER_NODES  = self.conf.get('io_nodes', 0))
        t.env.default(VORTEX_IOSERVER_TASKS  = self.conf.get('io_tasks', 6))
        t.env.default(VORTEX_IOSERVER_OPENMP = self.conf.get('io_openmp', 4))

    def io_poll(self, prefix=None):
        """Complete the polling of data produced by the execution step."""
        sh = self.sh
        if prefix and sh.path.exists('io_poll.todo'):
            for iopr in prefix:
                sh.header('IO poll <' + iopr  + '>')
                rc = sh.io_poll(iopr)
                print rc
                print rc.result
            sh.header('Post-IO Poll directory listing')
            sh.ll(output=False, fatal=False)

    def run(self, nbpass=0):
        """Execution driver: build, setup, refill, process, complete."""
        try:
            self.build(**self.options)
            self.setup(**self.options)
            self.summary()
            self.refill()
            self.process()
        except VortexForceComplete:
            self.sh.title('Force complete')
        finally:
            self.complete()


class Driver(footprints.util.GetByTag, NiceLayout):
    """Iterable object for a simple scheduling of :class:`Application` objects."""

    _tag_default = 'pilot'

    def __init__(self, ticket=None, nodes=(),
                 rundate=None, iniconf=None, jobname=None, options=None):
        """Setup default args value and read config file job."""
        self._ticket = t = ticket
        self._conf = None

        # Set default parameters for the actual job
        self._options = dict() if options is None else options
        self._special_prefix = self._options.get('special_prefix', 'OP_').upper()
        j_assist = self._options.get('jobassistant', None)
        if j_assist is not None:
            self._special_prefix = j_assist.special_prefix.upper()
        self._iniconf = iniconf or t.env.get('{:s}INICONF'.format(self._special_prefix))
        self._jobname = jobname or t.env.get('{:s}JOBNAME'.format(self._special_prefix)) or 'void'
        self._rundate = rundate or t.env.get('{:s}RUNDATE'.format(self._special_prefix))
        self._nbpass  = 0

        # Build the tree to schedule
        self._contents = list()
        fcount = 0
        for x in nodes:
            if isinstance(x, Node):
                self._contents.append(x)
            else:
                fcount += 1
                self._contents.append(
                    Family(
                        tag     = '{0:s}.f{1:02d}'.format(self.tag, fcount),
                        ticket  = self.ticket,
                        nodes   = x,
                        ** self._options
                    )
                )

    @property
    def ticket(self):
        return self._ticket

    @property
    def conf(self):
        return self._conf

    @property
    def sh(self):
        return self.ticket.sh

    @property
    def env(self):
        return self.ticket.env

    @property
    def iniconf(self):
        return self._iniconf

    @property
    def jobconf(self):
        return self._jobconf

    @property
    def contents(self):
        return self._contents

    @property
    def jobname(self):
        return self._jobname

    @property
    def rundate(self):
        return self._rundate

    @property
    def nbpass(self):
        return self._nbpass

    def read_config(self, inifile=None):
        """Read specified ``inifile`` initialisation file."""
        if inifile is None:
            inifile = self.iniconf
        try:
            iniparser = GenericConfigParser(inifile)
            thisconf  = iniparser.as_dict(merged=False)
        except StandardError:
            logger.critical('Could not read config %s', inifile)
            raise
        return thisconf

    def setup(self, name=None, date=None, verbose=True):
        """Top setup of the current configuration, including at least one name."""

        jobname = name or self.jobname

        rundate = date or self.rundate
        if rundate is None:
            raise ValueError('No date provided for this run.')

        if verbose:
            self.sh.title(['Starting job', '', jobname, '', 'date ' + rundate.isoformat()])

        # Read once for all the job configuration file
        if self.iniconf is None:
            logger.warning('This driver does not have any configuration file')
            self._jobconf = dict()
        else:
            self._jobconf = self.read_config(self.iniconf)

        self._conf = ConfigSet()
        updconf = self.jobconf.get('defaults', dict())
        updconf.update(self.jobconf.get(self.jobname, dict()))
        self.nicedump('Configuration for job ' + self.jobname, **updconf)
        self.conf.update(updconf)

        # Recursively set the configuration tree and contexts
        self.conf.rundate = rundate
        for node in self.contents:
            node.setconf(self.conf.copy(), self.jobconf)
            node.build_context()

    def run(self):
        """Assume recursion of nodes `run` methods."""
        self._nbpass += 1
        for node in self.contents:
            with node:
                node.run(nbpass=self.nbpass)
