#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

"""
This script can only run on Soprano servers (alose, rason, orphie, pagre).

The environment must be set before the launch:
- python2 (2.7 or higher)
- Vortex must be in the path
The following lines can be used to do so in the .bash_profile:
export PATH=/opt/rh/python27/root/usr/bin:$PATH
export LD_LIBRARY_PATH=/opt/rh/python27/root/usr/lib64:$LD_LIBRARY_PATH
export MTOOLDIR=$HOME
vortexpath="/soprano/home/marp999/vortex/vortex-olive"
export PYTHONPATH=$PYTHONPATH:$vortexpath/site:$vortexpath/src:$vortexpath/project

This script aims at doing a BDAP extract.
In Vortex, it is done using an AlgoComponent which uses dap3.
The request file must be provided.
This script can be used with multiple query files, provided they
do not have the same local name.
For each query file, each date and each term, the extraction creates
a directory named query_date_term (where query is the local name of
the query file), to receive all the extracted files.

Ok 20180801 - GR
"""

from __future__ import print_function, division, unicode_literals, absolute_import


# Load useful packages for the examples
import common
import gco
import vortex
from bronx.stdtypes import date
from vortex import toolbox

# prevent IDEs from removing seemingly unused imports
assert any([common, gco])


# #### Initializations

# Initialize environment for examples
t = vortex.ticket()
sh = t.sh
e = t.env

# Change the work directory
workdirectory = '/'.join([e.HOME, "tmp", "Vortex"])
if not sh.path.isdir(workdirectory):
    sh.mkdir(workdirectory)
sh.chdir(workdirectory)

# Define the rundate
rundate = date.yesterday()


# #### Get the request file from the Genv

# To use a remote path, replace this first ResourceHandler
# by the next one (which is at present commented)
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

# Define and run the BDAP AlgoComponent
algo = toolbox.algo(
    command = "dap3",
    date = rundate,
    engine = "algo",
    kind = "get_bdap",
    term = "0"
)
algo.run()

# Archive the different elements
rh_output_1 = toolbox.output(
    role = "Output #1",
    # Resource
    kind = "observations",
    geometry = "globalsp2",
    model = "arpege",
    part = "sst",
    stage = "extract",
    date=rundate,
    cutoff="assim",
    # Provider
    block = "observations",
    vapp = "arpege",
    vconf = "4dvarfr",
    experiment = "my_experiment@{}".format(e.USER),
    namespace = "vortex.archive.fr",
    # Container
    format = "grib",
    local = "{query}_{date}_{term}/fic_AUSA".format(
        query="bdapquery.1",
        date=rundate.ymdhms,
        term=date.Time(0).fmtraw
    )
)
for rh in rh_output_1:
    rh.put()
