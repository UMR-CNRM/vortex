#!/usr/bin/env python3

"""
Example of BDAP access.

This script can only run on Soprano servers (alose, rason, orphie, pagre).

The environment must be set prior to running this script:
- python3 (3.5 or higher)
- Vortex must be in the path

In Vortex, BDAP extractions are handled by an AlgoComponent wrapping the dap3 utility.
The request (or query) file must be provided.
This script can be used with multiple query files, provided they have different names.
For each query file, each date and each term, the extraction creates a directory for
the extracted files, named `query_date_term` (where query is the local name of the
query file).

Ok 20180801 - GR
"""

# load the packages used in this example
import common
import gco
import vortex
from bronx.stdtypes import date
from vortex import toolbox

# prevent IDEs from removing seemingly unused imports
assert any([common, gco])


# set up the Vortex environment
t = vortex.ticket()
sh = t.sh
e = t.env

# change the working directory
working_directory = sh.path.join(e.HOME, "tmp", "vortex_examples_tmpdir")
sh.cd(working_directory, create=True)

# define the rundate
rundate = date.yesterday()


# #### Get the request file from the Genv

# to use a remote path, comment out this ResourceHandler and uncomment the following one
rh_input_1 = toolbox.input(
    role   = "Query",
    # Resource
    kind   = "bdap_query",
    source = "dir_SST",
    # Provider
    gget   = "extract.stuff.arpege.69.tgz",
    # Container
    format = "ascii",
    local  = "bdapquery.1"
)

# rh_input_1 = toolbox.input(
#     role     = "Query #1",
#     # Resource
#     kind     = "bdap_query",
#     # Provider
#     remote   = "absolute-path-to-the-query-file",
#     tube     = "ftp", # or scp... if required
#     hostname = "hendrix.meteo.fr", # if required
#     # Container
#     format   = "ascii",
#     local    = "bdapquery.1"
# )

for rh in rh_input_1:
    rh.get()

# define and run the BDAP AlgoComponent
# the Component submits to 'dap3' the queries it finds by filtering
# the effective_inputs for role='Query' and kind='bdap_query'.
algo = toolbox.algo(
    command = "dap3",
    date    = rundate,
    engine  = "algo",
    kind    = "get_bdap",
    term    = "0"
)
algo.run()

# archive the extracted elements
rh_output_1 = toolbox.output(
    role       = "Output #1",
    # Resource
    kind       = "observations",
    geometry   = "globalsp2",
    model      = "arpege",
    part       = "sst",
    stage      = "extract",
    date       = rundate,
    cutoff     = "assim",
    # Provider
    block      = "observations",
    vapp       = "arpege",
    vconf      = "4dvarfr",
    experiment = "my_experiment@{}".format(e.USER),
    namespace  = "vortex.archive.fr",
    # Container
    format     = "grib",
    local      = "{query}_{date}_{term}/fic_AUSA".format(
             query = "bdapquery.1",
             date  = rundate.ymdhms,
             term  = date.Time(0).fmtraw
    )
)

for rh in rh_output_1:
    rh.put()
