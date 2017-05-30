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
"""

import locale
import logging
import random
import re
import socket
from StringIO import StringIO
from logging.handlers import SysLogHandler

import footprints
import vortex
from common.tools.agt import agt_actual_command
from vortex.syntax.stdattrs import DelayedEnvValue
from vortex.syntax.stdattrs import a_term, a_domain
from vortex.tools import date
from vortex.tools.actions import actiond as ad
from vortex.tools.schedulers import SMS
from vortex.tools.services import Service, FileReportService, TemplatedMailService
from vortex.tools.date import Time
#: Export nothing
__all__ = []

logger = footprints.loggers.getLogger(__name__)

# default Formatter for alarm logfile output
DEFAULT_ALARMLOG_FORMATTER = logging.Formatter(
    fmt='[%(asctime)s][%(name)s][%(levelname)s]: %(message)s',
    datefmt='%Y/%m/%d-%H:%M:%S',
)

# Syslog formatting *must* be compatible with RFC 5424., e.g.
# SYSLOG_FORMATTER = logging.Formatter(
#    fmt='%(asctime)s %(name)s: %(levelname)s %(message)s',
#    datefmt='%b %e %H:%M:%S',
# )
# or this one:
SYSLOG_FORMATTER = logging.Formatter(
    fmt='%(asctime)s [%(name)s][%(levelname)s]: %(message)s',
    datefmt='%Y/%m/%d T %H:%M:%S',
)


class LogFacility(int):
    """
    Attribute for SysLogHandler facility value, could be either a valid ``int``
    or a logging name such as ``log_local7`` or ``local7``.
    """

    def __new__(cls, value):
        if isinstance(value, basestring):
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
            sshhost=dict(
                optional = True,
                default  = 'node',
            ),
        )
    )

    def deactivated(self):
        """Tells if alarms are deactivated : OP_ALARM set to 0"""
        return not bool(self.env.get('OP_ALARM', 1))

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
            issyslognode = dict(
                values = [False, ],
                default = '[systemtarget:issyslognode]',
                type = bool,
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
        rc = ad.ssh(command, hostname=self.sshhost, nodetype='syslog')
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
            issyslognode = dict(
                values   = [True, ],
                default  = '[systemtarget:issyslognode]',
                type     = bool,
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
            issyslognode = dict(
                values   = [True, ],
                default  = '[systemtarget:issyslognode]',
                type     = bool,
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
            targetname = dict(
                optional = True,
                default  = None
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
            sshhost   = dict(
                optional = True,
                default  = 'node',
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
        value = self.env[key]
        if not value:
            raise KeyError('missing ' + key + ' in the environment')
        return value

    @property
    def taskname(self):
        """IGA task name (TACHE)."""
        return self.env.get('SLURM_JOB_NAME') or self.env.get('SMSNAME', 'interactif')

    @property
    def dmt_date_pivot(self):
        return self.mandatory_env('DMT_DATE_PIVOT')

    @property
    def aammjj(self):
        """Date from DMT_DATE_PIVOT or from the 'date' command (from mxpt001 scr/debut)."""
        envkey = 'DMT_DATE_PIVOT'
        default = date.now().compact(),
        stamp = self.env.get(envkey, default)
        return stamp[:8]

    @property
    def routing_name(self):
        return self.targetname or self.filename

    def file_ok(self):
        """Check that the file exists, send an alarm if not."""
        if not self.sh.path.exists(self.filename):
            msg = "{0.taskname} routage {0.realkind} du numero {0.productid}" \
                  " impossible - fichier {0.filename} inexistant".format(self)
            ad.alarm(level='critical', message=msg, sshhost=self.sshhost)
            return False
        return True

    def __call__(self):
        """Actual service execution."""

        self.filename = self.sh.path.abspath(self.filename)

        if not self.file_ok():
            return False

        if self.targetname:
            if self.sh.path.exists(self.targetname):
                raise ValueError("Won't overwrite file '{}'".format(self.targetname))
            self.sh.cp(self.filename, self.targetname, intent='in')

        cmdline = self.get_cmdline()
        if cmdline is None:
            return False

        rc = ad.ssh(cmdline, hostname=self.sshhost, nodetype='agt')

        if self.targetname:
            self.sh.remove(self.targetname)

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
            ad.alarm(level='critical', message=text, sshhost=self.sshhost)
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
                default  = 'agt_pa_cmd',
            ),
        ),
    )

    def __init__(self, *args, **kw):
        logger.debug('RoutingUpstreamService init %s', self.__class__)
        super(RoutingUpstreamService, self).__init__(*args, **kw)

    def get_logline(self):
        """Build the line to send to the IGA log file."""
        raise NotImplementedError()

    def get_cmdline(self):
        """Complete command line that runs the Transfer Agent."""
        # The only mode implemented is "tables usage": "productid -R"
        # The "addresses" mode is unused: "-L client [client...]"
        options = "{0.routing_name} {0.productid} {mode}".format(self, mode="-R")
        return agt_actual_command(self.sh, self.agt_pa_cmd, options)


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
            domain = a_domain,
            term   = a_term,
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
        return "{now}@{0.taskname}@{0.domain}@{0.term.hour:03d}@{0.productid}@{0.filename}" \
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
                default  = 'agt_pe_cmd',
            ),
            term = dict(
                optional = True,
                type     = Time,
                default  = '0',
            ),
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
        """The actual call to the service."""
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

    def get_cmdline(self):
        """Complete command line that runs the Transfer Agent."""
        if self.actual_routingkey is None:
            return None
        options = "{0.routing_name} {0.actual_routingkey} -p {0.producer}" \
                  " -n {0.productid} -e {0.term.fmtraw} -d {0.dmt_date_pivot}" \
                  " -q {0.quality} -r {0.soprano_target}".format(self)
        return agt_actual_command(self.sh, self.agt_pe_cmd, options)


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
            'bdpe.synopsis_preprod': 10433,

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

      * to a known file named filename
      * or to a temporary spool (see demon_messday.pl).
      * in async mode, requests are sent to the jeeves daemon.

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
                access   = 'rwx',
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
            async = dict(
                optional = True,
                type     = bool,
                default  = False,
            ),
            jname=dict(
                optional=True,
                default='test',
            ),
        )
    )

    @property
    def taskname(self):
        """IGA task name (TACHE)."""
        if self.task is None:
            return self.env.get('SLURM_JOB_NAME') or self.env.get('SMSNAME', 'interactif')
        return self.task

    @property
    def nodelist(self):
        """Nodeset of the task (could be expanded)."""
        return self.env.get('SLURM_JOB_NODELIST') or '<SLURM_JOB_NODELIST missing>'

    @property
    def timestamp(self):
        """Formatted hour used as standard prefix in log files."""
        return '{0.hour:02d}-{0.minute:02d}-{0.second:02d}'.format(date.now())

    def direct_target(self):
        """
        Absolute name of the file to write to, when filename is known.
        The path defaults to resuldir for named log files.
        """
        if self.sh.path.isabs(self.filename):
            return self.filename
        name = self.sh.path.join(
            self.actual_value('resuldir', as_var='OP_RESULDIR', default='.'),
            self.filename
        )
        return self.sh.path.abspath(name)

    def spooled_target(self):
        """
        Absolute name of the spooled file to write to. The path
        defaults to spooldir for these parts of centralized log files.
        """
        name = ''.join([
            str(date.now().epoch),
            '_',
            self.env.get('NQSID', ''),
            '1' if 'DEBUT' in self.mode else '0',
            str(random.random()),
        ])
        final = self.sh.path.join(
            self.actual_value(
                'spooldir',
                as_var='OP_SPOOLDIR',
                default=self.sh.path.join(self.env.HOME, 'spool_messdayf')
            ),
            name
        )
        return self.sh.path.abspath(final)

    @property
    def infos(self):
        fmt = dict(
            RAW='{0.message}',
            TEXTE='{0.timestamp} -> {0.message}',
            ECHEANCE='{0.timestamp} == {0.message}',
            DEBUT='{0.timestamp} == {0.mode}    {0.taskname} === noeuds {0.nodelist}',
            FIN='{0.timestamp} == {0.mode} OK {0.taskname} ===',
            ERREUR='{0.timestamp} == {0.mode} {0.taskname} *****'
        )
        return fmt[self.mode].format(self) + '\n'

    def __call__(self):
        """Main action: format, write or send depending on async."""

        if self.message is None:
            return True

        if self.async:
            if self.filename is None:
                self.filename = 'DAYFMSG.' + date.now().ymd
            target = self.direct_target()
            ad.jeeves(todo='dayfile', infos=self.infos, target=target, jname=self.jname)
            return True

        if self.filename:
            final = None
            target = self.direct_target()
        else:
            final = self.spooled_target()
            target = final + '.tmp'

        self.sh.filecocoon(target)
        with open(target, 'a') as fp:
            fp.write(self.infos)
        if not self.filename:
            self.sh.mv(target, final)

        return True


class SMSOpService(SMS):
    """
    Default SMS service with some extra colorful features.
    """

    _footprint = dict(
        info = 'SMS client service in operational context',
        priority = dict(
            level = footprints.priorities.top.OPER
        )
    )

    def logdate(self, tz='GMT', varname=None, status='unknown', comment=''):
        """Set a logging message for the dedicated XCDP variable."""
        if varname is None:
            logger.error('SMS service could log date message with variable [%s]', str(status))
        else:
            stamp = date.now().compact()
            self.variable(varname, stamp)
            self.label('etat', str(status) + ': ' + stamp + ' ' + str(comment))

    def close_init(self, *args):
        """Set starting date as a XCDP variable."""
        self.logdate(varname='date_execute', status='active')

    def setup_complete(self, *args):
        """Set completing date as a XCDP variable."""
        rc = args[0] if args else 0
        if rc:
            self.logdate(varname='date_end', status='aborted', comment=rc)
        else:
            self.logdate(varname='date_end', status='complete', comment=rc)
        if rc in (0, 98, 99):
            return True
        else:
            self.abort()
            return False


class DMTEventService(Service):
    """
    Class responsible for handling DMT events through the SOPRANO library.
    Mostly used for resources availability.
    """

    _footprint = dict(
        info = 'Send an event to the main monitoring system.',
        attr = dict(
            kind = dict(
                values   = ['dmtevent'],
            ),
            resource_name = dict(
                alias    = ('name',)
            ),
            resource_flag = dict(
                type     = int,
                optional = True,
                alias    = ('description', 'flag'),
                default  = 0,
            ),
            soprano_lib = dict(
                optional = True,
                alias    = ('sopralib', 'lib'),
                default  = '/opt/softs/sopra/lib',
            ),
            soprano_cmd = dict(
                optional = True,
                alias    = ('sopracmd', 'cmd'),
                default  = '/opt/softs/sopra/bin/dmtdisp.bin',
            ),
            soprano_host = dict(
                optional = True,
                alias    = ('soprahost', 'host'),
                default  = DelayedEnvValue('DMT_SERVER_HOST','piccolo'),
            ),
            expectedvars = dict(
                type     = footprints.FPTuple,
                optional = True,
                default  = footprints.FPTuple((
                    'SMS_PROG', 'SMSNODE', 'SMSNAME', 'SMSPASS', 'SMSTRYNO', 'SMSTIMEOUT',
                    'DMT_DATE_PIVOT', 'DMT_ECHEANCE', 'DMT_PATH_EXEC', 'DMT_TRAVAIL_ID', 'DMT_SOUS_SYSTEME'
                )),
            ),
        )
    )

    def get_dmtinfo(self):
        """The pair of usefull information to forward to monitor."""
        return [self.resource_name, str(self.resource_flag)]

    def get_cmdline(self):
        """Complete command line that runs the soprano command."""
        for var in [x for x in self.expectedvars if x not in self.env]:
            logger.warning('DMT missing variable %s', var)
        return ' '.join(
            self.env.mkautolist('SMS') + self.env.mkautolist('DMT_') + [
                'JOB_ID=' + self.env.get('SLURM_JOB_ID', 'NoJobId'),
                'DMT_SERVER_HOST=' + self.soprano_host,
                'LD_LIBRARY_PATH=' + self.soprano_lib,
                self.soprano_cmd,
            ] + self.get_dmtinfo()
        )

    def __call__(self):
        """Set some global variables, then launch the soprano command."""
        cmdline = self.get_cmdline()
        logger.info('DMT Event <%s>', cmdline)
        if not self.sh.default_target.isnetworknode:
            rc = ad.ssh(cmdline, hostname='node', nodetype='network')
        else:
            rc = self.sh.spawn(cmdline, shell=True, output=True)
        return rc


class OpMailService(TemplatedMailService):
    """
    Class responsible for sending predefined mails.
    This class should not be called directly.
    """

    _footprint = dict(
        info = 'OP predefined mail services class',
        attr = dict(
            kind = dict(
                values   = ['opmail'],
            ),
        )
    )

    def __init__(self, *args, **kw):
        super(OpMailService, self).__init__(*args, **kw)

    def deactivated(self):
        """Tells if opmail is deactivated : OP_MAIL set to 0"""
        return not bool(self.env.get('OP_MAIL', 1))

    def header(self):
        """String prepended to the message body."""
        locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
        stamp = date.now().strftime('%A %d %B %Y à %X locales')
        return 'Mail envoyé le {}\n--\n\n'.format(stamp)

    def trailer(self):
        """String appended to the message body."""
        return '\n--\nEnvoi automatique par Vortex {} ' \
               'pour <{}@{}>\n'.format(
            vortex.__version__,
            self.env.user,
            self.sh.default_target.inetname
        )

    def __call__(self, *args):
        """Main action as inherited, and prompts.
        """
        rc = super(OpMailService, self).__call__(*args)
        if not rc:
            ad.prompt(
                comment='OpMailService: mail was not sent.',
                **self.footprint_as_shallow_dict()
            )
        return rc
