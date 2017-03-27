#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A set of AlgoComponents interrogating various databases.
"""

from __future__ import division, print_function, absolute_import


import footprints
from vortex.algo.components import AlgoComponent
from vortex.syntax.stdattrs import a_date, a_term
from common.tools.bdap import BDAPrequest_actual_command, BDAPGetError, BDAPRequestConfigurationError

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


class GetBDAPResource(AlgoComponent):
    """Algo component to get BDAP resources considering a BDAP query file."""

    _footprint = dict(
        info = 'Algo component to get BDAP files.',
        attr = dict(
            kind = dict(
                values = ['get_bdap'],
            ),
            date = a_date,
            target_bdap = dict(
                default = 'OPER',
                optional = True,
                values = ['OPER', 'INTE'],
            ),
            term = a_term,
            command = dict(
                default = 'dap3',
                optional =True,
                values = ['dap3', 'dap3_dev'],
            ),
        )
    )

    def execute_single(self, rh, opts):
        """
        Launch the BDAP request(s).
        The results of each request are stored in a directory local_directory to avoid
        """

        # Determine the target BDAP
        int_bdap = self.target_bdap == 'INTE'

        # Look for the input queries
        input_queries = self.context.sequence.effective_inputs(
            role = 'Query',
            kind = 'bdap_query',
        )

        rc_all = True

        for input_query in input_queries:
            # Launch each input queries in a dedicated file (to check that the files do not overwrite each other)
            query_file = input_query.rh.container.abspath
            local_directory = '_'.join([query_file, self.date.ymdhms, self.term.fmtraw])

            with self.system.cdcontext(local_directory, create=True):
                # Determine the command to be launched
                actual_command = BDAPrequest_actual_command(command = self.command,
                                                            date = self.date,
                                                            term = self.term,
                                                            query = query_file,
                                                            int_extraenv = int_bdap)
                logger.info(' '.join(['BDAP extract command:', actual_command]))
                logger.info('The %s directive file contains:', query_file)
                self.system.cat(query_file, output=False)
                # Launch the BDAP request
                rc = self.system.spawn([actual_command, ], shell = True, output = False, fatal = False)

            if not rc:
                logger.exception('Problem during the BDAP request of %s.', query_file)
                if self.system.path.isfile('DIAG_BDAP'):
                    raise BDAPRequestConfigurationError
                else:
                    raise BDAPGetError

            rc_all = rc_all and rc

        if not rc_all:
            logger.exception('Problem during the BDAP request.')

        return rc_all
