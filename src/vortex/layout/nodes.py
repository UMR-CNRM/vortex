#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
This modules defines the base nodes of the logical layout
for any :mod:`vortex` experiment.
"""

#: Export real nodes.
__all__ = ['Driver', 'Task', 'Family']

import re

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex import toolbox, data, VortexForceComplete
from vortex.util.config import GenericConfigParser
from vortex.syntax.stdattrs import Namespace

from . import dataflow


class NiceLayout(object):
    """Some nice method to share between layout items."""

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
    """Simple struct-like object wich is also a lower case dictionnary."""

    def remap_int(self, value):
        try:
            value = int(value)
        except Exception:
            pass
        return value

    def remap_float(self, value):
        try:
            value = float(value)
        except Exception:
            pass
        return value

    def remap_default(self, value):
        return value

    def __getattr__(self, attr):
        if attr in self:
            return self.get(attr)
        else:
            raise AttributeError('No such parameter <' + attr + '>')

    def __setattr__(self, attr, value):
        self[attr] = value

    def __setitem__(self, key, value):
        if value is not None and isinstance(value, basestring):
            rmap = 'default'
            if re.match('\w+\(.*\)', value):
                ipos = value.index('(')
                rmap = value[:ipos]
                value = value[ipos+1:-1]
            remap = getattr(self, 'remap_' + rmap)
            if key.endswith('_range'):
                key = key[:-6]
                value = footprints.util.rangex(value.replace(' ', ''))
            elif key.endswith('_map'):
                key = key[:-4]
                value = { k:remap(v) for k, v in [ x.split(':') for x in value.split() ] }
            elif key.endswith('geometry'):
                value = data.geometries.get(tag=value)
            elif ',' in value:
                value = [ remap(v) for v in value.replace(' ', '').split(',') ]
            else:
                value = remap(value)
        super(ConfigSet, self).__setitem__(key, value)


class Node(footprints.util.GetByTag):
    """Base class type for any element in the logical layout."""

    def __init__(self, kw):
        logger.debug('Node initialisation %s', repr(self))
        self.play      = kw.pop('play', False)
        self._ticket   = kw.pop('ticket', None)
        self._conf     = None
        self._contents = list()
        self._aborted  = False

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

    def __enter__(self):
        """
        Enter a :keyword:`with` context, freezing the current env
        and joining a cocoon directory.
        """
        self._oldctx = self.ticket.context
        ctx = self.ticket.context.newcontext(self.tag, focus=True)
        ctx.cocoon()
        logger.debug('Node context directory <%s>', self.sh.getcwd())
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit from :keyword:`with` context."""
        logger.debug('Exit context directory <%s>', self.sh.getcwd())
        self._oldctx.catch_focus()
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

    def op2conf(self):
        """Set some parameters if defined in environment but not in actual conf."""
        autoconf = dict()
        for opvar in sorted([ x for x in self.env.keys() if x.startswith('OP_') ]):
            if opvar[3:] not in self.conf:
                autoconf[opvar[3:].lower()] = self.env[opvar]
        if autoconf:
            self.nicedump('Populate conf with op variables', **autoconf)
            self.conf.update(autoconf)

    def conf2io(self):
        """Abstract method."""
        pass

    def xp2conf(self):
        """Set the actual experiment value -- Could be the name of the op suite if any."""
        if 'experiment' not in self.conf:
            self.conf.xpid = self.conf.experiment = self.conf.get('suite', self.env.VORTEX_XPID)
        if self.conf.experiment is None:
            raise ValueError('Could not set a proper experiment id.')
        logger.info('Experiment name is <%s>', self.conf.experiment)

    def register_cycle(self, cyclename):
        """Abstract method."""
        pass

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

        for optk in ('cutoff', 'geometry'):
            if optk in self.conf:
                toolbox.defaults[optk] = self.conf.get(optk)

        toolbox.defaults(**extras)
        toolbox.defaults.show()

    def setup(self, **kw):
        """A methodic way to build the conf of the node."""
        self.subtitle(self.realkind.upper() + ' setup')
        self.localenv()
        self.op2conf()
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

    def reshape_starter(self, **kw):
        """Make a nice tuple from the starter value and possible preset configurations."""
        self.header('Reshape starter <' + str(self.starter) + '>')
        if self.starter:
            if type(self.starter) is bool:
                self.starter = ('full',)
            elif isinstance(self.starter, basestring):
                self.starter = self.starter.replace(' ', '').split(',')
            while any([ x for x in self.starter if x in kw ]):
                for item in [ x for x in self.starter if x in kw ]:
                    pos = self.starter.index(item)
                    self.starter[pos:pos+1] = list(kw[item])
                    print ' + remap', item.ljust(15), '=>', kw[item]
            self.starter = tuple(self.starter)
        else:
            self.starter = ('none',)
        print ' + remap', 'complete'.ljust(15), '=>', self.starter
        print

    def refill(self, **kw):
        """Populates the op vortex cache with expected input flow data."""
        pass

    def process(self):
        """Abstract method: perform the taks to do."""
        pass

    def complete(self, aborted=False):
        """Some cleaning and completetion status."""
        self._aborted = aborted

    def run(self, nbpass=0):
        """Abstract method: the actual job to do."""
        pass


class Family(Node, NiceLayout):
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
                fcount = fcount + 1
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

    def run(self, nbpass=0):
        """Execution driver: setup, run kids, complete."""
        self.setup(**self.options)
        self.summary()
        for node in self.contents:
            with node:
                node.run()
        self.complete()


class Task(Node, NiceLayout):
    """Terminal node including a :class:`Sequence`."""

    def __init__(self, **kw):
        logger.debug('Task init %s', repr(self))
        super(Task, self).__init__(kw)
        self.__dict__.update(
            steps   = kw.pop('steps',   tuple()),
            fetch   = kw.pop('fetch',   'fetch'),
            compute = kw.pop('compute', 'compute'),
            backup  = kw.pop('backup',  'backup'),
            starter = kw.pop('starter', False),
        )
        self._sequence = dataflow.Sequence()
        self.options = kw.copy()
        if isinstance(self.steps, basestring):
            self.steps = tuple(self.steps.replace(' ', '').split(','))

    @property
    def realkind(self):
        return 'task'

    @property
    def sequence(self):
        return self._sequence

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

        # Some attempt to find the current active steps
        if not self.steps:
            if self.play:
                self.steps = (self.fetch, self.compute, self.backup)
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
            sh.ll(output=False)

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

    def __init__(self, ticket=None, nodes=(), rundate=None, iniconf=None, jobname=None, options=None):
        """Setup default args value and read config file job."""
        self._ticket = t = ticket
        self._conf = None

        # Set default parameters for the actual job
        self._iniconf = iniconf or t.env.OP_INICONF
        self._jobname = jobname or t.env.OP_JOBNAME or 'void'
        self._rundate = rundate or t.env.OP_RUNDATE
        self._options = options
        self._nbpass  = 0

        # Build the tree to schedule
        self._contents = list()
        fcount = 0
        for x in nodes:
            if isinstance(x, Node):
                self._contents.append(x)
            else:
                fcount = fcount + 1
                self._contents.append(
                    Family(
                        tag     = '{0:s}.f{1:02d}'.format(self.tag, fcount),
                        ticket  = self.ticket,
                        nodes   = x,
                        options = options
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

    def setup(self, name=None, date=None, envname='OP_JOBNAME', envdate='OP_RUNDATE', verbose=True):
        """Top setup of the current configuration, including at least one name."""

        jobname = name or self.jobname or self.env.get(envname)
        if jobname is None:
            raise StandardError('No job name provided.')

        rundate = date or self.rundate or self.env.get(envdate)
        if rundate is None:
            raise StandardError('No date provided for this run.')

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

        # Recursively set the configuration tree
        self.conf.rundate = rundate
        for node in self.contents:
            node.setconf(self.conf.copy(), self.jobconf)

    def run(self):
        """Assume recursivity of nodes `run` methods."""
        self._nbpass += 1
        for node in self.contents:
            with node:
                node.run(nbpass=self.nbpass)
