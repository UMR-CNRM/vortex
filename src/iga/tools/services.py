#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module contains the services specifically needed by the operational suite.
  * Alarm sends messages to the syslog system for monitoring.
    Alarms with ``critical`` level are also forwarded to the dayfile system, hence
    the optional ``spooldir`` attribute.
    Depending on the OP_ALARM environment variable, all alarms are sent to a
    log file instead of being really emitted.

    * :class:`AlarmLogService` uses the local SysLog system
    * :class:`AlarmRemoteService` handles remote SysLog usage
    * both are available only on login nodes: a :class:`AlarmProxyService` is
      selected by the footprints elsewhere. This one delegates the service to
      the unix ``logger`` command, executed on a login node.

  * database routing, specifically

    * :class:`BdapService`
    * :class:`BdmService`
    * :class:`BdpeService` (through :class:`BdpeOperationsService` or :class:`BdpeIntegrationService`)

  * formatted dayfile logging with :class:`DayfileReportService`

  * :class:`RemoteCommandProxy` is a helper class able to execute a command
    on a specific node type, e.g. a login or a transfer node.
"""

#: No automatic export
__all__ = []

import logging
from logging.handlers import SysLogHandler

import re
import socket
import random
from StringIO import StringIO

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex import sessions
from vortex.syntax.stdattrs import a_term
from vortex.tools import date
from vortex.tools.services import Service, FileReportService
from vortex.tools.actions import actiond as ad
from vortex.tools.systems import ExecutionError

# TODO devrait dépendre d'un objet TARGET
LOGIN_NODES = [
    x + str(y)
    for x in ('prolixlogin', 'beaufixlogin', )
    for y in range(6)
]

# default Formatter for alarm logfile output
DEFAULT_ALARMLOG_FORMATTER = logging.Formatter(
    fmt     = '[%(asctime)s][%(name)s][%(levelname)s]: %(message)s',
    datefmt = '%Y/%d/%m-%H:%M:%S',
)

# Syslog formatting *must* be compatible with RFC 5424., e.g.
# SYSLOG_FORMATTER = logging.Formatter(
#    fmt     = '%(asctime)s %(name)s: %(levelname)s %(message)s',
#    datefmt = '%b %e %H:%M:%S',
# )
# or this one:
SYSLOG_FORMATTER = logging.Formatter(
    fmt     = '%(asctime)s [%(name)s][%(levelname)s]: %(message)s',
    datefmt = '%Y/%m/%d T %H:%M:%S',
)


class LogFacility(int):
    """
    Attribute for SysLogHandler facility value, could be either a valid ``int``
    or a logging name such as ``log_local7`` or ``local7``.
    """

    def __new__(cls, value):
        if type(value) is str:
            value = value.lower()
            if value.startswith('log_'):
                value = value[4:]
            try:
                value = SysLogHandler.facility_names[value]
            except KeyError:
                logger.error('Could not get a SysLog value for name ' + value)
                raise
        if value not in SysLogHandler.facility_names.values():
            raise ValueError('Not a SysLog facility value: ' + str(value))
        return int.__new__(cls, value)

    def name(self):
        """Reverse access: deduce the name from the integer value."""
        for s, n in SysLogHandler.facility_names.iteritems():
            if self == n:
                return s
        raise ValueError('Not a SysLog facility value: ' + str(self))


def tunable_value(sh, value, env_key=None, ini_key=None, default=None):
    """
    Try to get a value from several sources in turn:
       - a real value (e.g. from the footprint)
       - a shell environment variable
       - the ini files
       - a default value in last resort.
    """
    if value:
        return value
    if env_key and env_key in sh.env:
        return sh.env[env_key]
    if ini_key:
        return sh.target().get(ini_key, default)
    return default


class RemoteCommandProxy(footprints.FootprintBase):
    """Remote execution via ssh on a special node."""
    _collector = ('miscellaneous',)
    _footprint = dict(
        info = 'Remote command proxy',
        attr = dict(
            kind = dict(
                optional = True,
                values   = ['ssh_proxy'],
                alias    = ('remotecommand',),
            ),
            nodekind = dict(
                values = ['login', 'transfer'],
            ),
            loginnode = dict(
                optional = True,
                default  = None,
            ),
            transfernode = dict(
                optional = True,
                default  = None,
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Remote command proxy init %s', self.__class__)
        sh = kw.pop('sh', sessions.system())
        super(RemoteCommandProxy, self).__init__(*args, **kw)
        self._sh = sh

    @property
    def sh(self):
        return self._sh

    def nodename(self):
        """Node name to use for this kind of remote execution."""
        key = self.nodekind + 'node'
        return tunable_value(self.sh,
                             getattr(self, key, None),
                             ini_key='services:' + key,
                             env_key=key.upper(),
                             default='localhost')

    def execute(self, command):
        """Remote execution."""
        try:
            rc = self.sh.spawn(
                ('/usr/bin/ssh', '-x', self.nodename(), command),
                shell=False,
                output=False,
            )
        except ExecutionError:
            rc = False
        return rc


class AlarmService(Service):
    """
    Class responsible for handling alarm data.
    Children:

      * :class:`AlarmProxyService`  (external ``logger`` command for non-login nodes)
      * :class:`AlarmLogService`    (syslog based on ``address``)
      * :class:`AlarmRemoteService` (syslog based on ``syshost``, ``sysport`` and ``socktype``)

    This class should not be called directly.
    """

    _abstract = True
    _footprint = dict(
        info = 'Alarm services abstract class',
        attr = dict(
            kind = dict(
                values   = ['sendalarm']
            ),
            message = dict(
                alias    = ('content',)
            ),
            facility = dict(
                type     = LogFacility,
                optional = True,
                default  = SysLogHandler.LOG_LOCAL3,
            ),
            alarmlogfile = dict(
                optional = True,
                default  = 'alarms.log',
            ),
            alarmlogfmt = dict(
                optional = True,
                type     = logging.Formatter,
                default  = DEFAULT_ALARMLOG_FORMATTER,
            ),
            spooldir = dict(
                optional = True,
                default  = None,
            ),
        )
    )

    def deactivated(self):
        """Tells if alarms are deactivated : OP_ALARM set to 0"""
        return not bool(self.sh.env.get('OP_ALARM', 1))

    def get_syslog(self):
        """Define and return the SyslogHandler to use."""
        pass

    def get_logger_action(self):
        """
        Define a logging handler to broadcast the alarm.
        Return the actual logging method.
        """
        if self.deactivated():
            self.handler = logging.FileHandler(self.alarmlogfile, delay=True)
            self.handler.setFormatter(self.alarmlogfmt)
        else:
            self.handler = self.get_syslog()
            self.handler.setFormatter(SYSLOG_FORMATTER)
        logger.addHandler(self.handler)
        return getattr(logger, self.level, logger.warning)

    def get_message(self):
        """Return the actual message to log."""
        return self.message

    def after_broadcast(self, rc):
        """What to do after the logger was called (and returned rc)."""
        return rc

    def __call__(self):
        """Main action: pack the message to the actual logger action."""
        logmethod = self.get_logger_action()
        message = self.get_message()
        if self.level == 'critical':
            ad.report(kind='dayfile', message='!!! {} !!!'.format(message),
                      mode='TEXTE', spooldir=self.spooldir)
        rc = logmethod(message)
        rc = self.after_broadcast(rc)
        logger.removeHandler(self.handler)
        return rc


class AlarmProxyService(AlarmService):
    """
    Class responsible for handling alarm data through the remote
    unix ``logger`` command invocation (mandatory on non-login nodes)
    This class should not be called directly.
    """

    _footprint = dict(
        info = 'Alarm Proxy Service',
        attr = dict(
            hostname = dict(
                outcast = LOGIN_NODES,
            ),
        )
    )

    def memory_handler(self):
        """Create an in-memory handler."""
        self.buffer = StringIO()
        self.handler = logging.StreamHandler(self.buffer)
        return self.handler

    def memory_message(self):
        """Retrieve the formatted message from an in-memory handler."""
        self.handler.flush()
        self.buffer.flush()
        message = self.buffer.getvalue().rstrip('\n')
        self.buffer.truncate(0)
        return message

    def get_syslog(self):
        """Return an in-memory handler."""
        self.handler = self.memory_handler()
        return self.handler

    @staticmethod
    def priority(level):
        """
        Map a logging level to a SysLogHandler priority
        for the unix ``logger`` command.
        """
        if level == 'critical':
            return 'crit'
        return level

    def after_broadcast(self, rc):
        """
        Calling the logger has filled the in-memory buffer with the formatted
        record. Get this string and transmit it to the remote unix command.
        """
        if self.deactivated():
            return

        # get the formatted message from the logger
        message = self.memory_message()

        # send it to the unix 'logger' command on a login node
        command = "logger -p {}.{} '{}'".format(
            self.facility.name(),
            self.priority(self.level),
            message)
        rcp = RemoteCommandProxy(nodekind='login')
        rc = rcp.execute(command)
        if not rc:
            logger.warning("Remote execution failed: " + command)
        return rc


class AlarmLogService(AlarmService):
    """
    Class responsible for handling alarm data through domain socket.
    This class should not be called directly.
    """

    _footprint = dict(
        info = 'Alarm Log Service',
        attr = dict(
            address = dict(
                optional = True,
                default  = None,
                access   = 'rwx',
            ),
            hostname = dict(
                values = LOGIN_NODES,
            ),
        )
    )

    def get_syslog(self):
        """Return a SysLog on domain socket given by ``address`` attribute."""
        if self.address is None:
            self.address = self.sh.default_syslog
        return SysLogHandler(self.address, self.facility, None)


class AlarmRemoteService(AlarmService):
    """
    Class responsible for handling alarm data through domain socket.
    This class should not be called directly.
    """

    _footprint = dict(
        info = 'Alarm services class',
        attr = dict(
            syshost = dict(
                optional = False,
            ),
            sysport = dict(
                type     = int,
                optional = True,
                default  = 514,
            ),
            socktype = dict(
                type     = int,
                optional = True,
                default  = socket.SOCK_DGRAM,
            ),
            hostname = dict(
                values = LOGIN_NODES,
            ),
        )
    )

    def get_syslog(self):
        """Return a SysLog on remote socket given by ``syshost`` and ``sysport`` attributes."""
        return SysLogHandler((self.syshost, self.sysport), self.facility, self.socktype)


class RoutingService(Service):
    """
    Abstract class for routing services (BDAP, BDM, BDPE).
    Inheritance graph below this class:

      * :class:`RoutingUpstreamService`

        * :class:`BdmService`
        * :class:`BdapService`

      * :class:`BdpeService`

        * :class:`BdpeOperationsService`
        * :class:`BdpeIntegrationService`

    This class should not be called directly.
    """

    _abstract = True
    _footprint = dict(
        info = 'Routing services abstract class',
        attr = dict(
            filename = dict(
                access   = 'rwd',
            ),
            productid = dict(
                type     = int,
            ),
            agt_path  = dict(
                optional = True,
                default  = None
            ),
            resuldir  = dict(
                optional = True,
                default  = None
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('RoutingService init %s', self.__class__)
        super(RoutingService, self).__init__(*args, **kw)

    def get_cmdline(self):
        """Complete command line that runs the Transfer Agent."""
        raise NotImplementedError()

    def get_logline(self):
        """Build the line to send to IGA main routing log file."""
        raise NotImplementedError()

    @property
    def realkind(self):
        return 'routing'

    def mandatory_env(self, key):
        """Retrieve a key from the environment, or raise."""
        value = self.sh.env[key]
        if not value:
            raise KeyError('missing ' + key + ' in the environment')
        return value

    def actual_agt_path(self):
        """Path to use for the agt routing binaries."""
        return tunable_value(self.sh,
                             self.agt_path,
                             'AGT_PATH',
                             'services:agt_path')

    def agt_env(self):
        """Environment for the agt routing binaries (case counts)."""
        keys = ['HOME_SOPRA', 'LD_LIBRARY_PATH',
                'base_transfert_agent', 'DIAP_AGENT_NUMPROG_AGENT']
        vals = ["export " + key + "="
                + self.sh.target().get('agt:'+key.upper()) for key in keys]
        return ' ; '.join(vals)

    @property
    def taskname(self):
        """IGA task name (TACHE)."""
        return self.sh.env.get('SLURM_JOB_NAME', 'interactif')

    @property
    def dmt_date_pivot(self):
        return self.mandatory_env('DMT_DATE_PIVOT')

    @property
    def aammjj(self):
        """Date from DMT_DATE_PIVOT or from the 'date' command (from mxpt001 scr/debut)."""
        envkey  = 'DMT_DATE_PIVOT'
        default = date.now().compact(),
        stamp   = self.sh.env.get(envkey, default)
        return stamp[:8]

    def file_ok(self):
        """Check that the file exists, send an alarm if not."""
        if not self.sh.path.exists(self.filename):
            msg = "{0.taskname} routage {0.realkind} du numero {0.productid}" \
                  " impossible - fichier {0.filename} inexistant".format(self)
            ad.alarm(level='critical', message=msg)
            return False
        return True

    def __call__(self):
        """Actual service execution."""

        self.filename = self.sh.path.abspath(self.filename)

        cmdline = self.get_cmdline()
        if cmdline is None:
            return False

        if not self.file_ok():
            return False

        rcp = RemoteCommandProxy(nodekind='transfer')
        rc = rcp.execute(cmdline)

        logfile = 'routage.' + date.today().ymd
        ad.report(kind='dayfile', mode='RAW', message=self.get_logline(),
                  resuldir=self.resuldir, filename=logfile)

        if not rc:
            # BDM call has no term
            if hasattr(self, 'term'):
                term = ' echeance ' + str(self.term)
            else:
                term = ''
            text = "{0.taskname} Pb envoi {0.realkind} id {0.productid}{term}".format(self, term=term)
            ad.alarm(level='critical', message=text)
            return False

        return True


class RoutingUpstreamService(RoutingService):
    """
    Abstract class for upstream database feeding (router_pa: BDAP, BDM).
    This class should not be called directly.
    """

    _abstract = True
    _footprint = dict(
        info = 'Abstract class for upstream routing services',
        attr = dict(
            agt_pa_cmd = dict(
                optional = True,
                default  = None
            ),
        ),
    )

    def __init__(self, *args, **kw):
        logger.debug('RoutingUpstreamService init %s', self.__class__)
        super(RoutingUpstreamService, self).__init__(*args, **kw)

    def get_logline(self):
        """Build the line to send to the IGA log file."""
        raise NotImplementedError()

    def actual_agt_pa_cmd(self):
        """Actual routing command, without options."""
        pa_cmd = tunable_value(self.sh,
                               self.agt_pa_cmd,
                               None,
                               'services:agt_pa_cmd',
                               'router_pa.bin')
        binary = self.sh.path.join(self.actual_agt_path(), pa_cmd)
        return self.agt_env() + ' ; ' + binary

    def get_cmdline(self):
        """Complete command line that runs the Transfer Agent."""
        # The only mode implemented is "tables usage": "productid -R"
        # The "addresses" mode is unused: "-L client [client...]"
        options = "{0.filename} {0.productid} {mode}".format(self, mode="-R")
        return self.actual_agt_pa_cmd() + ' ' + options


class BdmService(RoutingUpstreamService):
    """
    Class responsible for handling bdm data.
    This class should not be called directly.
    """

    _footprint = dict(
        info = 'Bdm service class',
        attr = dict(
            kind = dict(
                values   = ['bdm'],
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('BdmService init %s', self.__class__)
        super(BdmService, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'BDM'

    def get_logline(self):
        """No log for bdm."""
        return None


class BdapService(RoutingUpstreamService):
    """
    Class responsible for handling bdap data.
    This class should not be called directly.
    """

    _footprint = dict(
        info = 'Bdap service class',
        attr = dict(
            kind = dict(
                values   = ['bdap'],
            ),
            domain = dict(
                type     = str,
            ),
            term = a_term,
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('BdapService init %s', self.__class__)
        super(BdapService, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'BDAP'

    def get_logline(self):
        """Build the line to send to IGA main routing log file."""
        return "{now}@{0.taskname}@{0.domain}@{0.term.hour:03d}@${0.productid}@{0.filename}" \
               "@{0.realkind}".format(self, now=date.now().compact())


class BdpeService(RoutingService):
    """
    Abstract class for handling bdpe data.
    This class should not be called directly.
    """

    _abstract = True
    _footprint = dict(
        info = 'Bdpe abstract service class',
        attr = dict(
            kind = dict(
                values   = ['bdpe'],
            ),
            producer = dict(
                optional = True,
                default  = 'fpe',
            ),
            routingkey = dict(
                type     = str,
            ),
            quality = dict(
                values = range(10),
                optional = True,
                default  = 0,
            ),
            agt_pe_cmd = dict(
                optional = True,
                default  = None
            ),
            term = a_term,
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('BdpeService init %s', self.__class__)
        super(BdpeService, self).__init__(*args, **kw)

    @property
    def actual_routingkey(self):
        """Return the actual routing key to use for the 'router_pe' call."""
        raise NotImplementedError()

    def __call__(self):
        rc = super(BdpeService, self).__call__()
        if rc:
            self.bdpe_log()
        return rc

    @property
    def realkind(self):
        return 'BDPE'

    def bdpe_log(self):
        """Additionnal log file specific to BDPE calls."""
        text = "envoi_bdpe.{0.producer} {0.productid} {0.taskname} {mode} " \
               "{0.routingkey}".format(self, mode='routage par cle')
        logfile = 'log_envoi_bdpe.' + self.aammjj
        ad.report(kind='dayfile', message=text, resuldir=self.resuldir,
                  filename=logfile, mode='RAW')

    def get_logline(self):
        """Build the line to send to IGA main routing log file."""
        s = "{now}@{0.taskname}@missing@{0.term.hour:03d}@{0.actual_routingkey}" \
            "@{0.filename}@{0.realkind}_{0.producer}"
        return s.format(self, now=date.now().compact())

    def actual_agt_pe_cmd(self):
        """Actual routing command, without options."""
        pe_cmd = tunable_value(self.sh, self.agt_pe_cmd, None, 'services:agt_pe_cmd', 'router_pe.bin')
        binary = self.sh.path.join(self.actual_agt_path(), pe_cmd)
        return self.agt_env() + ' ; ' + binary

    def get_cmdline(self):
        """Complete command line that runs the Transfer Agent."""
        if self.actual_routingkey is None:
            return None
        options = "{0.filename} {0.actual_routingkey} -p {0.producer}" \
                  " -n {0.productid} -e {0.term.fmtraw} -d {0.dmt_date_pivot}" \
                  " -q {0.quality} -r {0.soprano_target}".format(self)
        return self.actual_agt_pe_cmd() + ' ' + options


class BdpeOperationsService(BdpeService):
    """
    Class handling BDPE routing for operations
    This class should not be called directly.
    """

    _footprint = dict(
        info = 'Bdpe service class for operations',
        attr = dict(
            soprano_target = dict(
                values   = ('piccolo',),
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('BdpeOperationsService init %s', self.__class__)
        super(BdpeOperationsService, self).__init__(*args, **kw)

    @property
    def actual_routingkey(self):
        """Actual route key to use for operations."""
        rules = {
            'bdpe':                10001,
            'bdpe.gironde':        10130,
            'e_transmet_fac':      10212,
            'bdpe.e_transmet_fac': 10116,
        }
        default = '{0.productid}{0.term.fmtraw}'.format(self)
        return rules.get(self.routingkey.lower(), default)


class BdpeIntegrationService(BdpeService):
    """
    Class handling BDPE routing for integration
    This class should not be called directly.
    """

    _footprint = dict(
        info = 'Bdpe service class for integration',
        attr = dict(
            soprano_target = dict(
                values   = ('piccolo-int',),
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('BdpeIntegrationService init %s', self.__class__)
        super(BdpeIntegrationService, self).__init__(*args, **kw)

    @property
    def actual_routingkey(self):
        """Actuel route key to use for integration."""
        if self.routingkey.lower() == 'bdpe':
            return 10001

        rule = r'.*8124.*|.*8123.*|.*8119.*|.*7148.*|11161.*|11162.*|11163.*|10413.*|10414.*|10415.*'
        # ou bien:
        # rule = r'.*(8124|8123|8119|7148).*|(11161|11162|11163|10413|10414|10415).*'
        # ou encore (mais avec re.search):
        # rule = r'8124|8123|8119|7148|^11161|^11162|^11163|^10413|^10414|^10415'
        if not re.match(rule, str(self.productid)):
            return 10001

        msg = 'Pas de routage du produit {productid} en integration ({filename})'.format(
            productid=self.productid,
            filename=self.filename,
        )
        logger.info(msg)
        return None


class DayfileReportService(FileReportService):
    """
    Historical dayfile reporting for IGA usage.

      * to a known filename
      * to a temporary spool (see demon_messday.pl).

    This class should not be called directly.
    """

    _footprint = dict(
        info = 'Historical dayfile reporting service',
        attr = dict(
            kind = dict(
                values = ['dayfile'],
            ),
            message = dict(
                optional = True,
                default  = '',
            ),
            mode = dict(
                optional = True,
                default  = 'TEXTE',
                values   = ('TEXTE', 'ECHEANCE', 'DEBUT', 'FIN', 'ERREUR', 'RAW'),
            ),
            filename = dict(
                optional = True,
                default  = None,
            ),
            resuldir  = dict(
                optional = True,
                default  = None
            ),
            spooldir  = dict(
                optional = True,
                default  = None
            ),
            task = dict(
                optional = True,
                default  = None,
            ),
        )
    )

    @property
    def taskname(self):
        """IGA task name (TACHE)."""
        if self.task is None:
            return self.sh.env.get('SLURM_JOB_NAME', 'interactif')
        return self.task

    @property
    def timestamp(self):
        """Formatted hour used as standard prefix in log files."""
        return '{0.hour:02d}-{0.minute:02d}-{0.second:02d}'.format(date.now())

    def actual_resuldir(self):
        """The directory where to write named log files."""
        return tunable_value(self.sh,
                             self.resuldir,
                             'OP_RESULDIR',
                             'services:resuldir',
                             '.')

    def actual_spooldir(self):
        """The directory where to write spooled log files."""
        default = self.sh.path.join(self.sh.env.HOME, 'spool_messdayf')
        return tunable_value(self.sh,
                             self.spooldir,
                             'OP_SPOOLDIR',
                             'services:spooldir',
                             default)

    def direct_target(self):
        """
        Absolute name of the file to write to, when filename is known.
        The path defaults to resuldir for named log files.
        """
        if self.sh.path.isabs(self.filename):
            return self.filename
        name = self.sh.path.join(self.actual_resuldir(), self.filename)
        return self.sh.path.abspath(name)

    def spooled_target(self):
        """
        Absolute name of the spooled file to write to. The path
        defaults to spooldir for these parts of centralized log files.
        """
        name = ''.join([
            str(date.now().epoch),
            '_',
            self.sh.env.get('NQSID', ''),
            '1' if 'DEBUT' in self.mode else '0',
            str(random.random()),
        ])
        final = self.sh.path.join(self.actual_spooldir(), name)
        return self.sh.path.abspath(final)

    def __call__(self):
        """Main action: format, open, write, close, clean."""

        if self.message is None:
            return

        fmt = dict(
            RAW        = '{0.message}',
            TEXTE      = '{0.timestamp} -> {0.message}',
            ECHEANCE   = '{0.timestamp} == {0.message}',
            DEBUT      = '{0.timestamp} == {0.mode}    {0.taskname} === noeuds {0.message}',
            FIN        = '{0.timestamp} == {0.mode} OK {0.taskname} ===',
            ERREUR     = '{0.timestamp} == {0.mode} {0.taskname} *****'
        )
        infos = fmt[self.mode].format(self) + '\n'

        if self.filename:
            final = None
            destination = self.direct_target()
        else:
            final = self.spooled_target()
            destination = final + '.tmp'

        self.sh.filecocoon(destination)
        with open(destination, 'a') as fp:
            fp.write(infos)

        if not self.filename:
            self.sh.mv(destination, final)
