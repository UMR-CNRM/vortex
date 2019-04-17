#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=unused-argument

from __future__ import print_function, absolute_import, unicode_literals, division

import six

from bronx.fancies import loggers
from bronx.stdtypes import date
import footprints

from vortex.data.stores import Store
from vortex.syntax.stdattrs import compressionpipeline

from common.tools.agt import agt_actual_command

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


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
        """Cannot write to the BDPE (yet ?)."""
        logger.error("A BdpeStore is not able to perform PUTs.")
        return False

    def bdpedelete(self, remote, options):
        """Cannot delete a BDPE product."""
        logger.error("A BdpeStore is not able to perform DELETEs.")
        return False

    def bdpeget(self, remote, local, options):
        """Real extraction from the BDPE database."""

        # Check that local is a file (i.e not a virtual container)
        if not isinstance(local, six.string_types):
            raise TypeError('The BDPE provider can not deal with virtual containers')

        # remote['path'] looks like '/OPER_SEC_True/20151105T0000P/BDPE_42+06:00'
        _, targetmix, str_date, more = remote['path'].split('/')
        p_target, f_target, s_archive = targetmix.split('_')
        productid, str_term = more[5:].split('+')
        args = '{id} {date} {term} {local}'.format(
            id    = productid,
            date  = date.Date(str_date).ymdhms,  # yyyymmddhhmmss
            term  = date.Time(str_term).fmtraw,  # HHHHmm
            local = local,
        )
        extraenv = dict(
            BDPE_CIBLE_PREFEREE=p_target,
            BDPE_CIBLE_INTERDITE=f_target
        )
        if s_archive == 'True':
            extraenv['BDPE_LECTURE_ARCHIVE_AUTORISEE'] = 'oui'
        actual_command = agt_actual_command(self.system, 'agt_lirepe', args, extraenv=extraenv)

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
