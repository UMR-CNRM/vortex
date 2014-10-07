#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

from vortex.autolog import logdefault as logger

from footprints.util import rangex


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


class ConfigSet(object):
    """Simple struct_like object."""
    def __init__(self, **kw):
        self.update(kw)

    def update(self, *args, **kw):
        for a in args:
            self.__dict__.update(a)
        self.__dict__.update(kw)

    def as_list(self, item):
        v = getattr(self, item)
        if type(v) is str:
            v = v.replace(' ', '').split(',')
        return v


class Application(object):
    """
    Wrapper for setting up and performing a miscellaneous task.
    The abstract interface is the same as :class:`vortex.layout.nodes.Configuration`.
    """
    def __init__(self, t, **kw):
        """Set defaults attributes: play, steps, and steps names (eg: fetch, compute, backup)."""
        self.__dict__.update(
            tag     = t.env.OP_JOBNAME,
            iniconf = t.env.OP_INICONF,
            play    = False,
            steps   = tuple(),
            fetch   = 'fetch',
            compute = 'compute',
            backup  = 'backup',
            conf    = ConfigSet(),
        )
        self.__dict__.update(kw)
        self.ticket = t
        if type(self.steps) is str:
            self.steps = tuple(self.steps.split(','))
        self.conf.update(read_config(self.iniconf).get(self.tag))
        for kr in self.conf.as_list('as_range'):
            setattr(self.conf, kr, rangex(getattr(self.conf, kr)))

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

    def run(self, **kw):
        """Execution driver: build, refill, setup, process, complete."""
        self.build(**kw)
        self.refill()
        self.setup(**kw)
        self.process()
        self.complete()

    def build(self, **kw):
        """Abstract method: fills the configuration contents."""

        # Tentative de détermination plus ou moins hasardeuse de l'étape en cours
        if self.steps:
            self.steps = tuple(self.steps)
        else:
            if self.play:
                self.steps = (self.fetch, self.compute, self.backup)
            elif int(self.env.get('SLURM_NPROCS', 1)) > 1:
                self.steps = (self.fetch, self.compute)
            else:
                self.steps = tuple(kw.pop('args', [ self.fetch ]))
        self.header('Active Steps: ' + ' '.join(self.steps))

    def refill(self, **kw):
        """Populates the op vortex cache with expected input flow data."""
        pass

    def setup(self, **kw):
        """Abstract method: defines the interaction with vortex env."""
        pass

    def process(self):
        """Abstract method: perform the taks to do."""
        pass

    def complete(self):
        """Abstract method: post processing before completion."""
        pass

