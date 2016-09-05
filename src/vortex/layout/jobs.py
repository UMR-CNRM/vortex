#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
This modules defines helpers to build job's scripts.
"""

from __future__ import print_function

import ast
import collections
import functools
import importlib
import re
import string
import sys
import traceback

import footprints
from footprints.stdtypes import FPSet

import vortex
from vortex.tools import date
from vortex.util.config import ExtendedReadOnlyConfigParser, load_template

#: Export nothing
__all__ = []

logger = footprints.loggers.getLogger(__name__)


_RE_VORTEXDATE = re.compile(r'_(?P<date>\d{8})T(?P<hh>\d{2})(?P<mm>\d{2})(?P<cutoff>[AP])',
                            re.IGNORECASE)
_RE_OPTIME = re.compile(r'_t?(?P<hh>\d{2})(?:[:h-]?(?P<mm>\d{2})?)', re.IGNORECASE)
_RE_MEMBER = re.compile(r'_mb(?P<member>\d+)', re.IGNORECASE)


_JobBasicConf = collections.namedtuple('_JobBasicConf', ['xpid', 'vapp', 'vconf'])


def _guess_vapp_vconf_xpid(t, path=None):
    """
    Extract from specified or current ``path`` what could be actual
    ``xpid``, ``vapp`` and ``vconf`` values.
    """
    if path is None:
        path = t.sh.pwd()
    lpath = path.split('/')
    if lpath[-1] in ('demo', 'gco', 'genv', 'jobs', 'logs', 'src', 'tasks', 'vortex'):
        lpath.pop()
    return _JobBasicConf(*lpath[-3:])


def mkjob(t, **kw):
    """Build a complete job file according to a template and some parameters."""
    opts = dict(
        python    = t.sh.which('python'),
        pyopts    = '-u',
        profile   = 'void',
        inifile   = '@job-default.ini',
        create    = date.at_second().iso8601(),
        mkuser    = t.glove.user,
        mkhost    = t.sh.hostname,
        name      = 'autojob',
        home      = t.env.HOME,
        rundate   = None,
        runtime   = None,
        member    = None,
        taskconf  = None,
        wrap      = True,
        verbose   = True,
    )
    opts.update(kw)

    # Fix actual options of the create process
    opts.setdefault('mkopts', str(kw))

    # Switch verbosity from boolean to plain string
    if isinstance(opts['verbose'], bool):
        opts['verbose'] = 'verbose' if opts['verbose'] else 'noverbose'

    # Fix the task's name
    opts['name'] = re.sub(r'\.py$', '', opts['name'])
    opts.setdefault('file', opts['name'] + '.py')

    # Try to find default rundate/runtime according to the jobname
    if opts['runtime'] is None and opts['rundate'] is None:
        vtxdate = _RE_VORTEXDATE.search(opts['name'])
        if vtxdate:
            opts['rundate'] = str(date.Date(vtxdate.group('date') +
                                            vtxdate.group('hh') + vtxdate.group('mm')))
            opts['runtime'] = str(date.Time('{:s}:{:s}'.format(vtxdate.group('hh'),
                                                               vtxdate.group('mm'))))
            if 'cutoff' not in opts:
                opts['cutoff'] = dict(A='assim', P='production').get(vtxdate.group('cutoff'))
            opts['name'] = _RE_VORTEXDATE.sub('', opts['name'])
        else:
            optime = _RE_OPTIME.search(opts['name'])
            if optime:
                opts['runtime'] = str(date.Time('{:s}:{:s}'.format(optime.group('hh'),
                                                                   optime.group('mm'))))
                opts['name'] = _RE_OPTIME.sub('', opts['name'])

    for xopt in ('rundate', 'runtime'):
        if isinstance(opts[xopt], basestring):
            opts[xopt] = "'" + opts[xopt] + "'"

    # Try to find default member number according to the jobname
    if opts['member'] is None:
        mblookup = _RE_MEMBER.search(opts['name'])
        if mblookup:
            opts['member'] = int(mblookup.group('member'))
            opts['name'] = _RE_MEMBER.sub('', opts['name'])

    # Add the current working directory
    opts['pwd'] = t.sh.getcwd()

    try:
        iniparser = ExtendedReadOnlyConfigParser(inifile=opts['inifile'])
        opts['tplinit'] = iniparser.file
        tplconf = iniparser.as_dict()
    except Exception as pb:
        logger.warning('Could not read config %s', str(pb))
        tplconf = dict()

    tplconf = tplconf.get(opts['profile'])

    opset = _guess_vapp_vconf_xpid(t)

    tplconf.setdefault('xpid', opset.xpid)
    tplconf.setdefault('vapp', opset.vapp)
    tplconf.setdefault('vconf', opset.vconf)

    tplconf.update(opts)

    tplconf.setdefault('file', opts['name'] + '.py')

    if tplconf['taskconf']:
        jobconf = '../conf/{0:s}_{1:s}_{2:s}.ini'.format(tplconf['vapp'], tplconf['vconf'],
                                                         tplconf['taskconf'])
    else:
        jobconf = '../conf/{0:s}_{1:s}.ini'.format(tplconf['vapp'], tplconf['vconf'])

    if t.sh.path.exists(jobconf):
        t.sh.header('Add ' + jobconf)
        jobparser = ExtendedReadOnlyConfigParser(inifile=jobconf)
        tplconf.update(jobparser.as_dict().get(opts['name'], dict()))

    corejob = load_template(t, tplconf['template'])
    opts['tplfile'] = corejob.srcfile
    pycode = string.Template(corejob.substitute(tplconf)).substitute(tplconf)

    if opts['wrap']:
        def autojob():
            eval(compile(pycode, 'compile.mkjob.log', 'exec'))
        objcode = autojob
    else:
        # Using ast ensures that a valid python script was generated
        ast.parse(pycode, 'compile.mkjob.log', 'exec')
        objcode = pycode

    return objcode, tplconf


class JobAssistant(footprints.FootprintBase):
    """Class in charge of setting various session and environment settings for a Vortex job."""

    _abstract  = True
    _collector = ('jobassistant',)
    _footprint = dict(
        info = 'Abstract JobAssistant',
        attr = dict(
            kind = dict(),
            modules = dict(
                type = FPSet,
                optional = True,
                default = FPSet(()),
            ),
            addons = dict(
                type = FPSet,
                optional = True,
                default = FPSet(()),
            ),
            special_prefix = dict(
                optional = True,
                default = 'op_',
            )
        ),
    )

    _P_SESSION_INFO_FMT = '+ {0:14s} = {1!s}'
    _P_ENVVAR_FMT = '+ {0:s} = {1!s}'
    _P_MODULES_FMT = '+ {0:s}'
    _P_ADDON_FMT = '+ Add-on {0:10s} = {1!r}'

    def __init__(self, *args, **kw):
        super(JobAssistant, self).__init__(*args, **kw)
        # By default, no error code is thrown away
        self.unix_exit_code = 0

    @staticmethod
    def _printfmt(fmt, *kargs, **kwargs):
        print(fmt.format(*kargs, **kwargs))

    @classmethod
    def _print_session_info(cls, t):
        """Display informations about the current session."""

        locprint = functools.partial(cls._printfmt, cls._P_SESSION_INFO_FMT)

        t.sh.header('Toolbox description')

        locprint('Root directory', t.glove.siteroot)
        locprint('Path directory', t.glove.sitesrc)
        locprint('Conf directory', t.glove.siteconf)

        t.sh.header('Session description')

        locprint('Session Ticket', t)
        locprint('Session Glove', t.glove)
        locprint('Session System', t.sh)
        locprint('Session Env', t.env)

        t.sh.header('Target description')

        tg = t.sh.target()
        locprint('Target name', tg.hostname)
        locprint('Target system', tg.sysname)
        locprint('Target inifile', tg.inifile)

    @classmethod
    def _print_toolbox_settings(cls, t):
        """Display the toolbox settings."""
        t.sh.header('Toolbox module settings')
        vortex.toolbox.show_toolbox_settings()

    @classmethod
    def print_somevariables(cls, t, prefix=''):
        """Print some of the environment variables."""
        prefix = prefix.upper()
        filtered = sorted([x for x in t.env.keys() if x.startswith(prefix)])
        if filtered:
            t.sh.header('{:s} environment variables'.format(prefix if prefix else 'All'))
            maxlen = max([len(x) for x in filtered])
            for var_name in sorted([x for x in t.env.keys() if x.startswith(prefix)]):
                print(cls._P_ENVVAR_FMT.format(var_name.ljust(maxlen),
                                               t.env.native(var_name)))

    def _add_specials(self, t, prefix=None, **kw):
        """Print some of the environment variables."""
        prefix = prefix or self.special_prefix
        specials = kw.get('actual', dict())
        filtered = {k: v for k, v in specials.iteritems() if k.startswith(prefix)}
        if filtered:
            t.sh.header('Copying actual {:s} variables to the environment'.format(prefix))
            t.env.update({k: v for k, v in specials.iteritems() if k.startswith(prefix)})
            self.print_somevariables(t, prefix=prefix)

    def _modules_preload(self, t):
        """Import all the modules listed in the footprint."""
        t.sh.header('External imports')
        for module in sorted(self.modules):
            importlib.import_module(module)
            print(self._P_MODULES_FMT.format(module))

    def _addons_preload(self, t):
        """Load shell addons."""
        t.sh.header('Add-ons to the shell')
        for addon in self.addons:
            shadd = footprints.proxy.addon(kind=addon, shell=t.sh)
            print(self._P_ADDON_FMT.format(addon.upper(), shadd))

    def _system_setup(self, t, **kw):
        """Set usual settings for the system shell."""
        t.sh.header("Session's basic setup")
        t.sh.setulimit('stack')

    def _early_session_setup(self, t, **kw):
        """Create a now session, set important things, ..."""
        specials = kw.get('actual', dict())
        t.glove.vapp  = kw.get('vapp', specials.get(self.special_prefix + 'vapp', None))
        t.glove.vconf = kw.get('vconf', specials.get(self.special_prefix + 'vconf', None))
        return t

    def _extra_session_setup(self, t, **kw):
        """Additional setup for the session."""
        myrundir = kw.get('rundir', None) or t.env.TMPDIR
        if myrundir:
            t.rundir = kw.get('rundir', myrundir)
            print('+ Current rundir <%s>' % (t.rundir,))

    def _env_setup(self, t, **kw):
        """Session's environment setup."""
        t.env.verbose(True, t.sh)
        self._add_specials(t, **kw)

    def _toolbox_setup(self, t, **kw):
        """Toolbox default setup."""
        vortex.toolbox.active_verbose = True
        vortex.toolbox.active_now = True
        vortex.toolbox.active_clear = True

    def register_cycle(self, cycle):
        """A callback to register GCO cycles."""
        t = vortex.ticket()
        from gco.tools import genv
        if cycle in genv.cycles():
            logger.info('Cycle %s already registered', cycle)
        else:
            genv.autofill(cycle, cacheroot=t.rundir, writes_dump=True)
            print(genv.as_rawstr(cycle=cycle))

    def setup(self, **kw):
        """This is the main method. it setups everything in the session."""
        # We need the root session
        t = vortex.ticket()
        t.system().prompt = t.prompt
        # But a new session can be created here:
        t = self._early_session_setup(t, **kw)
        # Then, go on with initialisations...
        self._system_setup(t)
        self._print_session_info(t)
        self._env_setup(t, **kw)
        self._modules_preload(t)
        self._addons_preload(t)
        self._extra_session_setup(t, **kw)
        self._toolbox_setup(t, **kw)
        self._print_toolbox_settings(t)
        # Begin signal handling
        t.sh.signal_intercept_on()
        return t, t.env, t.sh

    @staticmethod
    def add_extra_traces(t):
        """Switch the system shell to verbose mode."""
        t.sh.trace = True

    def complete(self):
        """Should be called when a job finishes successfully"""
        pass

    def fulltraceback(self, latest_error=None):
        """Produce some nice traceback at the point of failure.

        :param Exception last_error: The latest caught exception.
        """
        t = vortex.ticket()
        t.sh.title('Handling exception')
        (exc_type, exc_value, exc_traceback) = sys.exc_info()  # @UnusedVariable
        print('Exception type: {!s}'.format(exc_type))
        print('Exception info: {!s}'.format(latest_error))
        t.sh.header('Traceback Error / BEGIN')
        print("\n".join(traceback.format_tb(exc_traceback)))
        t.sh.header('Traceback Error / END')

    def rescue(self):
        """Called at the end of a job when something went wrong."""
        self.unix_exit_code = 1

    def finalise(self):
        """Called whenever a job finishes (either successfully or badly)."""
        t = vortex.ticket()
        t.sh.signal_intercept_off()
        t.close()
        if self.unix_exit_code:
            print('Something went wrong :-(')
            exit(self.unix_exit_code)


class MtoolReadyJobAssistant(JobAssistant):
    """Class in charge of setting various session and environment settings for a Vortex job.

    This specialised version, take advantages of the variables automatically
    added by MTOOL.
    """

    _footprint = dict(
        info = 'MTOOL aware JobAssistant',
        attr = dict(
            kind = dict(
                values = ['mtool', ]
            ),
        ),
    )

    def _extra_session_setup(self, t, **kw):
        # Set the rundir according to MTTOL's spool
        t.rundir = t.env.MTOOL_STEP_SPOOL
        print('+ Current rundir <{:s}>'.format(t.rundir))
        # Check that the log directory exists
        if "MTOOL_STEP_LOGFILE" in t.env:
            logfile = t.sh.path.normpath(t.env.MTOOL_STEP_LOGFILE)
            logdir = t.sh.path.dirname(logfile)
            if not t.sh.path.isdir(logdir):
                t.sh.mkdir(logdir)
            print('+ Current logfile <{:s}>'.format(logfile))

    def complete(self):
        """Should be called when a job finishes successfuly"""
        super(MtoolReadyJobAssistant, self).complete()
        t = vortex.ticket()
        t.sh.cd(t.env.MTOOL_STEP_SPOOL)

    def rescue(self):
        """Called at the end of a job when something went wrong.

        It backups the session's rundir and clean promises.
        """
        super(MtoolReadyJobAssistant, self).rescue()
        t = vortex.ticket()
        t.sh.cd(t.env.MTOOL_STEP_SPOOL)
        vortex.toolbox.rescue(bkupdir=t.env.MTOOL_STEP_ABORT)
