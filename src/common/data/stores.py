#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=unused-argument

from __future__ import print_function, absolute_import

import footprints

from vortex.data.stores import Store, MultiStore, CacheStore
from vortex.syntax.stdattrs import compressionpipeline
from vortex.tools import date

from common.tools.agt import agt_actual_command
from vortex.syntax.stdattrs import Namespace
from vortex.tools.actions import actiond as ad
import vortex
from vortex.tools.net import Ssh

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


class BdpeStore(Store):
    """Access items stored in the BDPE database (get only)."""

    _footprint = [
        compressionpipeline,
        dict(
            info = 'Access the BDPE database',
            attr = dict(
                scheme = dict(
                    values   = ['bdpe'],
                ),
                netloc = dict(
                    values   = ['bdpe.archive.fr'],
                ),
            ),
            priority = dict(
                level = footprints.priorities.top.DEFAULT
            ),
        ),
    ]

    @property
    def realkind(self):
        return 'bdpe'

    def bdpelocate(self, remote, options):
        """Reasonably close to whatever 'remote location' could mean.
           e.g.: bdpe://bdpe.archive.fr/EXPE/date/BDPE_num+term
        """
        return self.scheme + '://' + self.netloc + remote['path']

    def bdpecheck(self, remote, options):
        """Cannot check a BDPE call a priori."""
        logger.warning("A BdpeStore is not able to perform CHECKs.")
        return False

    def bdpeput(self, local, remote, options):
        """Cannot wrte to the BDPE (yet ?)."""
        logger.error("A BdpeStore is not able to perform PUTs.")
        return False

    def bdpedelete(self, remote, options):
        """Cannot delete a BDPE product."""
        logger.error("A BdpeStore is not able to perform DELETEs.")
        return False

    def bdpeget(self, remote, local, options):
        """Real extraction from the BDPE database."""

        # Check that local is a file (i.e not a virtual container)
        if not isinstance(local, basestring):
            raise TypeError('The BDPE provider can not deal with virtual containers')

        # remote['path'] looks like '/86GV/20151105T0000P/BDPE_42+06:00'
        _, targetmix, str_date, more = remote['path'].split('/')
        p_target, f_target = targetmix.split('no')
        productid, str_term = more[5:].split('+')
        args = '{id} {date} {term} {local}'.format(
            id    = productid,
            date  = date.Date(str_date).ymdhms,  # yyyymmddhhmmss
            term  = date.Time(str_term).fmtraw,  # HHHHmm
            local = local,
        )
        actual_command = agt_actual_command(self.system, 'agt_lirepe', args,
                                            extraenv=dict(BDPE_CIBLE_PREFEREE=p_target,
                                                          BDPE_CIBLE_INTERDITE=f_target))

        logger.debug('lirepe_cmd: %s', actual_command)

        rc = self.system.spawn([actual_command, ], shell=True, output=False, fatal=False)
        rc = rc and self.system.path.exists(local)

        diagfile = local + '.diag'
        if not rc:
            logger.warning('Something went wrong with the following command: %s',
                           actual_command)
            if self.system.path.exists(diagfile):
                logger.warning('The %s file is:', diagfile)
                self.system.cat(diagfile)
        elif self._actual_cpipeline:
            # Deal with compressed files in the BDPE using the optional attribute
            # store_compressed of the BDPE store.
            tempfile = local + self._actual_cpipeline.suffix
            rc = rc and self.system.mv(local, tempfile)
            self._actual_cpipeline.file2uncompress(tempfile, local)
            rc = rc and self.system.path.exists(local)
            if not rc:
                logger.warning('Something went wrong while uncompressing the file %s.', tempfile)

        if self.system.path.exists(diagfile):
            self.system.remove(diagfile)

        return rc


class BdapArchiveStore(Store):
    """Access items stored in the BDAP database (get only)."""

    _footprint = dict(
        info = 'Access the BDAP database',
        attr = dict(
            scheme = dict(
                values   = ['bdap'],
            ),
            netloc = dict(
                values   = ['bdap.archive.fr'],
            ),
            storehost = dict(
                type     = Namespace,
                optional = True,
                default   = 'pagre.meteo.fr',
            ),
            storepath = dict(
                type     = str,
                optional = True,
                default   = 'tmp',
            ),
        ),
    )

    @property
    def realkind(self):
        return 'bdap'

    def bdaplocate(self, remote, options):
        """Reasonably close to whatever 'remote location' could mean.
           e.g.: bdap://bdap.archive.fr/xxx
        """
        return self.scheme + '://' + self.netloc + remote['path']

    def bdapcheck(self, remote, options):
        """Cannot check a BDAP call a priori."""
        logger.warning("A BdapStore is not able to perform CHECKs.")
        return False

    def bdapput(self, local, remote, options):
        """Cannot write to the BDAP."""
        logger.error("A BdapStore is not able to perform PUTs.")
        return False

    def bdapdelete(self, remote, options):
        """Cannot delete a BDAP product."""
        logger.error("A BdapStore is not able to perform DELETEs.")
        return False

    def bdapget(self, remote, local, options):
        """Real extraction from the BDAP database."""

        # Check that local is a file (i.e not a virtual container)
        if not isinstance(local, basestring):
            raise TypeError('The BDAP provider can not deal with virtual containers')

        providopts = options['rhandler']['provider']
        # remote['path'] looks like '/vapp/vconf/oper/date/mb[member]/GRID_[geometry]+[term]'
        _, vapp, vconf, suite, str_date, str_mb, more = remote['path'].split('/')
        geomarea, str_term = more[5:].split('+')
        member = str_mb[2:] if str_mb else ''
        date_pivot  = date.Date(str_date).ymdhms
        term = date.Time(str_term).hour
        cutoff = str_date[-1] if str_date[-1] != 'P' else ''

        bdap_v = {'arpege': {'france': 'PA', 'pearp': 'PEARP'}}  # , 'eps': 'PEPS'
        bdap_suite = {'double': 'D', 'test': 'T'}

        request = '#RQST'
        request += '#NFIC {}'.format(local)
        request += '#MOD ' + bdap_v[vapp][vconf] + cutoff + bdap_suite.get(suite, '') + member
        request += '#PARAM {}'.format(','.join(providopts['quantity']))
        request += '#Z_REF {}'.format(geomarea)
        request += '#L_TYP {}'.format(providopts['level_kind'].upper())
        request += '#L_LST {}'.format(str(providopts['level'])[1:-1])
        request += '#FORM BINAIRE'

        filereq = 'filereq'
        ssh = vortex.sessions.current().system.ssh(vortex.sessions.current().system, self.storehost)
        ssh.remove(self.storepath + '/' + filereq)
#         self.system.spawn(['ssh', 'rm', self.storehost, self.storepath + '/' + filereq], fatal = False, silent = True)

        cmds = ['cd ' + self.storepath]
        cmds += ['echo "' + request + '" > ' + filereq]
        cmds += ['export DMT_DATE_PIVOT=' + date_pivot]
        cmds += ['dap3_dev {} {}'.format(term, filereq)]

        actual_command = ';'.join(cmds)
        logger.debug('dap_cmd: {}'.format(actual_command))

        try:
            ssh.execute(actual_command)
            ssh.scpget(self.storepath + '/' + local, '.')
            ssh.remove(self.storepath + '/' + filereq)
            ssh.remove(self.storepath + '/' + local)
            #self.system.spawn(['scp'] + [self.storehost + ':' + self.storepath + '/' + local] + ['.'], shell = False, output = True)
#             ad.ssh('rm ' + self.storepath + '/' + filereq, hostname = self.storehost)
#             ad.ssh('rm ' + self.storepath + '/' + local, hostname = self.storehost)
            rc = True
        except RuntimeError:
            rc = False
            logger.critical('Something went wrong with the following command: {}'.format(actual_command))
        return rc
