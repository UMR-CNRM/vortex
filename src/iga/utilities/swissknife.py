#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re

import collections
OpSetValues = collections.namedtuple('OpSetValues', ['suite', 'vapp', 'vconf'])

from vortex.tools import date
from vortex.tools.config import GenericConfigParser, loadtemplate
from vortex.autolog import logdefault as logger


def bestdate(day=None, hh=None):
    """Find out the most accurate ``today`` date."""
    return date.synop()


def getopsetfrompath(sh, path=None):
    """
    Extract from specified or current ``path`` what could be actual
    ``suite``, ``vapp`` and ``vconf`` values."""
    if path is None:
        path = sh.pwd()
    lpath = path.split('/')
    if lpath[-1] in ('demo', 'gco', 'genv', 'jobs', 'logs', 'src', 'tasks', 'vortex'):
        lpath.pop()
    return OpSetValues(*lpath[-3:])


def mkjob(t, **kw):
    """Build a complete job file according to a template and some parameters."""
    opts = dict(
        template = 'job.default.tpl',
        inifile  = 'job.default.ini',
        create   = date.atsecond().iso8601(),
        mkuser   = t.glove.user,
        name = 'autojob',
        wrap = True,
    )
    opts.update(kw)

    corejob = loadtemplate(opts['template'])
    opts['tplfile'] = corejob.srcfile

    try:
        iniparser = GenericConfigParser(inifile=opts['inifile'])
        opts['tplinit'] = iniparser.file
        tplconf = iniparser.as_dict()
    except Exception as pb:
        logger.warning('Could not read config %s', str(pb))
        tplconf = dict()

    tplconf = tplconf.get(opts['name'], dict())

    opset = getopsetfrompath(t.sh)
    tplconf.setdefault('suite',   opset.suite)
    tplconf.setdefault('suitebg', opset.suite)
    tplconf.setdefault('vapp',    opset.vapp)
    tplconf.setdefault('vconf',   opset.vconf)

    tplconf.update(opts)

    tplconf.setdefault('file', opts['name'] + '.py')

    corejob = corejob.substitute(tplconf)

    if opts['wrap']:
        def autojob():
            eval(compile(corejob, 'compile.mkjob.log', 'exec'))
        objcode = autojob
    else:
        objcode = corejob

    return objcode, tplconf


def slurm_parameters(t, **kw):
    """Figure out what could be nnodes, ntasks and openmp actual values."""
    e = t.env
    slurm = dict(
        openmp = 1,
    )
    try:
        slurm['nn'] = int(e.SLURM_NNODES)
    except Exception as pb:
        print '[WARNING] SLURM_NNODES:', pb
        slurm['nn'] = 1
    try:
        slurm['nnp'] = int(re.sub('\(.*$', '', e.SLURM_TASKS_PER_NODE))
        if slurm['nnp'] > 1:
            slurm['nnp'] = slurm['nnp'] / 2
    except Exception as pb:
        print '[WARNING] SLURM_TASKS_PER_NODE:', pb
        slurm['nnp'] = 1
    if 'OMP_NUM_THREADS' in e:
        slurm['openmp'] = e.OMP_NUM_THREADS
    else:
        try:
            guess_cpus  = int(re.sub('\(.*$', '', e.SLURM_JOB_CPUS_PER_NODE))
            guess_tasks = int(re.sub('\(.*$', '', e.SLURM_TASKS_PER_NODE))
            slurm['openmp'] = guess_cpus / guess_tasks
        except Exception as pb:
            print '[WARNING] SLURM_JOB_CPUS_PER_NODE:', pb

    for x in ('nn', 'nnp', 'openmp'):
        if x in kw:
            slurm[x] = kw[x]
            del kw[x]

    return slurm, kw


class Application(object):
    """
    Wrapper for setting up and performing a miscellaneous task.
    The abstract interface is the same as :class:`vortex.layout.nodes.Configuration`.
    """
    def __init__(self, t, **kw):
        self.__dict__.update(kw)
        self.ticket = t

    def title(self, *args, **kw):
        """Proxy to :meth:`~vortex.tools.systems.title` method."""
        return self.ticket.sh.title(*args, **kw)

    def setup(self, **kw):
        """Abstract method: defines the interaction with vortex env."""
        pass

    def refill(self, **kw):
        """Populates the op vortex cache with expected input flow data."""
        pass

    def build(self, **kw):
        """Abstract method: fills the configuration contents."""
        pass

    def process(self, **kw):
        """Abstract method: perform the taks to do."""
        pass

    def complete(self, **kw):
        """Abstract method: post processing before completion."""
        pass
