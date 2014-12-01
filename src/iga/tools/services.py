#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
The module contains the service adapted to the actions present in the actions
module. We have an abstract class Services (inheritating from FootprintBase)
and 3 more classes inheritating from it: AlarmService, BdapService, RoutingService.
These classes are adpated to handle the data dedicated to the action to be
performed.
"""

#: No automatic export
__all__ = []

import logging
from logging.handlers import SysLogHandler

import re
import socket
from StringIO import StringIO

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex import sessions
from vortex.tools import date
from vortex.tools.services import Service
from vortex.tools.actions import actiond as ad
from vortex.tools.systems import ExecutionError

# TODO devrait dépendre d'un objet TARGET
LOGIN_NODES = [
    x + str(y)
    for x in ('prolixlogin', 'beaufixlogin', )
    for y in range(6)
]


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
        """Reverse access: deduce the name from the integer value"""
        for s, n in SysLogHandler.facility_names.iteritems():
            if self == n:
                return s
        raise ValueError('Not a SysLog facility value: ' + str(self))


def tunable_value(sh, value, env_key=None, ini_key=None, default=None):
    """Try to get a value from several sources in turn:
       - a real value (e.g. from the footprint)
       - the environment
       - the ini files
       - a default value in last resort"""
    if value:
        return value
    if env_key and env_key in sh.env:
        return sh.env[env_key]
    if ini_key:
        return sh.target().get(ini_key, default)
    return default


class RemoteCommandProxy(footprints.FootprintBase):
    """
    Remote execution via ssh on a special node
    """
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
        """Node name to use for this kind of remote execution"""
        key = self.nodekind + 'node'
        return tunable_value(self.sh,
                             getattr(self, key, None),
                             ini_key='services:' + key,
                             env_key=key.upper(),
                             default='localhost')

    def execute(self, command):
        """Remote execution"""
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
       - AlarmProxyService (external 'logger' command for non-login nodes)
       - AlarmLogService   (syslog based on 'address')
       - AlarmRemoteService(syslog based on 'syshost', 'sysport' and 'socktype')
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
            alarmfmt = dict(
                optional = True,
                default  = None,
            ),
        )
    )

    def get_syslog(self):
        """Define and return the SyslogHandler to use."""
        pass

    def get_logger_action(self):
        """
        Define a SysLogHandler to broadcast the alarm.
        Return the actual logging method.
        """

        # create the syslog handler
        hand = self.get_syslog()
        hand.setFormatter(logging.Formatter(self.alarmfmt))
        logger.addHandler(hand)

        return getattr(logger, self.level, logger.warning)

    def get_message(self):
        """Return the actual message to log."""
        return self.message

    def __call__(self):
        """Main action: pack the message to the actual logger action."""
        logmethod = self.get_logger_action()
        return logmethod(self.get_message())


class AlarmProxyService(AlarmService):
    """
    Class responsible for handling alarm data through the remote
    unix 'logger' command invocation (mandatory on non-login nodes)
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

    def get_syslog(self):
        """Return an in-memory handler"""
        self.buffer = StringIO()
        self.handler = logging.StreamHandler(self.buffer)
        return self.handler

    def priority(self, level):
        """
        Map a logging level to a SysLogHandler priority
        for the unix 'logger' command.
        """
        if level == 'critical':
            return 'crit'
        return level

    def __call__(self):
        """Main action: pack the message to the actual logger command."""

        # send to the logger as usual
        super(AlarmProxyService, self).__call__()

        # get the formatted message from the logger
        self.handler.flush()
        self.buffer.flush()
        message = self.buffer.getvalue().rstrip('\n')
        self.buffer.truncate(0)

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
                optional = True,
                default = 'localhost',
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
        RoutingUpstreamService
            BdmService
            BdapService
        BdpeService
            BdpeOperationsService
            BdpeIntegrationService
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
        """Build the command line that runs the Transfer Agent."""
        raise NotImplementedError()

    def get_logline(self):
        """Build the line to send to the IGA log file."""
        raise NotImplementedError()

    @property
    def realkind(self):
        return 'routing'

    def mandatory_ini(self, key):
        """Retrieve a key from the ini files, or raise"""
        value = self.sh.target().get(key)
        if not value:
            raise KeyError('missing key ' + key + ' in ini files')
        return value

    def mandatory_env(self, key):
        """Retrieve a key from the environment, or raise"""
        value = self.sh.env[key]
        if not value:
            raise KeyError('missing ' + key + ' in the environment')
        return value

    def actual_agt_path(self):
        """Path to use for the agt routing binaries"""
        return tunable_value(self.sh,
                             self.agt_path,
                             'AGT_PATH',
                             'services:agt_path')

    def agt_env(self):
        """Environment for the agt routing binaries (case counts)"""
        keys = ['HOME_SOPRA', 'LD_LIBRARY_PATH',
                'base_transfert_agent', 'DIAP_AGENT_NUMPROG_AGENT']
        vals = ["export " + key + "="
                + self.sh.target().get('agt:'+key.upper()) for key in keys]
        return ' ; '.join(vals)

    @property
    def taskname(self):
        """IGA task name (TACHE)"""
        return self.sh.env.get('SLURM_JOB_NAME', 'interactif')

    @property
    def dmt_date_pivot(self):
        return self.mandatory_env('DMT_DATE_PIVOT')

    @property
    def aammjj(self):
        """date from DMT_DATE_PIVOT or from the 'date' command (from mxpt001 scr/debut)"""
        envkey  = 'DMT_DATE_PIVOT'
        default = date.now().compact(),
        stamp   = self.sh.env.get(envkey, default)
        return stamp[:8]

    def file_ok(self):
        """check that the file exists, send an alarm if not"""
        self.filename = self.sh.path.abspath(self.filename)
        if not self.sh.path.exists(self.filename):
            msg = "{0.taskname} routage {0.realkind} du numero {0.productid}" \
                  " impossible - fichier {0.filename} inexistant".format(self)
            ad.alarm(level='critical', message=msg)
            return False
        return True

    def actual_resuldir(self):
        """The directory where to write IGA log files"""
        return tunable_value(self.sh,
                             self.resuldir,
                             'AGT_RESULDIR',
                             'services:resuldir',
                             '.')

    def iga_log(self, logline, logfile=None):
        """Append a line to IGA routage log file"""
        if not logline:
            return

        if not logfile:
            resuldir = self.actual_resuldir()
            self.sh.mkdir(resuldir)
            logfile = self.sh.path.join(resuldir, 'routage.') + date.today().ymd

        with open(logfile, 'a') as fp:
            fp.write(logline+'\n')

    def __call__(self):
        """Actual service execution"""

        cmdline = self.get_cmdline()
        if cmdline is None:
            return False

        if not self.file_ok():
            return False

        rcp = RemoteCommandProxy(nodekind='transfer')
        rc = rcp.execute(cmdline)

        logline = self.get_logline()
        self.iga_log(logline)

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
        """build the line to send to the IGA log file."""
        raise NotImplementedError()

    def actual_agt_pa_cmd(self):
        pa_cmd = tunable_value(self.sh,
                               self.agt_pa_cmd,
                               None,
                               'services:agt_pa_cmd',
                               'router_pa.bin')
        binary = self.sh.path.join(self.actual_agt_path(), pa_cmd)
        return self.agt_env() + ' ; ' + binary

    def get_cmdline(self):
        # seul le mode "utiliser les tables" semble servir
        #     "productid -R"
        # le mode "adresses" ferait:
        #     "-L client [client...]"
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
        # logger.debug('BdmService init %s', self.__class__)
        super(BdmService, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'BDM'

    def get_logline(self):
        """no log for bdm"""
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
            term = dict(
                type     = int,
                alias    = ('term_hhh',),
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('BdapService init %s', self.__class__)
        super(BdapService, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'BDAP'

    def get_logline(self):
        return "{now}@{0.taskname}@{0.domain}@{0.term:03d}@${0.productid}@{0.filename}" \
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
            cleroutage = dict(
                type     = str,
            ),
            term = dict(
                type     = int,
                alias    = ('term_hhhhmm',),
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
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('BdpeService init %s', self.__class__)
        super(BdpeService, self).__init__(*args, **kw)

    @property
    def agt_cleroutage(self):
        """return the actual routing key to use for the 'router_pe' call"""
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
        """BDPE has an additional log file"""
        text = "envoi_bdpe.{0.producer} {0.productid} {0.taskname} {mode} " \
               "{0.cleroutage}".format(self, mode='routage par cle')
        resuldir = self.actual_resuldir()
        logfile = self.sh.path.join(resuldir, 'log_envoi_bdpe.') + self.aammjj
        self.iga_log(text, logfile)
        return True

    def get_logline(self):
        s = "{now}@{0.taskname}@missing@{0.term:03d}@{0.agt_cleroutage}" \
            "@{0.filename}@{0.realkind}_{0.producer}"
        return s.format(self, now=date.now().compact())

    def actual_agt_pe_cmd(self):
        pe_cmd = tunable_value(self.sh, self.agt_pe_cmd, None, 'services:agt_pe_cmd', 'router_pe.bin')
        binary = self.sh.path.join(self.actual_agt_path(), pe_cmd)
        return self.agt_env() + ' ; ' + binary

    def get_cmdline(self):
        """Router_pe command line to run on the transfer node"""
        if self.agt_cleroutage is None:
            return None
        options = "{0.filename} {0.agt_cleroutage} -p {0.producer}" \
                  " -n {0.productid} -e {0.term:06d} -d {0.dmt_date_pivot}" \
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
    def agt_cleroutage(self):
        """agt_cleroutage for operations"""
        rules = {
            'bdpe':                10001,
            'bdpe.gironde':        10130,
            'e_transmet_fac':      10212,
            'bdpe.e_transmet_fac': 10116,
        }
        default = '{0.productid}{0.term:06d}'.format(self)
        return rules.get(self.cleroutage.lower(), default)


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
    def agt_cleroutage(self):
        """agt_cleroutage for integration"""
        if self.cleroutage.lower() == 'bdpe':
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
