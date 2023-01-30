"""
This package handles some common targets used at Meteo France.
"""


import collections
import contextlib
import io
import ftplib
import re
import shlex
import uuid

from bronx.fancies import loggers
import footprints

from vortex.tools.env import Environment, vartrue
from vortex.tools.targets import Target
from vortex.tools.prestaging import PrestagingTool

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


# Any kind of DSI's Supercomputer

class MeteoBullX3(Target):
    """Any MF's third generation of Bullx supercomputer."""

    _abstract = True
    _footprint = dict(
        info = 'Bull Supercomputer at Meteo France',
        attr = dict(
            sysname = dict(
                values = ['Linux', ]
            ),
            inifile = dict(
                default = '@target-[inetname].ini',
            )
        ),
        priority = dict(
            level = footprints.priorities.top.TOOLBOX
        )
    )

    def generic(self):
        """Generic name is inetname suffixed with ``fe`` or ``cn``."""
        if re.search('(login|transfert|nmipt|ndl)', self.hostname):
            return self.inetname + 'fe'
        else:
            return self.inetname + 'cn'

    @contextlib.contextmanager
    def algo_run_context(self, ticket, *kmappings):
        """Specific target hook before any component run."""
        with super().algo_run_context(ticket, *kmappings):
            dis_boost_confkey = 'bullx3_disable_boost'
            dis_boost_cmd = ['clush', '-bw', ticket.env.SLURM_JOB_NODELIST,
                             'sudo', '/opt/softs/amd/{todo:s}_boost_amd.sh']
            dis_boost = any([vartrue.match(str(a_mapping.get(dis_boost_confkey, '0'))) or
                             vartrue.match(str(a_mapping.get('vortex_' + dis_boost_confkey, '0')))
                             for a_mapping in kmappings])
            if dis_boost:
                actual_cmd = [c.format(todo='disable') for c in dis_boost_cmd]
                logger.info('Disabling AMD boost: %s\n', ' '.join(actual_cmd))
                ticket.sh.spawn(actual_cmd, output=False)
            try:
                yield
            finally:
                if dis_boost:
                    actual_cmd = [c.format(todo='enable') for c in dis_boost_cmd]
                    logger.info('Re-enabling AMD boost: %s\n', ' '.join(actual_cmd))
                    ticket.sh.spawn(actual_cmd, output=False)

    def plugable_extra_session_setup(self, ja, t, **kw):
        """When a JobAssitant's setup is called, this bit of code will be used."""
        if t.rundir:
            real_rundir = t.sh.path.realpath(t.rundir)
            # Read Lustre related configuration
            lfs_mapping = collections.defaultdict(list)
            for m_def in self.get('fs:lustre_fs', '').split(' '):
                k, values = m_def.split(':', 1)
                lfs_mapping[k].extend(values.split(','))
            fs_tag = None
            for tag, fss in lfs_mapping.items():
                if any([real_rundir.startswith(fs) for fs in fss]):
                    fs_tag = tag
                    break
            lfs_setstripes = []
            if fs_tag:
                lfs_setstripes = shlex.split(self.get('fs:lustre_setstripe_' + fs_tag, ''))
            # Set stripping if needed
            if lfs_setstripes and getattr(ja, 'mstep_is_first', True):
                # Tweak Lustre striping on the run directory
                logger.info('Setting stripping on < %s >. Parameters: %s',
                            t.rundir, lfs_setstripes)
                t.sh.spawn(['lfs', 'setstripe'] + lfs_setstripes + [t.rundir, ],
                           output=False)


class Belenos(MeteoBullX3):
    """Belenos Supercomputer at Meteo-France."""

    _footprint = dict(
        info = 'Bull Belenos supercomputer at Meteo France',
        attr = dict(
            inetname = dict(
                default = 'belenos',
                values  = ['belenos']
            ),
        ),
        only = dict(
            hostname = footprints.FPRegex(r'belenos(?:login|transfert|nmipt|ndl)?\d+(?:\.|$)')
        )
    )


class Taranis(MeteoBullX3):
    """Taranis Supercomputer at Meteo-France."""

    _footprint = dict(
        info = 'Bull Taranis supercomputer at Meteo France',
        attr = dict(
            inetname = dict(
                default = 'taranis',
                values  = ['taranis']
            ),
        ),
        only = dict(
            hostname = footprints.FPRegex(r'taranis(?:login|transfert|nmipt|ndl)?\d+(?:\.|$)')
        )
    )


# Any kind of DSI's Soprano servers

class MeteoSoprano(Target):
    """A Soprano Server."""

    _abstract = True
    _footprint = dict(
        info = 'A Soprano Server at Meteo France',
        attr = dict(
            sysname = dict(
                values = ['Linux', ]
            ),
        ),
        priority = dict(
            level = footprints.priorities.top.TOOLBOX
        )
    )


class MeteoSopranoDevRH6(MeteoSoprano):
    """A Soprano Development Server running CentOS 6."""

    _footprint = dict(
        info = 'A Soprano Development Server running CentOS 6',
        attr = dict(
            hostname = dict(
                values = (['alose', 'pagre', 'rason', 'orphie', 'guppy'] +
                          ['sotrtm{:d}-sidev'.format(n) for n in range(31, 41)])
            ),
            inifile = dict(
                optional=True,
                default='@target-soprano_dev_rh6.ini',
            ),
        ),
    )

    def generic(self):
        """Generic name to be used in acess paths"""
        return 'soprano_dev_rh6'


# Any kind of CNRM server or workstation

class UmrCnrmTarget(Target):
    """Restrict the FQDN to cnrm.meteo.fr."""

    _abstract = True
    _footprint = dict(
        info='Aneto Cluster at CNRM',
        only = dict(
            fqdn = [footprints.FPRegex(r'.+\.cnrm\.meteo\.fr$'),
                    footprints.FPRegex(r'.+\.umr-cnrm\.fr$')]
        ),
        priority = dict(
            level = footprints.priorities.top.TOOLBOX
        )
    )


class Aneto(UmrCnrmTarget):
    """Aneto cluster at Meteo-France CNRM."""

    _footprint = dict(
        info='Aneto Cluster at CNRM',
        attr=dict(
            inetname=dict(
                default = 'aneto',
                values = ['aneto']
            ),
            inifile=dict(
                default = '@target-[inetname].ini',
            ),
        ),
        only = dict(
            hostname = footprints.FPRegex(r'n[ct]x\d+(?:\.|$)')
        )
    )


class CnrmLinuxWorkstation(UmrCnrmTarget):
    """Aneto cluster at Meteo-France CNRM."""

    _footprint = dict(
        info='Aneto Cluster at CNRM',
        attr=dict(
            sysname = dict(
                values = ['Linux', ]
            ),
            inifile=dict(
                default = '@target-cnrmworkstation.ini',
            ),
        ),
        only = dict(
            hostname = footprints.FPRegex(r'[lp]x\w+(?:\.|$)')
        )
    )

    def cache_storage_alias(self):
        """The tag used when reading Cache Storage configuration files."""
        return 'cnrmworkstation'


class CnrmLinuxServer(UmrCnrmTarget):
    """Aneto cluster at Meteo-France CNRM."""

    _footprint = dict(
        info='Aneto Cluster at CNRM',
        attr=dict(
            sysname = dict(
                values = ['Linux', ]
            ),
            inifile=dict(
                default = '@target-cnrmserver.ini',
            ),
        ),
        only = dict(
            hostname = footprints.FPRegex(r'[scv]x\w+(?:\.|$)')
        )
    )


# Prestaging tools for MF mass storage archives

class HendrixPrestagingTool(PrestagingTool):

    _footprint = dict(
        info = "Process Hendrix's pre-staging requests.",
        attr = dict(
            issuerkind = dict(
                values = ['archivestore', ]
            ),
            storage = dict(
                values = ['hendrix', 'hendrix.meteo.fr'],
                remap = dict(hendrix='hendrix.meteo.fr')
            ),
            scheme = dict(),
            logname=dict(
                optional=True
            ),
            hendrix_stagedir = dict(
                optional = True,
                default = Environment(active=False).get(
                    'vortex_hendrix_stagedir',
                    '/DemandeMig/ChargeEnEspaceRapide',
                ),
            )
        )
    )

    def flush(self, email=None):
        """Actually send the pre-staging request to Hendrix."""
        # Build the target
        request = []
        logger.info('Prestaging to %s: requesting %d items', self.storage, len(self))
        if email is not None:
            logger.info('Prestaging to %s: MAIL directive added (%s).',
                        self.storage, email)
            request.append("#MAIL=" + email)
        request.extend(sorted(self.items()))
        # Send this stuff to hendrix
        request_filename = '.'.join([self.logname or 'unknownuser',
                                     'stagereq',
                                     uuid.uuid4().hex[:16],
                                     'MIG'])
        logger.info('Prestaging to %s: Uploading %s',
                    self.storage, self.system.path.join(self.hendrix_stagedir, request_filename))
        request_data = io.BytesIO()
        request_data.write(('\n'.join(request)).encode(encoding='utf_8'))
        request_data.seek(0)
        try:
            ftp = self.system.ftp(self.storage, logname=self.logname)
        except ftplib.all_errors as e:
            logger.error('Prestaging to %s: unable to connect: %s', self.storage, str(e))
            ftp = None
        if ftp:
            try:
                rc = ftp.cd(self.hendrix_stagedir)
            except ftplib.all_errors as e:
                logger.error('Prestaging to %s: error with "cd": %s', self.storage, str(e))
                rc = False
            if rc:
                try:
                    ftp.put(request_data, request_filename)
                except ftplib.all_errors as e:
                    logger.error('Prestaging to %s: error with "put": %s', self.storage, str(e))
                    rc = False
            ftp.close()
            return rc
        else:
            return False
