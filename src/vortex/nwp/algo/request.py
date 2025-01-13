"""
A set of AlgoComponents interrogating various databases.
"""

import copy

from bronx.fancies import loggers
from bronx.stdtypes.date import Time
import footprints

from vortex.algo.components import (
    AlgoComponent,
    AlgoComponentDecoMixin,
    Expresso,
    BlindRun,
)
from vortex.algo.components import algo_component_deco_mixin_autodoc
from vortex.syntax.stdattrs import a_date
from vortex.tools.systems import ExecutionError
from ..tools.bdap import (
    BDAPrequest_actual_command,
    BDAPGetError,
    BDAPRequestConfigurationError,
)
from ..tools.bdmp import BDMPrequest_actual_command, BDMPGetError
from ..tools.bdcp import BDCPrequest_actual_command, BDCPGetError
from ..tools.bdm import BDMGetError, BDMRequestConfigurationError, BDMError
from ..tools.mars import MarsGetError, callMarsExtract, findMarsExtractCommand
from ..data.obs import ObsMapContent

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class GetBDAPResource(AlgoComponent):
    """Algo component to get BDAP resources considering a BDAP query file."""

    _footprint = dict(
        info="Algo component to get BDAP files.",
        attr=dict(
            kind=dict(
                values=["get_bdap"],
            ),
            date=a_date,
            target_bdap=dict(
                default="OPER",
                optional=True,
                values=["OPER", "INTE"],
            ),
            terms=dict(
                info="A forecast term or a list of terms (rangex will be used to expand the string)",
                alias=("term",),
            ),
            command=dict(
                default="dap3",
                optional=True,
                values=["dap3", "dap3_dev"],
            ),
        ),
    )

    def execute_single(self, rh, opts):
        """
        Launch the BDAP request(s).
        The results of each request are stored in a directory local_directory to avoid
        files to be overwritten.
        """

        # Determine the target BDAP
        int_bdap = self.target_bdap == "INTE"

        # Look for the input queries
        input_queries = self.context.sequence.effective_inputs(
            role="Query",
            kind="bdap_query",
        )

        rc_all = True

        for input_query in input_queries:
            for term in [Time(t) for t in footprints.util.rangex(self.terms)]:
                # Launch each input queries in a dedicated file
                # (to check that the files do not overwrite each other)
                query_file = input_query.rh.container.abspath
                local_directory = "_".join(
                    [query_file, self.date.ymdhms, term.fmtraw]
                )

                with self.system.cdcontext(local_directory, create=True):
                    # Determine the command to be launched
                    actual_command = BDAPrequest_actual_command(
                        command=self.command,
                        date=self.date,
                        term=term,
                        query=query_file,
                        int_extraenv=int_bdap,
                    )
                    logger.info(
                        " ".join(["BDAP extract command:", actual_command])
                    )
                    logger.info("The %s directive file contains:", query_file)
                    self.system.cat(query_file, output=False)
                    # Launch the BDAP request
                    rc = self.system.spawn(
                        [
                            actual_command,
                        ],
                        shell=True,
                        output=False,
                        fatal=False,
                    )

                if not rc:
                    logger.exception(
                        "Problem during the BDAP request of %s.", query_file
                    )
                    if self.system.path.isfile("DIAG_BDAP"):
                        raise BDAPRequestConfigurationError
                    else:
                        raise BDAPGetError

                rc_all = rc_all and rc

        if not rc_all:
            logger.exception("Problem during the BDAP request.")

        return rc_all


class GetBDMPResource(AlgoComponent):
    """Algo component to get BDMP resources considering a BDMP query file."""

    _footprint = dict(
        info="Algo component to get BDMP files.",
        attr=dict(
            kind=dict(
                values=["get_bdmp"],
            ),
            target_bdmp=dict(
                default="OPER",
                optional=True,
                values=["OPER", "INTE", "ARCH"],
            ),
            command=dict(
                default="bdmp_lecture",
                optional=True,
                values=["bdmp_lecture", "bdmp_lecture_pg", "bdmp_lecture_ora"],
            ),
        ),
    )

    def execute_single(self, rh, opts):
        """
        Launch the BDMP request(s).
        The results of each request are stored in a directory local_directory to avoid
        files to be overwritten.
        """

        # Look for the input queries
        input_queries = self.context.sequence.effective_inputs(
            role="Query",
            kind="bdmp_query",
        )

        rc_all = True

        for input_query in input_queries:
            # Get information on the query file
            query_file = input_query.rh.container.abspath
            logger.info("The %s directive file contains:", query_file)
            self.system.cat(query_file, output=False)

            # Construct the name of the temporary directory
            local_directory = "_".join([query_file, "extract"])

            # Determine the command to be launched
            actual_command = BDMPrequest_actual_command(
                command=self.command,
                query=query_file,
                target_bdmp=self.target_bdmp,
            )
            logger.info(" ".join(["BDMP extract command:", actual_command]))

            # Launch the BDMP request
            with self.system.cdcontext(local_directory, create=True):
                rc = self.system.spawn(
                    [
                        actual_command,
                    ],
                    shell=True,
                    output=False,
                    fatal=False,
                )

            if not rc:
                logger.exception(
                    "Problem during the BDMP request of %s.", query_file
                )
                raise BDMPGetError

            rc_all = rc_all and rc

        if not rc_all:
            logger.exception("Problem during the BDMP request.")

        return rc_all


class GetBDCPResource(AlgoComponent):
    """Algo component to get BDCP resources considering a BDCP query file."""

    _footprint = dict(
        info="Algo component to get BDCP files.",
        attr=dict(
            kind=dict(
                values=["get_bdcp"],
            ),
            target_bdcp=dict(
                default="OPER",
                optional=True,
                values=["OPER"],
            ),
            command=dict(
                default="extraction_directives",
                optional=True,
                values=["extraction_directives"],
            ),
        ),
    )

    def execute_single(self, rh, opts):
        """
        Launch the BDCP request(s).
        The name of the output and log files are fixed by the AlgoComponent
        according to the attributes of each request.
        """

        # Look for the input queries
        input_queries = self.context.sequence.effective_inputs(
            role="Query",
            kind="bdcp_query",
        )

        rc_all = True

        for input_query in input_queries:
            # Get information on the query file
            query_file = input_query.rh.container.abspath
            logger.info("The %s directive file contains:", query_file)
            self.system.cat(query_file, output=False)

            # Construct the name of the output and log files
            local_directory = "_".join([query_file, "extract"])
            output_file = "extract.out"
            output_log = "extract.out.diag"

            # Determine the command to be launched
            actual_command = BDCPrequest_actual_command(
                command=self.command,
                query_file=query_file,
                output_file=output_file,
            )
            logger.info(" ".join(["BDMP extract command:", actual_command]))

            # Launch the BDCP request
            with self.system.cdcontext(local_directory, create=True):
                rc = self.system.spawn(
                    [
                        actual_command,
                    ],
                    shell=True,
                    output=False,
                    fatal=False,
                )
                # Cat the log file
                logger.info("Content of the log file:")
                self.system.cat(output_log, output=False)

            if not rc:
                logger.exception(
                    "Problem during the BDCP request of %s.", query_file
                )
                raise BDCPGetError

            rc_all = rc_all and rc

        if not rc_all:
            logger.exception("Problem during the BDCP request.")

        return rc_all


@algo_component_deco_mixin_autodoc
class _GetBDMDecoMixin(AlgoComponentDecoMixin):
    """Class variables and methods usefull for BDM extractions."""

    _MIXIN_EXTRA_FOOTPRINTS = [
        footprints.Footprint(
            attr=dict(
                date=a_date,
                pwd_file=dict(
                    default="/usr/local/sopra/neons_pwd",
                    values=["/usr/local/sopra/neons_pwd"],
                    optional=True,
                ),
                fatal=dict(
                    type=bool,
                    default=False,
                    values=[True, False],
                    optional=True,
                ),
                defaut_queryname=dict(
                    default="vortexdefault_query_name",
                    doc_visibility=footprints.doc.visibility.GURU,
                    optional=True,
                ),
            )
        )
    ]

    def _verbose_env_export(self, varname, value):
        self.env.setvar(varname, value)
        logger.info(
            "Setting environment variable %s = %s", varname, str(value)
        )

    def _prepare_commons(self, rh, opts):
        """
        Prepare the launch of the script
        """
        # Some exports to be done
        self._verbose_env_export("PWD_FILE", self.pwd_file)
        self._verbose_env_export("DMT_DATE_PIVOT", self.date.ymdhms)

    _MIXIN_PREPARE_HOOKS = (_prepare_commons,)

    def _spawn_command_options_extend(self, prev):
        prev["query"] = self.defaut_queryname
        return prev

    _MIXIN_CLI_OPTS_EXTEND = (_spawn_command_options_extend,)

    def _execute_commons(self, rh, opts):
        """Launch the BDM request(s).

        The results of each request are stored in a directory local_directory
        to avoid files overwritten by others
        """

        # Look for the input queries
        input_queries = self._get_input_queries()
        # Initialize some variables
        rc_all = True

        # Loop over the query files
        for input_query in input_queries:
            # Find out the temporary directory name
            query_filename = input_query.rh.container.filename
            query_abspath = input_query.rh.container.abspath
            loc_dir = self._local_directory(query_filename)
            # Launch an execution for each input queries in a dedicated directory
            # (to check that the files do not overwrite one another)
            with self.system.cdcontext(loc_dir, create=True):
                # Make the links needed
                self.system.symlink(query_abspath, self.defaut_queryname)
                # Cat the query content
                logger.info("The %s directive file contains:", query_filename)
                self.system.cat(self.defaut_queryname, output=False)
                # Launch the BDM request and catch
                try:
                    super(self.mixin_execute_companion(), self).execute(
                        rh, opts
                    )
                except ExecutionError:
                    rc_all = False
                    logger.error(
                        "Problem during the BDM request of %s.", query_filename
                    )
                    if self.fatal:
                        raise BDMGetError(
                            "Problem during the BDM request of {}.".format(
                                query_filename
                            )
                        )
                # Delete the links
                self.system.rm(self.defaut_queryname)
                self.system.dir(output=False, fatal=False)

        if not rc_all:
            logger.error(
                "At least one of the BDM request failed. Please check the logs above."
            )

    _MIXIN_EXECUTE_OVERWRITE = _execute_commons

    def _postfix_commons(self, rh, opts):
        """Concatenate the batormap from the different tasks and check if there is no duplicated entries."""

        # BATORMAP concatenation
        # Determine the name of the batormap produced by the execution in the different directories
        input_queries = self._get_input_queries()
        local_dir = [
            self._local_directory(input_query.rh.container.filename)
            for input_query in input_queries
        ]
        temp_files = []
        for directory in local_dir:
            glob_files = self.system.glob("/".join([directory, "*batormap*"]))
            for element in glob_files:
                temp_files.append(element)
        # Initialize the resulting batormap file
        obsmap_filename = "_".join(["OBSMAP", self.date.ymdhms])
        content = []
        # Check if a batormap is already present in the directory (from previous extract)
        if self.system.path.isfile(obsmap_filename):
            temp_files.append(obsmap_filename)
        # Loop over the directories to concatenate the batormap
        for a_file in temp_files:
            file_container = footprints.proxy.container(local=a_file)
            content_tmp = ObsMapContent()
            content_tmp.slurp(file_container)
            content.append(content_tmp)
        out_content = ObsMapContent()
        out_content.merge(unique=True, *content)
        out_content.sort()
        out_container = footprints.proxy.container(local=obsmap_filename)
        out_content.rewrite(out_container)
        out_container.close()
        logger.info("Content of the global batormap:")
        self.system.cat(out_container.filename, output=False)

        # Listing concatenation
        # Initialize the resulting file
        listing_filename = "OULOUTPUT"
        # Determine the name of the listing files produced by the execution
        listing_files = []
        for directory in local_dir:
            glob_files = self.system.glob(
                "/".join([directory, listing_filename])
            )
            for element in glob_files:
                listing_files.append(element)
        # Check if a listing is already present and has to be merged with the other
        if self.system.path.isfile(listing_filename):
            temp_listing = ".".join([listing_filename, "tmp"])
            self.system.mv(listing_filename, temp_listing)
            listing_files.append(temp_listing)
        # Concatenate the listings
        self.system.cat(*listing_files, output=listing_filename)

    _MIXIN_POSTFIX_HOOKS = (_postfix_commons,)


class GetBDMBufr(Expresso, _GetBDMDecoMixin):
    """Algo component to get BDM resources considering a BDM query file."""

    _footprint = dict(
        info="Algo component to get BDM BUFR.",
        attr=dict(
            kind=dict(
                values=["get_bdm_bufr"],
            ),
            db_file_bdm=dict(
                default="/usr/local/sopra/neons_db_bdm",
                values=[
                    "/usr/local/sopra/neons_db_bdm",
                    "/usr/local/sopra/neons_db_bdm.archi",
                    "/usr/local/sopra/neons_db_bdm.intgr",
                ],
                optional=True,
            ),
            extra_env_opt=dict(
                values=["RECHERCHE", "OPERATIONNEL", "OPER"],
                default="OPER",
                optional=True,
            ),
            shlib_path=dict(
                default="/usr/local/lib",
                optional=True,
            ),
            interpreter=dict(
                default="awk",
                values=["awk"],
                optional=True,
            ),
        ),
    )

    def _local_directory(self, query_filename):
        return "_".join(["BUFR", query_filename, self.date.ymdhms])

    def _get_input_queries(self):
        """Returns the list of queries to process."""
        return self.context.sequence.effective_inputs(
            role="Query",
            kind="bdm_query",
        )

    def prepare(self, rh, opts):
        """
        Prepare the launch of the script
        """
        # Do the standard pre-treatment
        super().prepare(rh, opts)

        # Some exports to be done
        self._verbose_env_export("EXTR_ENV", self.extra_env_opt)
        self._verbose_env_export("DB_FILE_BDM", self.db_file_bdm)
        self._verbose_env_export(
            "SHLIB_PATH", ":".join(["$SHLIB_PATH", self.shlib_path])
        )

        # Check if query files are present
        input_queries = self._get_input_queries()
        if len(input_queries) < 1:
            logger.exception(
                "No query file found for the BDM extraction. Stop."
            )
            raise BDMRequestConfigurationError(
                "No query file found for the BDM extraction"
            )


class GetBDMOulan(BlindRun, _GetBDMDecoMixin):
    """Algo component to get BDM files using Oulan."""

    _footprint = dict(
        info="Algo component to get BDM files using Oulan.",
        attr=dict(
            kind=dict(
                values=["get_bdm_oulan"],
            ),
            db_file=dict(
                default="/usr/local/sopra/neons_db",
                values=["/usr/local/sopra/neons_db"],
                optional=True,
            ),
            defaut_queryname=dict(
                default="NAMELIST",
            ),
        ),
    )

    def _local_directory(self, query_filename):
        return "_".join(["Oulan", query_filename, self.date.ymdhms])

    def _get_input_queries(self):
        """Returns the list of namelists to process."""
        return self.context.sequence.effective_inputs(
            role="NamelistOulan",
            kind="namutil",
        )

    def prepare(self, rh, opts):
        """Prepare the execution of the Oulan extraction binary."""
        # Do the standard pre-treatment
        super().prepare(rh, opts)

        # Export additional variables
        self._verbose_env_export("DB_FILE", self.db_file)

        # Check if namelists are present
        input_namelists = self._get_input_queries()
        if len(input_namelists) < 1:
            logger.error("No Oulan namelist found. Stop.")
            raise BDMError("No Oulan namelist found.")


class GetMarsResource(AlgoComponent):
    """AlgoComponent to get Mars resources using a Mars query file"""

    _footprint = dict(
        info="AlgoComponent to get a Mars resource",
        attr=dict(
            kind=dict(
                values=[
                    "get_mars",
                ]
            ),
            date=a_date,
            substitutions=dict(
                info="A dictionary of values to be substituted",
                type=footprints.stdtypes.FPDict,
                default=footprints.stdtypes.FPDict(),
                optional=True,
            ),
            command=dict(optional=True),
            fatal=dict(type=bool, default=True, optional=True),
        ),
    )

    def execute(self, rh, opts):
        """
        Launch the Mars request(s).
        The results of each requests are stored in a directory to avoid
        files to be overwritten.
        """
        # Look for input queries
        input_queries = self.context.sequence.effective_inputs(
            role="Query",
            kind="mars_query",
        )
        if len(input_queries) < 1:
            logger.exception(
                "No query file found for the Mars extraction. Stop."
            )
            raise MarsGetError("No query file found for the Mars extraction")

        rc_all = True

        # Find the command to be launched
        actual_command = findMarsExtractCommand(
            sh=self.system, command=self.command
        )

        # Prepare the substitutions' dictionnary
        dictkeyvalue = copy.deepcopy(self.substitutions)
        if self.date is not None:
            dictkeyvalue["YYYYMMDDHH"] = self.date.ymdh
            dictkeyvalue["YYYYMMDD"] = self.date.ymd
            dictkeyvalue["HH"] = self.date.hh

        # For each input query, extract the files
        for input_query in input_queries:
            # Prepare the query file used
            query_content = input_query.rh.contents
            query_content.setitems(dictkeyvalue)
            input_query.rh.save()
            # Launch each input queries in a dedicated file
            # (to check that the files do not overwrite each other)
            query_file_path = input_query.rh.container.abspath
            local_directory = "_".join([query_file_path, self.date.ymdhms])
            logger.info(
                "Here is the content of the query file %s (after substitution):",
                query_file_path,
            )
            self.system.cat(query_file_path, output=False)
            with self.system.cdcontext(local_directory, create=True):
                # Launch the command
                rc = callMarsExtract(
                    sh=self.system,
                    query_file=query_file_path,
                    fatal=self.fatal,
                    command=actual_command,
                )
                if not rc:
                    if self.fatal:
                        logger.error(
                            "Problem during the Mars request of %s",
                            query_file_path,
                        )
                        raise MarsGetError
                    else:
                        logger.warning(
                            "Problem during the Mars request of %s",
                            query_file_path,
                        )
                rc_all = rc_all and rc
