#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re
import io
import collections

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.tools import date
from vortex.util.config import GenericConfigParser, load_template

from gco.tools import genv

OpSetValues = collections.namedtuple('OpSetValues', ['suite', 'vapp', 'vconf'])


def bestdate(day=None, hh=None):
    """Find out the most accurate ``today`` date."""
    return date.synop()


def getopsetfrompath(t, path=None):
    """
    Extract from specified or current ``path`` what could be actual
    ``suite``, ``vapp`` and ``vconf`` values.
    """
    if path is None:
        path = t.sh.pwd()
    lpath = path.split('/')
    if lpath[-1] in ('demo', 'gco', 'genv', 'jobs', 'logs', 'src', 'tasks', 'vortex'):
        lpath.pop()
    return OpSetValues(*lpath[-3:])


def mkjob(t, **kw):
    """Build a complete job file according to a template and some parameters."""
    opts = dict(
        python   = '/usr/bin/python',
        pyopts   = '-u',
        template = 'job.default.tpl',
        inifile  = 'job.default.ini',
        create   = date.at_second().iso8601(),
        mkuser   = t.glove.user,
        mkhost   = t.sh.hostname,
        name     = 'autojob',
        rundate  = None,
        runtime  = None,
        wrap     = True,
    )
    opts.update(kw)

    # Try to find default runtime according to jobname
    if opts['runtime'] is None:
        jtime = re.search('_t?(\d+(?:[:-h]?\d+)?)', opts['name'], re.IGNORECASE)
        if jtime:
            jtime = re.sub('[:-hH]', '', jtime.group(1))
            if len(jtime) > 2:
                jtime = jtime[0:-2] + ':' + jtime[-2:]
            opts['runtime'] = repr(str(date.Time(jtime)))

    corejob = load_template(t, opts['template'])
    opts['tplfile'] = corejob.srcfile

    try:
        iniparser = GenericConfigParser(inifile=opts['inifile'])
        opts['tplinit'] = iniparser.file
        tplconf = iniparser.as_dict()
    except Exception as pb:
        logger.warning('Could not read config %s', str(pb))
        tplconf = dict()

    opts['name'] = re.sub('\.py$', '', opts['name'])

    tplconf = tplconf.get(opts['name'], tplconf.get('void'))

    opset = getopsetfrompath(t)
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
        logger.warning('SLURM_NNODES: %s', str(pb))
        slurm['nn'] = 1

    try:
        slurm['nnp'] = int(re.sub('\(.*$', '', e.SLURM_TASKS_PER_NODE))
        if slurm['nnp'] > 1:
            slurm['nnp'] /= 2
    except Exception as pb:
        logger.warning('SLURM_TASKS_PER_NODE: %s', str(pb))
        slurm['nnp'] = 1

    if 'OMP_NUM_THREADS' in e:
        slurm['openmp'] = e.OMP_NUM_THREADS
    else:
        try:
            guess_cpus  = int(re.sub('\(.*$', '', e.SLURM_JOB_CPUS_PER_NODE))
            guess_tasks = int(re.sub('\(.*$', '', e.SLURM_TASKS_PER_NODE))
            slurm['openmp'] = guess_cpus / guess_tasks
        except Exception as pb:
            logger.warning('SLURM_JOB_CPUS_PER_NODE: %s', str(pb))

    for x in ('nn', 'nnp', 'openmp'):
        if x in kw:
            slurm[x] = kw[x]
            del kw[x]

    return slurm, kw


def gget_resource_exists(t, ggetfile):
    """Check whether a gget resource exists in the current path or not."""

    if t.sh.path.exists(ggetfile):
        return True

    if not ggetfile.startswith('clim'):
        return False

    # all monthly clim files must be present
    clims = [ ggetfile + '.m{0:02d}'.format(m) for m in range(1, 13) ]
    missing = [ clim for clim in clims if not t.sh.path.isfile(clim) ]
    if missing:
        print 'missing :', missing
        return False
    return True


def freeze_cycle(t, cycle, force=False, verbose=True, genvpath='genv', gcopath='gco', logpath=None):
    """
    Retrieve a copy of all relevant gco resources for a cycle.
    The genv reference is kept in ./genv/cycle.genv
    The resources are stored in current ``gcopath`` target path.
    Use ``force=True`` to continue in spite of errors.
    """
    tg = t.sh.target()

    defs = genv.autofill(cycle)

    # Save genv raw output in specified `genvpath` folder
    t.sh.mkdir(genvpath)
    genvconf = t.sh.path.join(genvpath, cycle + '.genv')
    with io.open(genvconf, mode='w', encoding='utf-8') as fp:
        fp.write(unicode(genv.as_rawstr(cycle=cycle)))

    # Start a log
    if logpath is None:
        logpath = t.sh.path.join(genvpath, 'freeze_cycle.log')
    log = io.open(logpath, mode='a', encoding='utf-8')
    log.write(unicode(t.line))
    log.write(unicode(t.prompt + ' ' + cycle + ' upgrade ' + date.now().reallynice() + "\n"))

    # Remove unwanted definitions
    for prefix in ('PACK', 'SRC'):
        for key in defs.keys():
            if key.startswith(prefix):
                del defs[key]

    # Build a list of unique resource names
    ggetnames = set()
    for v in defs.values():
        if isinstance(v, basestring):
            ggetnames.add(v)
        else:
            ggetnames |= set(v)

    # Could filter out here unwanted extensions

    # Perform gget on all resources to target directory
    t.sh.cd(gcopath, create=True)
    gcmd  = tg.get('gco:ggetcmd', 'gget')
    gpath = tg.get('gco:ggetpath', '')
    gtool = t.sh.path.join(gpath, gcmd)

    increase = 0
    details  = dict(retrieved=list(), inplace=list(), failed=list())

    for name in sorted(list(ggetnames)):
        if verbose:
            print t.line
            print name, '...',
        if gget_resource_exists(t, name):
            if verbose:
                print 'already there'
                t.sh.ll(name)
            details['inplace'].append(name)
        else:
            try:
                t.sh.spawn([gtool, name], output=False)
                increase += t.sh.size(name)
                if verbose:
                    print 'ok'
                    t.sh.ll(name)
                details['retrieved'].append(name)
            except StandardError:
                if verbose:
                    print 'failed &',
                details['failed'].append(name)
                if force:
                    print 'continue'
                else:
                    print 'abort'
                    log.write(unicode('Aborted on ' + name + "\n"))
                    log.close()
                    raise

    if verbose:
        print t.line

    for k, v in details.items():
        log.write(unicode('Number of items ' + k + ' = ' + str(len(v)) + "\n"))
        for item in v:
            log.write(unicode(' > '  + item + "\n"))

    log.close()

    return (increase, details)
