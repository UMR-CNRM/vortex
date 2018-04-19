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
import six
import socket

from StringIO import StringIO
from logging.handlers import SysLogHandler

from bronx.stdtypes import date
from bronx.stdtypes.date import Time
import footprints
from footprints.stdtypes import FPDict
import vortex
from common.tools.agt import agt_actual_command
from vortex.syntax.stdattrs import DelayedEnvValue
from vortex.syntax.stdattrs import a_term, a_domain
from vortex.tools.actions import actiond as ad
from vortex.tools.schedulers import SMS
from vortex.tools.services import Service, FileReportService, TemplatedMailService
from vortex.util.config import GenericReadOnlyConfigParser
from iga.tools.transmet import get_ttaaii_transmet_sh
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
                values = [str(False), ],
                default = '[systemtarget:issyslognode]',
                optional = True
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
        if self.sshhost is None:
            sshobj = self.sh.ssh(hostname='syslog', virtualnode=True)
        else:
            sshobj = self.sh.ssh(hostname=self.sshhost)
        rc = sshobj.execute(command)
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
                values   = [str(True), ],
                default  = '[systemtarget:issyslognode]',
                optional = True
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
                values   = [str(True), ],
                default  = '[systemtarget:issyslognode]',
                optional = True
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
            ),
            maxtries = dict(
                type     = int,
                optional = True,
                default  = 5,
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('RoutingService init %s', self.__class__)
        super(RoutingService, self).__init__(*args, **kw)
        self._actual_filename = self.sh.path.abspath(self.filename)

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
    def _actual_targetname(self):
        if self.targetname is not None:
            return self.sh.path.join(self.sh.path.dirname(self._actual_filename),
                                     self.targetname)
        else:
            return None

    @property
    def routing_name(self):
        return self._actual_targetname or self._actual_filename

    def file_ok(self):
        """Check that the file exists, send an alarm if not."""
        if not self.sh.path.exists(self._actual_filename):
            msg = "{0.taskname} routage {0.realkind} du numero {0.productid}" \
                  " impossible - fichier {0.filename} inexistant".format(self)
            logger.warning(msg)
            ad.alarm(level='critical', message=msg, sshhost=self.sshhost)
            return False
        return True

    def __call__(self):
        """Actual service execution."""

        if not self.file_ok():
            return False

        if self._actual_targetname:
            if self.sh.path.exists(self._actual_targetname):
                raise ValueError("Won't overwrite file '{}'".format(self._actual_targetname))
            self.sh.cp(self._actual_filename, self._actual_targetname, intent='in')

        cmdline = self.get_cmdline()
        if cmdline is None:
            return False

        if self.sshhost is None:
            if self.sh.default_target.isagtnode:
                rc = self.sh.spawn(cmdline, shell=True, output=True)
            else:
                sshobj = self.sh.ssh(hostname='agt', virtualnode=True, maxtries=self.maxtries)
                rc = sshobj.execute(cmdline)
        else:
            sshobj = self.sh.ssh(hostname=self.sshhost, maxtries=self.maxtries)
            rc = sshobj.execute(cmdline)

        if self._actual_targetname:
            self.sh.remove(self._actual_targetname)

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
            logger.warning(text)
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

    _footprint = dict(
        info = 'Bdpe service class',
        attr = dict(
            kind = dict(
                values   = ['bdpe'],
            ),
            soprano_target = dict(
                values   = ['piccolo', 'piccolo-int'],
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
        self.inifile = '@opbdpe.ini'
        self.iniparser = GenericReadOnlyConfigParser(self.inifile)

    @property
    def actual_routingkey(self):
        """Return the actual routing key to use for the 'router_pe' call."""

        rule = self.iniparser.get(self.soprano_target, 'rule_exclude')
        if re.match(rule, str(self.productid)):
            msg = 'Pas de routage du produit {productid} sur {soprano_target} ({filename})'.format(
                productid=self.productid,
                filename=self.filename,
                soprano_target=self.soprano_target,
            )
            logger.info(msg)
            return None

        default = '{0.productid}{0.term.fmtraw}'.format(self)
        return self.iniparser.get(self.soprano_target, self.routingkey.lower(), default)

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


class TransmetService(BdpeService):
    """
    Class responsible for handling transmet data.

    The **version_header** attribute impact the header generation :

        * 'TTAAII' use the 'entete_fichier_transmet.sh' script to
          generate the header into a empty file and the filename used for routing
        * 'gfnc' not implemented (for the new naming rule)

    This class should not be called directly.
    """
    _footprint = dict(
        info = 'transmet service class',
        attr = dict(
            kind = dict(
                values    = ['transmet'],
            ),
            scriptdir = dict(
                optional = True,
                default  = 'scriptdir'
            ),
            transmet_cmd = dict(
                optional = True,
                default  = 'transmet_cmd'
            ),
            transmet = dict(
                optional  = True,
                type      = FPDict,
            ),
            version_header = dict(
                values    = ['TTAAII', 'gfnc'],
                optional  = True,
                default   = 'TTAAII',
            ),
            header_infile = dict(
                optional  = True,
                type      = bool,
                default   = True,
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Transmet init %s', self.__class__)
        super(TransmetService, self).__init__(*args, **kw)
        self._filename_transmet = None

    @property
    def realkind(self):
        return 'TRANSMET'

    @property
    def routing_name(self):
        if self._filename_transmet is None:
            if self.version_header == 'TTAAII':
                actual_transmet = self.transmet if isinstance(self.transmet, dict) else dict()
                self._filename_transmet = get_ttaaii_transmet_sh(self.sh, self.transmet_cmd,
                                                                 actual_transmet, self.filename,
                                                                 self.scriptdir, self.header_infile)
                logger.debug('filename transmet : %s', self._filename_transmet)
            else:
                logger.error('version_header : %s not implemented', self.version_header)
                self._filename_transmet = False
        return self._filename_transmet

    def __call__(self):
        """Actual service execution."""
        if self.routing_name:
            return super(TransmetService, self).__call__()
        else:
            return False


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
            date.now().strftime('%Y%m%d%H%M%S.%f'),
            '_',
            self.env.get('SLURM_JOBID', ''),
            str(self.sh.getpid()),
            '_',
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
                default  = DelayedEnvValue('DMT_SERVER_HOST', 'piccolo'),
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
            sshobj = self.sh.ssh(hostname='network', virtualnode=True)
            rc = sshobj.execute(cmdline)
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

    def substitution_dictionary(self, add_ons=None):
        sdict = super(OpMailService, self).substitution_dictionary(add_ons=add_ons)
        if 'OP_RUNDATE' in sdict:
            sdict.setdefault('RESEAU', sdict['OP_RUNDATE'].hh)
        if 'LOG' in sdict:
            sdict.setdefault('LOGPATH', sdict['LOG'])
        if 'RUNDIR' in sdict and 'task' in sdict:
            sdict.setdefault('RUNDIR', sdict['RUNDIR'] + '/opview/' + sdict['task'])
        if 'OP_VAPP' in sdict:
            sdict.setdefault('VAPP', sdict['OP_VAPP'].upper())
        if 'OP_VCONF' in sdict:
            sdict.setdefault('VCONF', sdict['OP_VCONF'].lower())
        if 'OP_XPID' in sdict:
            sdict.setdefault('XPID', sdict['OP_XPID'].lower())
        if sdict.get('OP_HASMEMBER', False) and 'OP_MEMBER' in sdict:
            sdict.setdefault('MEMBER_S1_FR_FR', ' du membre {:d}'.format(int(sdict['OP_MEMBER'])))
        else:
            sdict.setdefault('MEMBER_S1_FR_FR', '')
        return sdict

    def _template_name_rewrite(self, tplguess):
        if not tplguess.startswith('@opmails/'):
            tplguess = '@opmails/' + tplguess
        if not tplguess.endswith('.tpl'):
            tplguess += '.tpl'
        return tplguess

    def header(self):
        """String prepended to the message body."""
        locale.setlocale(locale.LC_ALL, u'fr_FR.UTF-8')
        now = date.now()
        stamp1 = now.strftime(u'%A %d %B %Y')
        stamp2 = now.strftime(u'%X')
        if six.PY2:
            penc = locale.getpreferredencoding()
            stamp1 = stamp1.decode(penc)
            stamp2 = stamp2.decode(penc)
        return u'Mail envoyé le {} à {} locales.\n--\n\n'.format(stamp1, stamp2)

    def trailer(self):
        """String appended to the message body."""
        return (u'\n--\nEnvoi automatique par Vortex {} pour <{}@{}>.\n'
                .format(vortex.__version__,
                        self.env.user, self.sh.default_target.inetname))

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
