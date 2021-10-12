# -*- coding: utf-8 -*-

"""
This modules defines helpers to build job's scripts.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import six

import ast
import collections
import functools
import importlib
import re
import string
import sys
import tempfile
import traceback

from bronx.fancies import loggers
from bronx.stdtypes import date
from bronx.syntax.decorators import nicedeco
import footprints
from footprints import proxy as fpx
from footprints.stdtypes import FPSet

import vortex
from vortex.layout import subjobs
from vortex.layout.appconf import ConfigSet
from vortex.tools.actions import actiond as ad
from vortex.tools.actions import FlowSchedulerGateway
from vortex.tools.systems import istruedef
from vortex.util.config import GenericConfigParser, ExtendedReadOnlyConfigParser, load_template

#: Export nothing
__all__ = []

logger = loggers.getLogger(__name__)


_RE_VORTEXDATE = re.compile(r'_(?P<date>\d{8})T(?P<hh>\d{2})(?P<mm>\d{2})(?P<cutoff>[AP])',
                            re.IGNORECASE)
_RE_OPTIME = re.compile(r'_t?(?P<hh>\d{2})(?:[:h-]?(?P<mm>\d{2})?)', re.IGNORECASE)
_RE_MEMBER = re.compile(r'_mb(?P<member>\d+)', re.IGNORECASE)


_JobBasicConf = collections.namedtuple('_JobBasicConf', ['appbase', 'xpid', 'vapp', 'vconf'])


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
    if re.match('jobs_[^' + t.sh.path.sep + ']+', lpath[-1]):
        lpath.pop()
    return _JobBasicConf('/'.join(lpath), *lpath[-3:])


def _mkjob_opts_detect_1(t, ** opts):
    """Detect options that does not depend on the configuration file."""
    tr_opts = dict()
    auto_opts = dict()

    # Things guessed from the directory name
    opset = _guess_vapp_vconf_xpid(t)
    appbase = opts.pop('appbase', opset.appbase)
    target_appbase = opts.get('target_appbase', opset.appbase)
    xpid = opts.get('xpid', opset.xpid)
    vapp = opts.pop('vapp', opset.vapp)
    vconf = opts.pop('vconf', opset.vconf)

    taskconf = opts.pop('taskconf', None)
    if taskconf:
        jobconf = '{0:s}/conf/{1:s}_{2:s}_{3:s}.ini'.format(appbase, vapp, vconf, taskconf)
        taskconf = '_' + taskconf
    else:
        jobconf = '{0:s}/conf/{1:s}_{2:s}.ini'.format(appbase, vapp, vconf)
        taskconf = ''

    # Other pre-calculated stuff
    tr_opts['appbase'] = appbase
    tr_opts['target_appbase'] = target_appbase
    tr_opts['xpid'] = xpid
    tr_opts['vapp'] = vapp
    tr_opts['vconf'] = vconf
    tr_opts['jobconf'] = jobconf
    tr_opts['taskconf'] = taskconf

    return tr_opts, auto_opts, opts


def _mkjob_opts_detect_2(t, tplconf, jobconf, tr_opts, auto_opts, ** opts):
    """Detect options that depend on the configuration file."""

    # The mkjob profile and associated conf
    profile = opts.pop('profile', 'void')
    p_tplconf = tplconf.get(profile, None)
    if p_tplconf is None:
        emsg = "Job's profile << {:s} >> not found.".format(profile)
        logger.critical(emsg)
        raise ValueError(emsg)

    # Fix the task's name
    name = re.sub(r'\.py$', '', opts.pop('name', 'autojob'))

    # Try to find default rundate/runtime according to the jobname
    runtime = opts.pop('runtime', None)
    rundate = opts.pop('rundate', None)
    cutoff = opts.pop('cutoff', None)
    if runtime is None and rundate is None:
        vtxdate = _RE_VORTEXDATE.search(name)
        if vtxdate:
            rundate = date.Date(vtxdate.group('date') +
                                vtxdate.group('hh') + vtxdate.group('mm'))
            runtime = date.Time('{:s}:{:s}'.format(vtxdate.group('hh'),
                                                   vtxdate.group('mm')))
            if cutoff is None:
                cutoff = dict(A='assim', P='production').get(vtxdate.group('cutoff'))
            name = _RE_VORTEXDATE.sub('', name)
        else:
            optime = _RE_OPTIME.search(name)
            if optime:
                runtime = date.Time('{:s}:{:s}'.format(optime.group('hh'), optime.group('mm')))
                name = _RE_OPTIME.sub('', name)

    # Try to find default member number according to the jobname
    member = opts.pop('member', None)
    if member is None:
        mblookup = _RE_MEMBER.search(name)
        if mblookup:
            member = int(mblookup.group('member'))
            name = _RE_MEMBER.sub('', name)

    # Get the job's configuration
    p_jobconf = jobconf.get(name, None)
    if p_jobconf is None:
        logger.error('No job configuration for job name=%s', name)
        logger.warning('Going on with an emtpy job configuration... probably a bad idea !')
        p_jobconf = dict()

    def opts_plus_job(what, default):
        """Function that look up in command line options, then in job's conf."""
        return opts.pop(what, p_jobconf.get(what, default))

    def opts_plus_job_plus_tpl(what, default):
        """
        Function that look up in command line options, then in job's conf,
        then in template's conf.
        """
        return opts.pop(what, p_jobconf.get(what, p_tplconf.get(what, default)))

    # A last chance for these super-stars : they may be set in job's conf...
    if rundate is None:
        rundate = p_jobconf.get('rundate', None)
    if runtime is None:
        runtime = p_jobconf.get('runtime', None)
    if cutoff is None:
        cutoff = p_jobconf.get('cutoff', None)
    if member is None:
        member = p_jobconf.get('member', None)

    if member is not None:
        try:
            member = int(member)
        except ValueError:
            pass

    # Special treatment for xpid and target_appbase (they may be in jobconf but
    # command line value remain the preferred value)
    for stuff in ('xpid', 'target_appbase'):
        if stuff not in opts:
            if stuff in p_jobconf:
                tr_opts[stuff] = p_jobconf[stuff]
        else:
            del opts[stuff]

    # Switch verbosity from boolean to plain string
    verb = opts_plus_job_plus_tpl('verbose', True)
    if isinstance(verb, bool):
        verb = 'verbose' if verb else 'noverbose'

    # Adapt the partition name if refill is on
    refill = opts_plus_job_plus_tpl('refill', False)
    if not isinstance(refill, bool):
        refill = bool(istruedef.match(refill))
    warmstart = opts_plus_job_plus_tpl('warmstart', False)
    if not isinstance(warmstart, bool):
        warmstart = bool(istruedef.match(warmstart))
    partition = opts_plus_job_plus_tpl('partition', None)
    if refill or warmstart:
        partition = opts_plus_job_plus_tpl('refill_partition', None)

    # SuiteBg
    suitebg = opts_plus_job_plus_tpl('suitebg', None)

    # Rundates
    rundates = opts_plus_job_plus_tpl('rundates', None)

    # Lists...
    for explist in ('loadedmods', 'loadedaddons', 'loadedjaplugins',
                    'ldlibs', 'extrapythonpath'):
        val = opts_plus_job_plus_tpl(explist, None)
        if val:
            tr_opts[explist] = ','.join(["'{:s}'".format(x)
                                         for x in re.split(r'\s*,\s*', val)
                                         if len(x)])
            if tr_opts[explist]:
                tr_opts[explist] += ','  # Always ends with a ,

    # A lot of basic stuffs...
    tr_opts['create'] = opts.pop('create', date.at_second().iso8601())
    tr_opts['mkuser'] = opts.pop('mkuser', t.glove.user)
    tr_opts['mkhost'] = opts.pop('mkhost', t.sh.hostname)
    tr_opts['mkopts'] = opts.pop('mkopts')
    tr_opts['pwd'] = opts.pop('pwd', t.sh.getcwd())
    tr_opts['home'] = opts_plus_job('home', t.env.HOME)

    tr_opts['python'] = opts_plus_job_plus_tpl('python', t.sh.which('python'))
    tr_opts['pyopts'] = opts_plus_job_plus_tpl('pyopts', '-u')

    tr_opts['task'] = opts_plus_job_plus_tpl('task', 'void')

    # Other pre-calculated stuff
    tr_opts['verbose'] = verb
    tr_opts['name'] = name
    tr_opts['file'] = opts.pop('file', name + '.py')
    if rundate is None:
        tr_opts['rundate'] = None
    else:
        try:
            rundate = date.Date(rundate).ymdh
        except (ValueError, TypeError):
            pass
        tr_opts['rundate'] = "'" + six.text_type(rundate) + "'"  # Ugly, but that's history
    if runtime is None:
        tr_opts['runtime'] = None
    else:
        try:
            runtime = date.Time(runtime)
        except (ValueError, TypeError):
            pass
        tr_opts['runtime'] = "'" + six.text_type(runtime) + "'"  # Ugly, but that's history
    if cutoff is not None:
        tr_opts['cutoff'] = cutoff
    tr_opts['member'] = member
    auto_opts['member'] = member
    if suitebg is None:
        tr_opts['suitebg'] = suitebg
    else:
        tr_opts['suitebg'] = "'" + suitebg + "'"  # Ugly, but that's history
    auto_opts['suitebg'] = suitebg
    tr_opts['refill'] = refill
    tr_opts['warmstart'] = warmstart
    if partition is not None:
        tr_opts['partition'] = partition
    if rundates:
        tr_opts['rundates'] = rundates
        auto_opts['rundates'] = rundates
    else:
        tr_opts['rundates'] = ''

    # The list of auto command-line options to ignore
    auto_options_filter_opts = opts.pop('auto_options_filter', ())
    auto_options_filter = (opts_plus_job_plus_tpl('auto_options_filter', '').split(',') +
                           list(auto_options_filter_opts))
    # All the remaining stuff...
    for k, v in opts.items():
        tr_opts.setdefault(k, v)
        if k not in auto_options_filter:
            auto_opts.setdefault(k, v)
    for k, v in p_jobconf.items():
        tr_opts.setdefault(k, v)
    for k, v in p_tplconf.items():
        tr_opts.setdefault(k, v)

    return tr_opts, auto_opts


def _mkjob_type_translate(k, v):
    """Dump values as strings for auto_options export..."""
    if 'dates' in k:
        return "bronx.stdtypes.date.daterangex('{:s}')".format(v)
    elif 'date' in k:
        return "bronx.stdtypes.date.Date('{:s}')".format(v)
    else:
        if isinstance(v, six.string_types):
            return "'{:s}'".format(v)
        else:
            return six.text_type(v)


def _mkjob_opts_autoexport(auto_opts):
    return ',\n'.join(['    ' + k + '=' + _mkjob_type_translate(k, v)
                       for k, v in sorted(auto_opts.items())])


def mkjob(t, **kw):
    """Build a complete job file according to a template and some parameters."""
    opts = dict(
        inifile='@job-default.ini',
        wrap=False,
    )
    opts.update(kw)

    # Detect some basic options that do not depend on the configuration files
    tr_opts, auto_opts, r_kw = _mkjob_opts_detect_1(t, mkopts=six.text_type(kw), **kw)

    # Read the configuration files
    try:
        iniparser = ExtendedReadOnlyConfigParser(inifile=opts['inifile'])
        tplconf = iniparser.as_dict()
    except Exception as pb:
        emsg = 'Could not read the << {:s} >> config file: {!s}'.format(opts['inifile'], pb)
        logger.critical(emsg)
        raise ValueError(emsg)

    if t.sh.path.exists(tr_opts['jobconf']):
        t.sh.header('Reading ' + tr_opts['jobconf'])
        try:
            jobparser = ExtendedReadOnlyConfigParser(inifile=tr_opts['jobconf'])
            jobconf = jobparser.as_dict()
        except Exception as pb:
            emsg = 'Could not read the << {:s} >> config file: {!s}'.format(tr_opts['jobconf'], pb)
            logger.critical(emsg)
            raise ValueError(emsg)
    else:
        emsg = 'Could not find the << {:s} >> config file.'.format(tr_opts['jobconf'])
        logger.error(emsg)
        raise ValueError(emsg)

    # Detect most of the options that depend on the configuration file
    tr_opts, auto_opts = _mkjob_opts_detect_2(t, tplconf, jobconf,
                                              tr_opts, auto_opts, ** r_kw)

    # Dump auto_exported options
    tr_opts['auto_options'] = _mkjob_opts_autoexport(auto_opts)

    # Generate the job
    corejob = load_template(t, tr_opts['template'], encoding="script")
    tr_opts['tplfile'] = corejob.srcfile
    pycode = string.Template(corejob.substitute(tr_opts)).substitute(tr_opts)

    if opts['wrap']:
        def autojob():
            eval(compile(pycode, 'compile.mkjob.log', 'exec'))
        objcode = autojob
    else:
        # Using ast ensures that a valid python script was generated
        ast.parse(pycode, 'compile.mkjob.log', 'exec')
        objcode = pycode

    return objcode, tr_opts


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
                info = 'A set of Python modules/packages to be imported.',
                type = FPSet,
                optional = True,
                default = FPSet(()),
            ),
            addons = dict(
                info = 'A set of Vortex shell addons to load in the main System object',
                type = FPSet,
                optional = True,
                default = FPSet(()),
            ),
            ldlibs = dict(
                info = 'A set of paths to prepend to the LD_LIBRARY_PATH variable.',
                type = FPSet,
                optional = True,
                default = FPSet(()),
            ),
            special_prefix = dict(
                info = 'The prefix of environment variable with a special meaning.',
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
        self.subjob_allowed = True
        self.subjob_tag = None
        self.subjob_fsid = None
        # By default, no error code is thrown away
        self.unix_exit_code = 0
        self._plugins = list()
        self._conf = None
        self._special_variables = None

    @property
    def plugins(self):
        return self._plugins

    def add_plugin(self, kind, **kwargs):
        self._plugins.append(fpx.jobassistant_plugin(kind=kind, masterja=self,
                                                     **kwargs))

    @property
    def conf(self):
        if self._conf is None:
            raise RuntimeError('It is too soon to access the JobAssisant configuration')
        return self._conf

    @property
    def special_variables(self):
        if self._special_variables is None:
            raise RuntimeError('It is too soon to access the JobAssisant special variables')
        return self._special_variables

    def __getattr__(self, name):
        """Search the plugins for unknown methods."""
        if not (name.startswith('_') or name.startswith('plugable')):
            for plugin in self.plugins:
                if hasattr(plugin, name):
                    return getattr(plugin, name)
        raise AttributeError('Attribute not found.')

    @_extendable
    def _init_special_variables(self, prefix=None, **kw):
        """Print some of the environment variables."""
        prefix = prefix or self.special_prefix
        # Suffixed variables
        specials = kw.get('actual', dict())
        self._special_variables = {k[len(prefix):].lower(): v
                                   for k, v in specials.items() if k.startswith(prefix)}
        # Auto variables
        auto = kw.get('auto_options', dict())
        for k, v in auto.items():
            self._special_variables.setdefault(k.lower(), v)

    def _kw_and_specials_get(self, what, default, **kw):
        """Look for name in **kw** and **self.special_variables**."""
        return kw.get(what, self.special_variables.get(what, default))

    def _init_conf(self, **kw):
        """Read the application's configuration file."""
        jobname = self._kw_and_specials_get('jobname', None)
        iniconf = self._kw_and_specials_get('iniconf', None)
        iniencoding = self._kw_and_specials_get('inienconding', None)
        self._conf = ConfigSet()
        if iniconf:
            try:
                iniparser = GenericConfigParser(iniconf, encoding=iniencoding)
            except Exception:
                logger.critical('Could not read config %s', iniconf)
                raise
            thisconf = iniparser.as_dict(merged=False)
            # Conf defaults
            self._conf.update(thisconf.get('defaults', dict()))
            if jobname is not None:
                # Job specific conf
                self._conf.update(thisconf.get(jobname, dict()))
        # Stuff from the script and command-line
        self._conf.update(self.special_variables)

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

        t.sh.header('Session & Target description')

        locprint('Session Ticket', t)
        locprint('Session Glove', t.glove)
        locprint('Session System', t.sh)
        locprint('Session Env', t.env)
        tg = t.sh.default_target
        locprint('Target name', tg.hostname)
        locprint('Target system', tg.sysname)
        locprint('Target inifile', tg.inifile)

    @_extendable
    def _print_toolbox_settings(self, t):
        """Display the toolbox settings."""
        vortex.toolbox.show_toolbox_settings()

    @classmethod
    def print_somevariables(cls, t, prefix=''):
        """Print some of the environment variables."""
        prefix = prefix.upper()
        filtered = sorted([x for x in t.env.keys() if x.startswith(prefix)])
        if filtered:
            t.sh.highlight('{:s} environment variables'.format(prefix if prefix else 'All'))
            maxlen = max([len(x) for x in filtered])
            for var_name in filtered:
                cls._printfmt(cls._P_ENVVAR_FMT,
                              var_name.ljust(maxlen), t.env.native(var_name))
        return len(filtered)

    @_extendable
    def _add_specials(self, t, prefix=None, **kw):
        """Print some of the environment variables."""
        prefix = prefix or self.special_prefix
        if self.special_variables:
            filtered = {prefix + k: v for k, v in self.special_variables.items()}
            self._printfmt('Copying actual {:s} variables to the environment', prefix)
            t.env.update(filtered)
            self.print_somevariables(t, prefix=prefix)

    @_extendable
    def _modules_preload(self, t):
        """Import all the modules listed in the footprint."""
        t.sh.header('External imports')
        for module in sorted(self.modules):
            importlib.import_module(module)
            self._printfmt(self._P_MODULES_FMT, module)

    @_extendable
    def _addons_preload(self, t):
        """Load shell addons."""
        t.sh.header('Add-ons to the shell')
        for addon in self.addons:
            shadd = footprints.proxy.addon(kind=addon, shell=t.sh)
            self._printfmt(self._P_ADDON_FMT, addon.upper(), shadd)

    @_extendable
    def _system_setup(self, t, **kw):
        """Set usual settings for the system shell."""
        t.sh.header("Session and system basic setup")
        self._printfmt('+ Setting "stack" and "memlock" limits to unlimited.')
        t.sh.setulimit('stack')
        t.sh.setulimit('memlock')
        for ldlib in self.ldlibs:
            self._printfmt('+ Prepending "{}" to the LD_LIBRARY_PATH.', ldlib)
            t.env.setgenericpath('LD_LIBRARY_PATH', ldlib, pos=0)

    @_extendable
    def _early_session_setup(self, t, **kw):
        """Create a now session, set important things, ..."""
        t.sh.header("Session's early setup")
        t.glove.vapp = self._kw_and_specials_get('vapp', None)
        t.glove.vconf = self._kw_and_specials_get('vconf', None)
        # Ensure that the script's path is an absolute path
        sys.argv[0] = t.sh.path.abspath(sys.argv[0])
        return t

    @_extendable
    def _extra_session_setup(self, t, **kw):
        """Additional setup for the session."""
        t.sh.header("Session's final setup")
        # Handle session's datastore for subjobs
        if self.subjob_tag is not None:
            t.datastore.pickle_load(subjobs._DSTORE_IN.format(self.subjob_fsid))
            self._printfmt('+ The datastore was read from disk: ' + subjobs._DSTORE_IN,
                           self.subjob_fsid)
        # Possibly setup the default user names for file-transfers
        ftuser = self.conf.get('ftuser', None)
        if ftuser is not None:
            if isinstance(ftuser, dict):
                for dest, d_ftuser in ftuser.items():
                    if not (isinstance(dest, six.string_types) and isinstance(d_ftuser, six.string_types)):
                        logger.error('Improper ftuser configuration (Destination=%s, Logname=%s)',
                                     dest, d_ftuser)
                        continue
                    if dest.lower() == 'default':
                        self._printfmt('+ Setting the default file-transfer user to: {:s}', d_ftuser)
                        t.glove.setftuser(d_ftuser)
                    else:
                        self._printfmt('+ Setting the {:s} file-transfer user to: {:s}', dest, d_ftuser)
                        t.glove.setftuser(d_ftuser, dest)
            elif isinstance(ftuser, six.string_types):
                self._printfmt('+ Setting the default file-transfer user to: {:s}', ftuser)
                t.glove.setftuser(ftuser)
            else:
                logger.error('Improper ftuser value %s', ftuser)
        # Possibly setup the default hostname for file-transfers
        fthost = self.conf.get('fthost', None)
        if fthost is not None:
            t.glove.default_fthost = fthost
            self._printfmt('+ Setting the default file-transfer hostname to: {:s}', fthost)

    @_extendable
    def _env_setup(self, t, **kw):
        """Session's environment setup."""
        t.sh.header("Environment variables setup")
        t.env.verbose(True, t.sh)
        self._add_specials(t, **kw)

    @_extendable
    def _toolbox_setup(self, t, **kw):
        """Toolbox default setup."""
        t.sh.header('Toolbox module settings')
        vortex.toolbox.active_verbose = True
        vortex.toolbox.active_now = True
        vortex.toolbox.active_clear = True

    @_extendable
    def _actions_setup(self, t, **kw):
        """Setup the action dispatcher."""
        t.sh.header('Actions setup')

    @_extendable
    def _job_final_init(self, t, **kw):
        """Final initialisations for a job."""
        t.sh.header("Job's final init")

    def _subjob_detect(self, t):
        if 'VORTEX_SUBJOB_ACTIVATED' in t.env:
            tag, fsid = t.env['VORTEX_SUBJOB_ACTIVATED'].split(':', 1)
            self.subjob_tag = tag
            self.subjob_fsid = fsid

    def setup(self, **kw):
        """This is the main method. it setups everything in the session."""
        # We need the root session
        t = vortex.ticket()
        t.system().prompt = t.prompt
        t.sh.subtitle("Starting JobAssistant's setup")
        # Am I a subjob ?
        self._subjob_detect(t)
        # JA object setup
        self._init_special_variables(**kw)
        self._init_conf(**kw)
        # A new session can be created here
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
        # A last word ?
        self._job_final_init(t, **kw)
        self._printfmt('')
        return t, t.env, t.sh

    @_extendable
    def add_extra_traces(self, t):
        """Switch the system shell to verbose mode."""
        t.sh.trace = True

    @_extendable
    def register_cycle(self, cycle):
        """A callback to register GCO cycles."""
        from gco.syntax.stdattrs import GgetId
        try:
            cycle = GgetId(cycle)
        except ValueError:
            self._printfmt('** Cycle << {!s} >> will auto-register whenever necessary **', cycle)
            return
        from gco.tools import genv
        if cycle in genv.cycles():
            self._printfmt('** Cycle << {!s} >> already registered **', cycle)
        else:
            self._printfmt('\n** Cycle << {!s} >> is to be registered **', cycle)
            genv.autofill(cycle)
            print(genv.as_rawstr(cycle=cycle))

    @_extendable
    def complete(self):
        """Should be called when a job finishes successfully"""
        t = vortex.ticket()
        t.sh.subtitle("Executing JobAssistant's complete actions")

    @_extendable
    def fulltraceback(self, latest_error=None):
        """Produce some nice traceback at the point of failure.

        :param Exception latest_error: The latest caught exception.
        """
        t = vortex.ticket()
        t.sh.subtitle('Handling exception')
        (exc_type, exc_value, exc_traceback) = sys.exc_info()  # @UnusedVariable
        self._printfmt('Exception type: {!s}', exc_type)
        self._printfmt('Exception info: {!s}', latest_error)
        t.sh.header('Traceback Error / BEGIN')
        print("\n".join(traceback.format_tb(exc_traceback)))
        t.sh.header('Traceback Error / END')

    @_extendable
    def rescue(self):
        """Called at the end of a job when something went wrong."""
        t = vortex.ticket()
        t.sh.subtitle("Executing JobAssistant's rescue actions")
        self.unix_exit_code = 1

    @_extendable
    def finalise(self):
        """Called whenever a job finishes (either successfully or badly)."""
        t = vortex.ticket()
        t.sh.subtitle("Executing JobAssistant's finalise actions")
        if self.subjob_tag is not None:
            t.datastore.pickle_dump(subjobs._DSTORE_OUT.format(self.subjob_fsid, self.subjob_tag))
            self._printfmt('+ The datastore was written to disk: ' + subjobs._DSTORE_OUT,
                           self.subjob_fsid, self.subjob_tag)

    def close(self):
        """This must be the last called method whenever a job finishes."""
        t = vortex.ticket()
        t.sh.subtitle("Executing JobAssistant's close")
        t.sh.signal_intercept_off()
        t.exit()
        if self.unix_exit_code:
            self._printfmt('Something went wrong :-(')
            exit(self.unix_exit_code)
        if self.subjob_tag:
            self._printfmt('Subjob fast exit :-)')
            exit(0)


class JobAssistantPlugin(footprints.FootprintBase):

    _conflicts = []
    _abstract = True
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
            if conflicting in [p.kind for p in self.masterja.plugins]:
                raise RuntimeError('"{:s}" conflicts with "{:s}"'.format(self.kind, conflicting))

    @staticmethod
    def _printfmt(fmt, *kargs, **kwargs):
        JobAssistant._printfmt(fmt, *kargs, **kwargs)


class JobAssistantTmpdirPlugin(JobAssistantPlugin):

    _conflicts = ['mtool', 'autodir']
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
            self._printfmt('+ Current rundir < {:s} >', t.rundir)


class JobAssistantAutodirPlugin(JobAssistantPlugin):

    _conflicts = ['mtool', 'tmpdir']
    _footprint = dict(
        info = 'JobAssistant Automatic Directory Plugin',
        attr = dict(
            kind = dict(
                values = ['autodir', ]
            ),
            appbase = dict(
                info="The directory where the application lies.",
            ),
            jobname = dict(
                info="The current job name.",
            ),
            cleanup = dict(
                info = "Remove the workind directory when the job is done.",
                type = bool,
                optional = True,
                default = True,
            ),
        ),
    )

    def __init__(self, *kargs, **kwargs):
        super(JobAssistantAutodirPlugin, self).__init__(*kargs, **kwargs)
        self._joblabel = None

    def _autodir_tmpdir(self, t):
        tmpbase = t.sh.path.join(self.appbase, 'run', 'tmp')
        if self._joblabel is None:
            with t.sh.cdcontext(tmpbase, create=True):
                self._joblabel = t.sh.path.basename(tempfile.mkdtemp(
                    prefix='{:s}_{:s}_'.format(self.jobname, date.now().iso8601()),
                    dir='.'
                ))
        return t.sh.path.join(tmpbase, self._joblabel)

    def _autodir_abort(self, t):
        abortbase = t.sh.path.join(self.appbase, 'run', 'abort')
        if self._joblabel is None:
            self._autodir_tmpdir(t)
        abortdir = t.sh.path.join(abortbase, self._joblabel)
        t.sh.mkdir(abortdir)
        return abortdir

    def plugable_extra_session_setup(self, t, **kw):
        """Set the rundir according to the TMPDIR variable."""
        t.rundir = self._autodir_tmpdir(t)
        self._printfmt('+ Current rundir < {:s} >', t.rundir)

    def plugable_finalise(self, t):
        """Should be called when a job finishes successfully"""
        if self.cleanup:
            self._printfmt('+ Removing the rundir < {:s} >', t.rundir)
            t.sh.cd(t.env.HOME)
            t.sh.rm(self._autodir_tmpdir(t))

    def plugable_rescue(self, t):
        """Called at the end of a job when something went wrong."""
        t.sh.cd(self._autodir_tmpdir(t))
        if self.masterja.subjob_tag is None:
            vortex.toolbox.rescue(bkupdir=self._autodir_abort(t))


class JobAssistantMtoolPlugin(JobAssistantPlugin):

    _conflicts = ['tmpdir', 'autodir']

    _footprint = dict(
        info = 'JobAssistant MTOOL Plugin',
        attr = dict(
            kind = dict(
                values = ['mtool', ]
            ),
            step = dict(
                info="The number of the current MTOOL step.",
                type=int,
            ),
            stepid=dict(
                info="The name (id) of the current MTOOL step.",
            ),
            lastid = dict(
                info="The name (id) of the last effective MTOOL step.",
                optional=True,
            ),
            mtoolid = dict(
                info="The MTOOL's job number",
                type=int,
                optional=True,
            )
        ),
    )

    @property
    def mtool_steps(self):
        """The list of Task' steps asociated a given MTOOL step."""
        steps_map = {'transfer': ('early-fetch', 'fetch', 'backup', 'late-backup'),
                     'fetch': ('early-fetch', ),
                     'compute': ('early-fetch', 'fetch', 'compute', 'backup'),
                     'backup': ('backup', 'late-backup'), }
        try:
            return steps_map[self.stepid]
        except KeyError:
            logger.error("Unknown MTOOL step: %s", self.stepid)
            return ()

    @property
    def is_last(self):
        """Is it the laste MTOOL step (appart from the cleaning)."""
        return self.stepid == self.lastid

    def plugable_extra_session_setup(self, t, **kw):
        """Set the rundir according to MTTOL's spool."""
        t.rundir = t.env.MTOOL_STEP_SPOOL
        t.sh.cd(t.rundir)
        self._printfmt('+ Current rundir < {:s} >', t.rundir)
        # Load the session's data store
        if self.step > 1 and self.masterja.subjob_tag is None:
            t.datastore.pickle_load()
            self._printfmt('+ The datastore was read from disk.')
        # Check that the log directory exists
        if "MTOOL_STEP_LOGFILE" in t.env:
            logfile = t.sh.path.normpath(t.env.MTOOL_STEP_LOGFILE)
            logdir = t.sh.path.dirname(logfile)
            if not t.sh.path.isdir(logdir):
                t.sh.mkdir(logdir)
            self._printfmt('+ Current logfile < {:s} >', logfile)
        # Only allow subjobs in compute steps
        self.masterja.subjob_allowed = self.stepid == 'compute'

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
        if self.masterja.subjob_tag is None:
            t.datastore.pickle_dump()
            self._printfmt('+ The datastore is dumped to disk')

    def plugable_rescue(self, t):
        """Called at the end of a job when something went wrong.

        It backups the session's rundir and clean promises.
        """
        t.sh.cd(t.env.MTOOL_STEP_SPOOL)
        if self.masterja.subjob_tag is None:
            vortex.toolbox.rescue(bkupdir=t.env.MTOOL_STEP_ABORT)


class JobAssistantFlowSchedPlugin(JobAssistantPlugin):

    _footprint = dict(
        info = 'JobAssistant Flow Scheduler Plugin',
        attr = dict(
            kind = dict(
                values = ['flow', ]
            ),
            backend = dict(
                values = ['ecflow', 'sms']
            ),
            jobidlabels = dict(
                info="Update the task's jobid label.",
                default=False,
                optional=True,
                type=bool,
            ),
            mtoolmeters  = dict(
                info="Update the MTOOL's work meter.",
                default=False,
                optional=True,
                type=bool,
            )
        ),
    )

    def __init__(self, *kargs, **kwargs):
        super(JobAssistantFlowSchedPlugin, self).__init__(*kargs, **kwargs)
        self._flow_sched_saved_mtplug = 0

    @property
    def _flow_sched_mtool_plugin(self):
        """Return the MTOOL plugin (if present)."""
        if self._flow_sched_saved_mtplug == 0:
            self._flow_sched_saved_mtplug = None
            for p in self.masterja.plugins:
                if p.kind == 'mtool':
                    self._flow_sched_saved_mtplug = p
        return self._flow_sched_saved_mtplug

    def _flow_sched_ids(self, t):
        """Return the jobid and RID."""
        # Simple heuristic to find a job id
        jid = t.env.PBS_JOBID or t.env.SLURM_JOB_ID or 'localpid'
        if jid == 'localpid':
            jid = t.sh.getpid()
        # Find a suitable RID
        mtplug = self._flow_sched_mtool_plugin
        if mtplug is None:
            rid = jid
        else:
            if mtplug.mtoolid is None:
                raise RuntimeError("mtplug.mtoolid must be defined")
            rid = mtplug.mtoolid
        return jid, rid

    def plugable_actions_setup(self, t, **kw):
        """Setup the flow action dispatcher."""
        if self.masterja.subjob_tag is None:
            ad.add(FlowSchedulerGateway(service=self.backend))

            # Configure the action
            jid, rid = self._flow_sched_ids(t)
            label = "{:s}".format(jid)
            confdict = kw.get('flowscheduler', dict())
            confdict.setdefault('ECF_RID', rid)
            ad.flow_conf(confdict)

            t.sh.highlight('Flow Scheduler ({:s}) Settings'.format(self.backend))
            ad.flow_info()
            self._printfmt('')
            self._printfmt('Flow scheduler client path: {:s}', ad.flow_path())

            # Initialise the flow scheduler
            mtplug = self._flow_sched_mtool_plugin
            if mtplug is None:
                ad.flow_init(rid)
            else:
                if mtplug.step == 1:
                    ad.flow_init(rid)
                label = "{:s} (mtoolid={!s})".format(label, mtplug.mtoolid)
                if self.mtoolmeters:
                    ad.flow_meter('work', 1 + (mtplug.step - 1) * 2)
            if self.jobidlabels:
                ad.flow_label('jobid', label)

    def plugable_complete(self, t):
        """Should be called when a job finishes successfully."""
        if self.masterja.subjob_tag is None:
            mtplug = self._flow_sched_mtool_plugin
            if mtplug is None:
                ad.flow_complete()
            else:
                if self.mtoolmeters:
                    ad.flow_meter('work', 2 + (mtplug.step - 1) * 2)
                # With MTOOL, complete only at the end of the last step...
                if mtplug.stepid == mtplug.lastid:
                    ad.flow_complete()

    def plugable_rescue(self, t):
        """Called at the end of a job when something went wrong."""
        if self.masterja.subjob_tag is None:
            ad.flow_abort("An exception was caught")


class JobAssistantEpygramPlugin(JobAssistantPlugin):

    _footprint = dict(
        info = 'JobAssistant Plugin to perform the epygram setup',
        attr = dict(
            kind = dict(
                values      = ['epygram_setup', ]
            ),
        ),
    )

    def plugable_env_setup(self, t, **kw):  # @UnusedVariable
        # Is epygram here ?
        epygram_re = re.compile(r'.*epygram$')
        epygram_path = [bool(epygram_re.match(p)) for p in sys.path]
        if any(epygram_path):
            # Add eccodes and site subdirectories if necessary
            i_epygram = epygram_path.index(True)
            logger.info('Epygram package found in path: %s', sys.path[i_epygram])
            for spath in ('eccodes_python', 'site'):
                full_spath = t.sh.path.join(sys.path[i_epygram], spath)
                if full_spath not in sys.path:
                    logger.info('Extending python path with: %s', full_spath)
                    sys.path.insert(i_epygram + 1, full_spath)
            # Python3, ECCODES_DIR is needed
            if sys.version_info.major == 3:
                edir_path = t.sh.path.join(sys.path[i_epygram], 'eccodes_dir')
                if t.sh.path.exists(edir_path):
                    logger.info('ECCODES_DIR environment variable setup to %s', edir_path)
                    t.env.ECCODES_DIR = edir_path
                else:
                    logger.info('ECCODES_DIR environment variable left unconfigured')
            # In any case, run with the Agg matplotlib backend
            t.env.MPLBACKEND = 'Agg'


class JobAssistantAppWideLockPlugin(JobAssistantPlugin):
    """Manage an application wide lock.

    If **acquire** is True, the lock will be acquired when the job starts (if
    the lock is already taken, it will fail). If **release** is True, the
    lock will be released at the end of the job. In any case, the lock will
    be released whenever the job crashes.

    The lock mechanism that is used is :meth:`vortex.tools.systems.OSExtended.appwide_lock`.

    Prior to being used, the **label** will be formated by the string's format
    method using any rd|op_* variable in the submitted job. For exemple::

        >>> label = 'my_lock_{xpid:s}'

    This class is not usable one its own. It must be subclassed in the target
    application (in the python module that holds the job's driver):

        * **kind** must be provided with a unique authorised value;
        * **label** must be set optional and given a default value;
        * **acquire** and **release** default values may be changed depending
          on ones needs.
    """

    _abstract = True
    _footprint = dict(
        info='JobAssistant to deal with application wide locks.',
        attr = dict(
            label=dict(
                info="The name of the lock.",
            ),
            acquire=dict(
                info="Acquire the lock during the setup phase.",
                type=bool,
                optional=True,
                default=False,
            ),
            release=dict(
                info="Release the lock at the end.",
                type=bool,
                optional=True,
                default=False,
            ),
            blocking=dict(
                info="Block when acquiring the lock.",
                type=bool,
                optional=True,
                default=False,
            ),
            blocking_timeout=dict(
                info="Block at most N seconds.",
                type=int,
                optional=True,
                default=300,
            ),
        ),
    )

    def __init__(self, *kargs, **kwargs):
        super(JobAssistantAppWideLockPlugin, self).__init__(*kargs, **kwargs)
        self._appwide_lock_saved_mtplug = 0
        self._appwide_lock_label = None
        self._appwide_lock_acquired = None

    @property
    def _appwide_lock_mtool_plugin(self):
        """Return the MTOOL plugin (if present)."""
        if self._appwide_lock_saved_mtplug == 0:
            self._appwide_lock_saved_mtplug = None
            for p in self.masterja.plugins:
                if p.kind == 'mtool':
                    self._appwide_lock_saved_mtplug = p
        return self._appwide_lock_saved_mtplug

    def plugable_job_final_init(self, t, **kw):
        """Acquire the lock on job startup."""
        self._appwide_lock_label = self.label.format(** self.masterja.special_variables)
        if self.acquire:
            mtplug = self._appwide_lock_mtool_plugin
            if (mtplug and mtplug.step == 1) or mtplug is None:
                logger.info("Acquiring the '%s' application wide lock",
                            self._appwide_lock_label)
                self._appwide_lock_acquired = t.sh.appwide_lock(self._appwide_lock_label,
                                                                blocking=self.blocking,
                                                                timeout=self.blocking_timeout)
                if not self._appwide_lock_acquired:
                    logger.error("Acquiring the '%s' application wide lock failed.",
                                 self._appwide_lock_label)
                    raise RuntimeError("Unable to acquire the '{:s}' application wide lock."
                                       .format(self._appwide_lock_label))

    def _appwide_lock_release(self, t):
        """Actualy release the lock."""
        if self._appwide_lock_label:
            logger.info("Releasing the '%s' application wide lock",
                        self._appwide_lock_label)
            t.sh.appwide_unlock(self._appwide_lock_label)

    def plugable_complete(self, t):
        """Should be called when a job finishes successfully."""
        if self.release:
            mtplug = self._appwide_lock_mtool_plugin
            if (mtplug and mtplug.stepid == mtplug.lastid) or mtplug is None:
                self._appwide_lock_release(t)

    def plugable_rescue(self, t):
        """Should be called when a job fails."""
        if self._appwide_lock_acquired is not False:
            self._appwide_lock_release(t)


class JobAssistantRdMailSetupPlugin(JobAssistantPlugin):
    """Activate/Deactivate mail actions for R&D tasks."""

    _footprint = dict(
        info='JobAssistant to deal with application wide locks.',
        attr = dict(
            kind=dict(
                values=['rd_mail_setup', ]
            ),
        )
    )

    def plugable_actions_setup(self, t, **kw):
        """Acquire the lock on job startup."""
        if self.masterja.conf.get('mail_to', None):
            todo = {a for a in ad.actions
                    if a.endswith('mail') and a not in ('mail', 'opmail')}
            for candidate in todo:
                for action in ad.candidates(candidate):
                    logger.info('Activating the << %s >> action.', action.kind)
                    action.on()
