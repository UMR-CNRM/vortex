#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A set of AlgoComponents interrogating various databases.
"""

from __future__ import division, print_function, absolute_import


import footprints
from vortex.algo.components import AlgoComponent, Expresso, BlindRun
from vortex.syntax.stdattrs import a_date, a_term
from common.tools.bdap import BDAPrequest_actual_command, BDAPGetError, BDAPRequestConfigurationError
from common.tools.bdm import BDMGetError, BDMRequestConfigurationError, BDMError
from common.data.obs import ObsMapContent

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
        files to be overwritten.
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
            # Launch each input queries in a dedicated file
            # (to check that the files do not overwrite each other)
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


class GetBDMBufr(Expresso):
    """Algo component to get BDM resources considering a BDM query file."""

    _footprint = dict(
        info = 'Algo component to get BDM BUFR.',
        attr = dict(
            kind = dict(
                values = ['get_bdm_bufr'],
            ),
            date = a_date,
            db_file_bdm = dict(
                default = '/usr/local/sopra/neons_db_bdm',
                values = ['/usr/local/sopra/neons_db_bdm',
                          '/usr/local/sopra/neons_db_bdm.archi',
                          '/usr/local/sopra/neons_db_bdm.intgr'],
                optional = True,
            ),
            extra_env_opt = dict(
                values = ['RECHERCHE', 'OPERATIONNEL', 'OPER'],
                default = 'RECHERCHE',
                optional = True,
            ),
            pwd_file = dict(
                default = '/usr/local/sopra/neons_pwd',
                values = ['/usr/local/sopra/neons_pwd'],
                optional = True,
            ),
            shlib_path = dict(
                default = '/usr/local/lib',
                optional = True,
            ),
            interpreter = dict(
                default = 'awk',
                values = ['awk'],
                optional = True,
            ),
            fatal = dict(
                default = False,
                values = [True, False],
                optional = True,
            ),
        )
    )

    def _local_directory(self, query_filename):
        return '_'.join(['BUFR', query_filename, self.date.ymdhms])

    def prepare(self, rh, opts):
        """
        Prepare the launch of the script
        """
        # Do the standard pre-treatment
        super(GetBDMBufr, self).prepare(rh, opts)

        # Some exports to be done
        self.env.setvar('EXTR_ENV', self.extra_env_opt)
        logger.info('Setting environment variable EXTR_ENV = %s', self.extra_env_opt)
        self.env.setvar('DB_FILE_BDM', self.db_file_bdm)
        logger.info('Setting environment variable DB_FILE_BDM = %s', self.db_file_bdm)
        self.env.setvar('PWD_FILE', self.pwd_file)
        logger.info('Setting environment variable PWD_FILE = %s', self.pwd_file)
        self.env.setvar('SHLIB_PATH', ':'.join(['$SHLIB_PATH', self.shlib_path]))
        logger.info('Setting environment variable SHLIB_PATH = %s',
                    ':'.join(['$SHLIB_PATH', self.shlib_path]))
        self.env.setvar('DMT_DATE_PIVOT', self.date.ymdhms)
        logger.info('Setting environment variable DMT_DATE_PIVOT = %s', self.date.ymdhms)

        # Check if query files are present
        input_queries = self.context.sequence.effective_inputs(
            role = 'Query',
            kind = 'bdm_query',
        )
        if len(input_queries)<1:
            logger.exception('No query file found for the BDM extraction. Stop.')
            raise BDMRequestConfigurationError

    def execute_single(self, rh, opts):
        """
        Launch the BDM request(s).
        The results of each request are stored in a directory local_directory to avoid files overwritten by others
        """

        # Look for the input queries
        input_queries = self.context.sequence.effective_inputs(
            role = 'Query',
            kind = 'bdm_query',
        )

        # Initialize some variables
        rc_all = True
        script_abspath = rh.container.abspath
        script_filename = rh.container.filename

        # Loop over the query files
        for input_query in input_queries:
            # Initialize some variables
            query_abspath = input_query.rh.container.abspath
            query_filename = input_query.rh.container.filename
            loc_dir = self._local_directory(query_filename)
            # Launch an execution for each input queries in a dedicated directory
            # (to check that the files do not overwrite one another)
            with self.system.cdcontext(loc_dir, create = True):
                # Make the links needed
                self.system.symlink(query_abspath, query_filename)
                self.system.symlink(script_abspath, script_filename)
                # Cat the query content
                logger.info('The %s directive file contains:', query_filename)
                self.system.cat(query_filename, output = False)
                # Launch the BDM request
                args = [self.interpreter, '-f', script_filename, query_filename]
                args.extend(self.spawn_command_line(rh))
                logger.debug('Run script %s', args)
                rc = self.spawn(args, opts)
                # Delete the links
                self.system.rm(query_filename)
                self.system.rm(script_filename)
                self.system.dir(output = False, fatal = False)

            if not rc:
                logger.error('Problem during the BDM request of %s.',
                                    query_filename)
                if self.fatal == True:
                    raise BDMGetError

            rc_all = rc_all and rc

        if not rc_all:
            logger.error('Problem during the BDM requests.')
            if self.fatal == True:
                raise BDMGetError

        return rc_all

    def postfix(self, rh, opts):
        """Concatenate the batormap from the different tasks and check if there is no duplicated entries."""

        # BATORMAP concatenation
        # Determine the name of the batormap produced by the execution in the different directories
        input_queries = self.context.sequence.effective_inputs(
            role='Query',
            kind='bdm_query',
        )
        local_dir = [self._local_directory(input_query.rh.container.filename)
                    for input_query in input_queries]
        temp_files = []
        for directory in local_dir:
            glob_files = self.system.glob('/'.join([directory, '*batormap*']))
            for element in glob_files:
                temp_files.append(element)
        # Initialize the resulting batormap file
        obsmap_filename = '_'.join(['OBSMAP', self.date.ymdhms])
        content = []
        # Check if a batormap is already present in the directory (from Oulan extract)
        if self.system.path.isfile(obsmap_filename):
            temp_files.append(obsmap_filename)
        # Loop over the directories to concatenate the batormap
        for file in temp_files:
            file_container = footprints.proxy.container(local = file)
            content_tmp = ObsMapContent()
            content_tmp.slurp(file_container, nofilter = True)
            content.append(content_tmp)
        out_content = ObsMapContent()
        out_content.merge(unique = True, *content)
        out_container = footprints.proxy.container(local = obsmap_filename)
        out_content.rewrite(out_container)
        self.system.cat(out_container.filename, output = False)

        # Listing concatenation
        # Initialize the resulting file
        listing_filename = 'OULOUTPUT'
        # Determine the name of the listing files produced by the execution
        listing_files = []
        for directory in local_dir:
            glob_files = self.system.glob('/'.join([directory, listing_filename]))
            for element in glob_files:
                listing_files.append(element)
        # Check if a listing is already present and has to be merged with the other
        if self.system.path.isfile(listing_filename):
            temp_listing = '.'.join([listing_filename, 'tmp'])
            self.system.mv(listing_filename, temp_listing)
            listing_files.append(temp_listing)
        # Concatenate the listings
        self.system.cat(*listing_files, output = listing_filename)

        # Do the standard postfix
        super(GetBDMBufr, self).postfix(rh, opts)


class GetBDMOulan(BlindRun):
    """Algo component to get BDM files using Oulan."""

    _footprint = dict(
        info = "Algo component to get BDM files using Oulan.",
        attr = dict(
            kind = dict(
                values = ['get_bdm_oulan'],
            ),
            date = a_date,
            db_file = dict(
                default = '/usr/local/sopra/neons_db',
                values = ['/usr/local/sopra/neons_db'],
                optional = True,
            ),
            pwd_file = dict(
                default = '/usr/local/sopra/neons_pwd',
                values = ['/usr/local/sopra/neons_pwd'],
                optional = True,
            ),
            fatal = dict(
                default = False,
                values = [True, False],
                optional = True
            ),
        ),
    )

    def _local_directory(self, namelist_filename):
        return '_'.join(['Oulan', namelist_filename, self.date.ymdhms])

    def prepare(self, rh, opts):
        """Prepare the execution of the Oulan extraction binary."""
        # Do the standard pre-treatment
        super(GetBDMOulan, self).prepare(rh, opts)

        # Export additional variables
        self.env.setvar('DB_FILE', self.db_file)
        logger.info('Setting environment variable DB_FILE = %s', self.db_file)
        self.env.setvar('PWD_FILE', self.pwd_file)
        logger.info('Setting environment variable PWD_FILE = %s', self.pwd_file)
        self.env.setvar('DMT_DATE_PIVOT', self.date.ymdhms)
        logger.info('Setting environment variable DMT_DATE_PIVOT = %s', self.date.ymdhms)

        # Check if namelists are present
        input_namelists = self.context.sequence.effective_inputs(
            role = 'NamelistOulan',
            kind = 'namutil',
        )
        if len(input_namelists)<1:
            logger.error('No Oulan namelist found. Stop.')
            raise BDMError

    def execute(self, rh, opts):
        """Run the binary for each namelist."""
        # Look for the input namelists
        input_namelists = self.context.sequence.effective_inputs(
            role = 'NamelistOulan',
            kind = 'namutil',
        )
        # Iitialize some variables
        rc_all = True
        namelist_lc_filename = 'NAMELIST'
        binary_filename = rh.container.filename
        binary_abspath = rh.container.abspath

        # Loop over the input namelists
        for input_namelist in input_namelists:
            namelist_abspath = input_namelist.rh.container.abspath
            namelist_filename = input_namelist.rh.container.filename
            local_directory_name = self._local_directory(namelist_filename)
            # Launch an execution for each input namelist in a dedicated directory
            # (to check that the files do not overwrite one another)
            with self.system.cdcontext(local_directory_name, create=True):
                # Make needed links
                self.system.symlink(namelist_abspath, namelist_lc_filename)
                self.system.cp(binary_abspath, binary_filename)
                # Cat the namelist content
                logger.info('The %s directive file contains:', namelist_lc_filename)
                self.system.cat(namelist_lc_filename, output = False)
                # Launch the Oulan extraction
                args = [self.absexcutable(binary_filename)]
                args.extend(self.spawn_command_line(rh))
                logger.debug('BlindRun executable resource %s', args)
                rc = self.spawn(args, opts)
                # Delete the links
                self.system.rm(namelist_lc_filename)
                self.system.rm(binary_filename)
                self.system.dir(output = False, fatal = False)

            if not rc:
                logger.error('Problem during the Oulan BDM request of %s.',
                                 namelist_filename)
                if self.fatal == True:
                    raise BDMGetError

            rc_all = rc_all and rc

        if not rc_all:
            logger.error('Problem during the Oulan BDM request.')
            if self.fatal == True:
                raise BDMGetError

        return rc_all

    def postfix(self, rh, opts):
        """Concatenate the batormap from the different tasks and check if there is no duplicated entries."""
        # BATORMAP concatenation
        # Determine the name of the batormap produced by the execution in the different directories
        input_namelists = self.context.sequence.effective_inputs(
            role='NamelistOulan',
            kind='namutil',
        )
        local_dir = [self._local_directory(input_namelist.rh.container.filename)
                    for input_namelist in input_namelists]
        temp_files = []
        for directory in local_dir:
            glob_files = self.system.glob('/'.join([directory, '*batormap*']))
            for element in glob_files:
                temp_files.append(element)
        # Initialize the resulting batormap file
        obsmap_file = '_'.join(['OBSMAP', self.date.ymdhms])
        content = []
        # Check if a batormap is already present in the directory (from BUFR extract)
        if self.system.path.isfile(obsmap_file):
            temp_files.append(obsmap_file)
        # Loop over the directories to concatenate the batormap
        for file in temp_files:
            file_container = footprints.proxy.container(local = file)
            content_tmp = ObsMapContent()
            content_tmp.slurp(file_container, nofilter = True)
            content.append(content_tmp)
        out_content = ObsMapContent()
        out_content.merge( unique = True, *content)
        out_container = footprints.proxy.container(local = obsmap_file)
        out_content.rewrite(out_container)
        self.system.cat(out_container.filename, output = False)

        # Listing concatenation
        # Initialize the resulting file
        listing_file = 'OULOUTPUT'
        listing_files = []
        for directory in local_dir:
            glob_files = self.system.glob('/'.join([directory, listing_file]))
            for element in glob_files:
                listing_files.append(element)
        # Check if a listing is already present and has to be merged with the other
        if self.system.path.isfile(listing_file):
            temp_listing = '.'.join([listing_file, 'tmp'])
            self.system.mv(listing_file, temp_listing)
            listing_files.append(temp_listing)
        # Concatenate the listings
        self.system.cat(*listing_files, output = listing_file)

        # Do the standard postfix
        super(GetBDMOulan, self).postfix(rh, opts)
