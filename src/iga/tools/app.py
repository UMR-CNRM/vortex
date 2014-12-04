#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []


import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex import toolbox

from . import op

def read_config(inifile):
    """read specified ``section`` (eg: job name) in ``inifile``."""
    from vortex.util.config import GenericConfigParser
    try:
        iniparser = GenericConfigParser(inifile)
        iniconf   = iniparser.as_dict()
    except Exception:
        logger.critical('Could not read config %s', inifile)
        raise
    return iniconf


class ConfigSet(footprints.util.LowerCaseDict):
    """Simple struct-like object wich is also a lower case dictionnary."""

    def __getattr__(self, attr):
        if attr in self:
            return self.get(attr)
        else:
            raise AttributeError('No such parameter <' + attr + '>')

    def __setattr__(self, attr, value):
        self[attr] = value

    def __setitem__(self, key, value):
        if value is not None and type(value) is str and ',' in value:
            value = value.replace(' ', '').split(',')
        super(ConfigSet, self).__setitem__(key, value)


class Application(footprints.util.GetByTag):
    """Wrapper for setting up and performing a miscellaneous task."""

    _tag_default = 'task'

    def __init__(self, t, **kw):
        """Set defaults attributes: play, steps, and steps names (eg: fetch, compute, backup)."""
        self.__dict__.update(
            jobname = kw.pop('jobname', t.env.OP_JOBNAME),
            iniconf = kw.pop('iniconf', t.env.OP_INICONF),
            play    = kw.pop('play',    False),
            steps   = kw.pop('steps',   tuple()),
            fetch   = kw.pop('fetch',   'fetch'),
            compute = kw.pop('compute', 'compute'),
            backup  = kw.pop('backup',  'backup'),
            starter = kw.pop('starter', False),
            conf    = kw.pop('conf',    ConfigSet()),
        )

        self.ticket  = t
        self.options = kw

        if type(self.steps) is str:
            self.steps = tuple(self.steps.replace(' ', '').split(','))

        config = read_config(self.iniconf)

        upd1 = config.get(self.jobname, dict())
        self.nicedump('Configuration for job ' + self.jobname, **upd1)
        self.conf.update(upd1)

        upd2 = config.get(self.tag, dict())
        self.nicedump('Configuration for task ' + self.tag, **upd2)
        self.conf.update(upd2)

        if 'as_range' in self.conf:
            for kr in self.conf.as_range:
                setattr(self.conf, kr, footprints.util.rangex(getattr(self.conf, kr)))

    @property
    def sh(self):
        return self.ticket.sh

    @property
    def env(self):
        return self.ticket.env

    @property
    def ctx(self):
        return self.ticket.context

    def title(self, **kw):
        """Top title of the current app, including at least one name."""
        jobname = kw.pop('name', self.env.OP_JOBNAME)
        if jobname is None:
            raise StandardError('No job name provided.')

        rundate = kw.pop('date', self.env.OP_RUNDATE)
        if rundate is None:
            raise StandardError('No date provided for this run.')

        self.conf.rundate = rundate

        return self.sh.title(
            'Starting job {0:s} for date {1:s}'.format(
                jobname,
                rundate.isoformat()
            )
        )

    def subtitle(self, *args, **kw):
        """Proxy to :meth:`~vortex.tools.systems.subtitle` method."""
        return self.sh.subtitle(*args, **kw)

    def header(self, *args, **kw):
        """Proxy to :meth:`~vortex.tools.systems.header` method."""
        return self.sh.header(*args, **kw)

    def nicedump(self, msg, **kw):
        """Simple dump of the dict contents with ``msg`` as header."""
        self.header(msg)
        for k, v in sorted(kw.iteritems()):
            print ' +', k.ljust(12), '=', str(v)
        print

    def build(self, **kw):
        """Abstract method: fills the configuration contents."""

        # Change actual rundir if specified
        rundir = kw.get('rundir', None)
        if rundir:
            t = self.ticket
            t.env.RUNDIR = rundir
            t.sh.cd(rundir, create=True)
            t.rundir = t.sh.getcwd()

        # Find a nice place for cocooning
        ctx = self.ticket.context.newcontext(self.tag, focus=True)
        ctx.cocoon()
        logger.info('Task context directory <%s>', self.sh.getcwd())

        # Tentative de détermination plus ou moins hasardeuse de l'étape en cours
        if not self.steps:
            if self.play:
                self.steps = (self.fetch, self.compute, self.backup)
            elif int(self.env.get('SLURM_NPROCS', 1)) > 1:
                self.steps = (self.fetch, self.compute)
            else:
                self.steps = (self.fetch,)
        self.header('Active steps: ' + ' '.join(self.steps))

    def reshape_starter(self, **kw):
        """Make a nice tuple from the starter value and possible preset configurations."""
        self.header('Reshape starter <' + str(self.starter) + '>')
        if self.starter:
            if type(self.starter) is bool:
                self.starter = 'full'
            if type(self.starter) is str:
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

    def defaults(self, extras):
        """Set toolbox defaults, extended with actual arguments ``kw``."""
        t = self.ticket
        toolbox.defaults(
            model      = t.glove.vapp,
            date       = self.conf.rundate,
            cutoff     = self.conf.cutoff,
            geometry   = self.conf.geometry,
            namespace  = 'vortex.cache.fr',
            gnamespace = 'opgco.cache.fr',
        )
        toolbox.defaults(**extras)
        toolbox.defaults.show()

    def op2conf(self):
        """Set some parameters if defined in environment but not in actual conf."""
        autoconf = dict()
        for opvar in sorted([ x for x in self.env.keys() if x.startswith('OP_') ]):
            if opvar not in self.conf:
                autoconf[opvar[3:].lower()] = self.env[opvar]
        if autoconf:
            self.nicedump('Populate conf with op variables', **autoconf)
            self.conf.update(autoconf)

    def conf2io(self):
        """Broadcast IO SERVER configuration values to environment."""
        t = self.ticket
        t.sh.header('IOSERVER Environment')
        t.env.default(VORTEX_IOSERVER_NODES  = self.conf.get('io_nodes', 0))
        t.env.default(VORTEX_IOSERVER_TASKS  = self.conf.get('io_tasks', 6))
        t.env.default(VORTEX_IOSERVER_OPENMP = self.conf.get('io_openmp', 4))

    def register(self, cycle):
        """Register a given GCO cycle."""
        self.header('GCO cycle ' + cycle)
        op.register(self.ticket, cycle)

    def setup(self, **kw):
        """Switch to a new context."""
        self.subtitle('TASK setup')
        self.header('Actual ENV')
        self.env.mydump()
        self.op2conf()
        self.conf2io()
        self.conf.xpid = self.conf.suite
        self.nicedump('Update conf with task arguments', **kw)
        self.conf.update(kw)
        self.register(self.conf.cycle)

    def params(self):
        """Dump actual parameters of the configuration."""
        self.nicedump('Complete parameters', **self.conf)

    def process(self):
        """Abstract method: perform the taks to do."""
        pass

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

    def complete(self):
        """Abstract method: post processing before completion."""
        pass

    def run(self):
        """Execution driver: build, setup, refill, process, complete."""
        self.build(**self.options)
        self.setup(**self.options)
        self.params()
        self.refill()
        self.process()
        self.complete()
