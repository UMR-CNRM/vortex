#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re
import io
import collections
import string

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
        python    = '/usr/bin/python',
        pyopts    = '-u',
        profile   = 'research',
        template  = 'job.default.tpl',
        inifile   = 'job.default.ini',
        exclusive = 'exclusive',
        create    = date.at_second().iso8601(),
        mkuser    = t.glove.user,
        mkhost    = t.sh.hostname,
        name      = 'autojob',
        home      = t.env.HOME,
        rundate   = None,
        runtime   = None,
        taskconf  = None,
        wrap      = True,
        verbose   = True,
    )
    opts.update(kw)

    # Fix actual options of the create process
    opts.setdefault('mkopts', str(kw))

    # Switch verbosity from boolean to plain string
    if type(opts['verbose']) is bool:
        if opts['verbose']:
            opts['verbose'] = 'verbose'
        else:
            opts['verbose'] = 'noverbose'

    # Fix taskconf as task by default
    if opts['taskconf'] is None:
        opts['taskconf'] = opts['task']

    # Try to find default runtime according to jobname
    if opts['runtime'] is None and opts['rundate'] is None:
        jtime = re.search('_t?(\d+(?:[:-h]?\d+)?)', opts['name'], re.IGNORECASE)
        if jtime:
            jtime = re.sub('[:-hH]', '', jtime.group(1))
            if len(jtime) > 2:
                jtime = jtime[0:-2] + ':' + jtime[-2:]
            opts['runtime'] = str(date.Time(jtime))

    for xopt in ('rundate', 'runtime'):
        if type(opts[xopt]) is str:
            opts[xopt] = "'" + opts[xopt] + "'"

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

    tplconf = tplconf.get(opts['profile'], tplconf.get('void'))

    opset = getopsetfrompath(t)

    tplconf.setdefault('suite',   opset.suite)
    tplconf.setdefault('suitebg', opset.suite)
    tplconf.setdefault('vapp',    opset.vapp)
    tplconf.setdefault('vconf',   opset.vconf)

    tplconf.update(opts)

    tplconf.setdefault('file', opts['name'] + '.py')

    jobconf = '../conf/{0:s}_{1:s}_{2:s}.ini'.format(tplconf['vapp'], tplconf['vconf'], tplconf['taskconf'])
    if t.sh.path.exists(jobconf):
        t.sh.header('Add ' + jobconf)
        jobparser = GenericConfigParser(inifile=jobconf)
        tplconf.update(jobparser.as_dict().get(opts['name'], dict()))

    pycode = string.Template(corejob.substitute(tplconf)).substitute(tplconf)

    if opts['wrap']:
        def autojob():
            eval(compile(pycode, 'compile.mkjob.log', 'exec'))
        objcode = autojob
    else:
        objcode = pycode

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
    except Exception as pb:
        logger.warning('SLURM_TASKS_PER_NODE: %s', str(pb))
        slurm['nnp'] = 1

    if 'OMP_NUM_THREADS' in e:
        slurm['openmp'] = e.OMP_NUM_THREADS
    else:
        try:
            guess_cpus  = int(re.sub('\(.*$', '', e.SLURM_JOB_CPUS_PER_NODE)) / 2
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


def freeze_cycle(t, cycle, force=False, verbose=True, genvpath='genv', gcopath='gco/tampon', logpath=None):
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
    details  = dict(retrieved=list(), inplace=list(), failed=list(), expanded=list())

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
                    t.sh.readonly(name)
                    t.sh.ll(name)
                details['retrieved'].append(name)
                if name.endswith('.tgz'):
                    subpath = name.rstrip('.tgz')
                    locpath = t.sh.getcwd()
                    t.sh.cd(subpath, create=True)
                    t.sh.untar('../' + name, output=False)
                    for subfile in t.sh.glob('*'):
                        details['expanded'].append(t.sh.path.join(subpath, subfile))
                        t.sh.readonly(subfile)
                    t.sh.cd(locpath)
                    t.sh.remove(name)
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
