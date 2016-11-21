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
from footprints import proxy as fpx
from footprints.stdtypes import FPSet

import vortex
from vortex.tools import date
from vortex.util.config import ExtendedReadOnlyConfigParser, load_template
from vortex.util.decorators import nicedeco

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


@nicedeco
def _extendable(func):
    """Decorator for some of the JobAssistant method

    The added behaviour is to look into the plugins list and call appropriate
    methods upon them.
    """
    def new_me(self, *kargs, **kw):
        # Call the original function, save the result
        res = func(self, *kargs, **kw)
        # Automatically add the session (if missing)
        dargs = list(kargs)
        if not (dargs and isinstance(dargs[0], vortex.sessions.Ticket)):
            dargs.insert(0, vortex.sessions.current())
        # Go through the plugins and look for available methods
        plugable_n = 'plugable_' + func.__name__.lstrip('_')
        for p in [p for p in self.plugins if hasattr(p, plugable_n)]:
            # If the previous result was a session, use it...
            if isinstance(res, vortex.sessions.Ticket):
                dargs[0] = res
            res = getattr(p, plugable_n)(*dargs, **kw)
        return res
    return new_me


class JobAssistant(footprints.FootprintBase):
    """Class in charge of setting various session and environment settings for a Vortex job."""

    _collector = ('jobassistant',)
    _footprint = dict(
        info = 'Abstract JobAssistant',
        attr = dict(
            kind = dict(
                values = ['generic', 'minimal']
            ),
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
        self._plugins = list()

    @property
    def plugins(self):
        return self._plugins

    def add_plugin(self, kind, **kwargs):
        self._plugins.append(fpx.jobassistant_plugin(kind=kind, masterja=self,
                                                     **kwargs))

    def __getattr__(self, name):
        """Search the plugins for unknown methods."""
        if not (name.startswith('_') or name.startswith('plugable')):
            for plugin in self.plugins:
                if hasattr(plugin, name):
                    return getattr(plugin, name)
        raise AttributeError('Attribute not found.')

    @staticmethod
    def _printfmt(fmt, *kargs, **kwargs):
        print(fmt.format(*kargs, **kwargs))

    @_extendable
    def _print_session_info(self, t):
        """Display informations about the current session."""

        locprint = functools.partial(self._printfmt, self._P_SESSION_INFO_FMT)

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

    @_extendable
    def _print_toolbox_settings(self, t):
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

    @_extendable
    def _add_specials(self, t, prefix=None, **kw):
        """Print some of the environment variables."""
        prefix = prefix or self.special_prefix
        specials = kw.get('actual', dict())
        filtered = {k: v for k, v in specials.iteritems() if k.startswith(prefix)}
        if filtered:
            t.sh.header('Copying actual {:s} variables to the environment'.format(prefix))
            t.env.update({k: v for k, v in specials.iteritems() if k.startswith(prefix)})
            self.print_somevariables(t, prefix=prefix)

    @_extendable
    def _modules_preload(self, t):
        """Import all the modules listed in the footprint."""
        t.sh.header('External imports')
        for module in sorted(self.modules):
            importlib.import_module(module)
            print(self._P_MODULES_FMT.format(module))

    @_extendable
    def _addons_preload(self, t):
        """Load shell addons."""
        t.sh.header('Add-ons to the shell')
        for addon in self.addons:
            shadd = footprints.proxy.addon(kind=addon, shell=t.sh)
            print(self._P_ADDON_FMT.format(addon.upper(), shadd))

    @_extendable
    def _system_setup(self, t, **kw):
        """Set usual settings for the system shell."""
        t.sh.header("Session's basic setup")
        t.sh.setulimit('stack')
        t.sh.setulimit('memlock')

    @_extendable
    def _early_session_setup(self, t, **kw):
        """Create a now session, set important things, ..."""
        specials = kw.get('actual', dict())
        t.glove.vapp  = kw.get('vapp', specials.get(self.special_prefix + 'vapp', None))
        t.glove.vconf = kw.get('vconf', specials.get(self.special_prefix + 'vconf', None))
        return t

    @_extendable
    def _extra_session_setup(self, t, **kw):
        """Additional setup for the session."""
        pass

    @_extendable
    def _env_setup(self, t, **kw):
        """Session's environment setup."""
        t.env.verbose(True, t.sh)
        self._add_specials(t, **kw)

    @_extendable
    def _toolbox_setup(self, t, **kw):
        """Toolbox default setup."""
        vortex.toolbox.active_verbose = True
        vortex.toolbox.active_now = True
        vortex.toolbox.active_clear = True

    @_extendable
    def _actions_setup(self, t, **kw):
        """Setup the action dispatcher."""
        pass

    def setup(self, **kw):
        """This is the main method. it setups everything in the session."""
        # We need the root session
        t = vortex.ticket()
        t.system().prompt = t.prompt
        # But a new session can be created here:
        t = self._early_session_setup(t, **kw)
        # Then, go on with initialisations...
        self._system_setup(t)  # Tweak the session's System object
        self._print_session_info(t)  # Print some info about the session
        self._env_setup(t, **kw)  # Setup the session's Environment object
        self._modules_preload(t)  # Load a few modules
        self._addons_preload(t)  # Active some shell addons
        self._extra_session_setup(t, **kw)  # Some extra configuration on the session
        self._toolbox_setup(t, **kw)  # Setup toolbox settings
        self._print_toolbox_settings(t)  # Print a summary of the toolbox settings
        self._actions_setup(t, **kw)  # Setup the actionDispatcher
        # Begin signal handling
        t.sh.signal_intercept_on()
        return t, t.env, t.sh

    @_extendable
    def add_extra_traces(self, t):
        """Switch the system shell to verbose mode."""
        t.sh.trace = True

    @_extendable
    def register_cycle(self, cycle):
        """A callback to register GCO cycles."""
        from gco.tools import genv
        if cycle in genv.cycles():
            logger.info('Cycle %s already registered', cycle)
        else:
            genv.autofill(cycle)
            print(genv.as_rawstr(cycle=cycle))

    @_extendable
    def complete(self):
        """Should be called when a job finishes successfully"""
        pass

    @_extendable
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

    @_extendable
    def rescue(self):
        """Called at the end of a job when something went wrong."""
        self.unix_exit_code = 1

    @_extendable
    def finalise(self):
        """Called whenever a job finishes (either successfully or badly)."""
        pass

    def close(self):
        """This must be the last called method whenever a job finishes."""
        t = vortex.ticket()
        t.sh.signal_intercept_off()
        t.close()
        if self.unix_exit_code:
            print('Something went wrong :-(')
            exit(self.unix_exit_code)


class JobAssistantPlugin(footprints.FootprintBase):

    _conflicts = []
    _abstract  = True
    _collector = ('jobassistant_plugin',)
    _footprint = dict(
        info = 'Abstract JobAssistant Plugin',
        attr = dict(
            kind = dict(),
            masterja = dict(
                type=JobAssistant,
            ),
        ),
    )

    def __init__(self, *kargs, **kwargs):
        super(JobAssistantPlugin, self).__init__(*kargs, **kwargs)
        # Check for potential conflicts
        for conflicting in self._conflicts:
            if conflicting in self.masterja.plugins:
                raise RuntimeError('"{:s}" conflicts wit "{:s}"'.format(self.kind, conflicting))


class JobAssistantTmpdirPlugin(JobAssistantPlugin):

    _conflicts = ['mtool', ]
    _footprint = dict(
        info = 'JobAssistant TMPDIR Plugin',
        attr = dict(
            kind = dict(
                values = ['tmpdir', ]
            ),
        ),
    )

    def plugable_extra_session_setup(self, t, **kw):
        """Set the rundir according to the TMPDIR variable."""
        myrundir = kw.get('rundir', None) or t.env.TMPDIR
        if myrundir:
            t.rundir = kw.get('rundir', myrundir)
            print('+ Current rundir <%s>' % (t.rundir,))


class JobAssistantMtoolPlugin(JobAssistantPlugin):

    _conflicts = ['tmpdir', ]

    _footprint = dict(
        info = 'JobAssistant MTOOL Plugin',
        attr = dict(
            kind = dict(
                values = ['mtool', ]
            ),
            step = dict(
                type=int,
            ),
            stepid = dict(
            ),
        ),
    )

    @property
    def mtool_steps(self):
        steps_map = {'fetch': ('early-fetch', ),
                     'compute': ('early-fetch', 'fetch', 'compute', 'backup'),
                     'backup': ('backup', 'late-backup'), }
        try:
            return steps_map[self.stepid]
        except KeyError:
            logger.error("Unknown MTOOL step: %s", self.stepid)
            return ()

    def plugable_extra_session_setup(self, t, **kw):
        """Set the rundir according to MTTOL's spool."""
        t.rundir = t.env.MTOOL_STEP_SPOOL
        t.sh.cd(t.rundir)
        print('+ Current rundir <{:s}>'.format(t.rundir))
        # Load the session's data store
        if self.step > 1:
            t.datastore.pickle_load()
            print('+ The datastore was read from disk.')
        # Check that the log directory exists
        if "MTOOL_STEP_LOGFILE" in t.env:
            logfile = t.sh.path.normpath(t.env.MTOOL_STEP_LOGFILE)
            logdir = t.sh.path.dirname(logfile)
            if not t.sh.path.isdir(logdir):
                t.sh.mkdir(logdir)
            print('+ Current logfile <{:s}>'.format(logfile))

    def plugable_toolbox_setup(self, t, **kw):
        """Toolbox MTOOL setup."""
        if self.stepid == 'compute':
            # No network activity during the compute step + promises already made
            vortex.toolbox.active_promise = False
            vortex.toolbox.active_insitu = True
            vortex.toolbox.active_incache = True

    def plugable_complete(self, t):
        """Should be called when a job finishes successfully"""
        t.sh.cd(t.env.MTOOL_STEP_SPOOL)
        # Dump the session datastore in the rundir
        t.datastore.pickle_dump()
        print('+ The datastore is dumped to disk')

    def plugable_rescue(self, t):
        """Called at the end of a job when something went wrong.

        It backups the session's rundir and clean promises.
        """
        t.sh.cd(t.env.MTOOL_STEP_SPOOL)
        vortex.toolbox.rescue(bkupdir=t.env.MTOOL_STEP_ABORT)
