#!/usr/bin/env python3

"""
This example shows how to use the glob expansion mechanism in Vortex:
- the way it is used in good old shell scripts
- as a way to create vortex objects based on pattern recognition on
  file names (often used to identify models output)

Ok 20190527 - PL
Ok 20180801 - GR
"""

# load the packages used in this example
import pprint

import common
import vortex
from bronx.stdtypes.date import Time
from vortex import toolbox

# prevent IDEs from removing seemingly unused imports
assert any([common, ])

# set up the Vortex environment
t = vortex.ticket()
sh = t.sh
e = t.env

# change the current directory
sh.chdir(e.HOME)

# list all files and directories in the current directory
my_files_1 = sh.glob("*")
print('\nfiles and directories in HOME:')
pprint.pprint(my_files_1)

# list all files with "tmp" in their name
my_files_2 = sh.glob("*tmp*")
print('\nFile and directory names containing "tmp"')
pprint.pprint(my_files_2)

# list the content of the tmp directory, if it exists
my_files_3 = sh.glob("tmp/*")
print('\nfiles and directories in "tmp/"')
pprint.pprint(my_files_3)

# now work in a dedicated directory
working_directory = sh.path.join(e.HOME, "tmp", "vortex_examples_tmpdir")
sh.cd(working_directory, create=True)

# check the directory content and clean all files and subdirectories
print("\nThe current path is now: {}".format(sh.pwd()))
print('Files and directories:')
pprint.pprint(sh.dir())

# create a file
file_name = "my_file"
file_container = toolbox.proxy.container(local=file_name, actualfmt="ascii")
file_container.write("A text file with nearly nothing in it.")
file_container.close()

# duplicate the file under specific names
for i in range(0, 20, 5):
    for j in range(i, 15, 3):
        sh.cp(file_name, ".".join([file_name, str(i), str(Time(j))]))
print("\nThe directory content is now:")
pprint.pprint(sh.dir())

# create vortex resource handlers based on the "local" pattern description
# 'glob:term' and 'glob:num' are defined by what matches the 'local' definition
# and used to define the 'nickname' variable.
print("\nFilenames matching the Regular Expression: " + r"my_file.\d+.\d+:\d+")
rh_list1 = toolbox.rload(
    # Resource
    unknown    = True,
    nickname   = ["[glob:term]_[glob:num]"],
    # Container
    local      = r"my_file.{glob:num:\d+}.{glob:term:\d+:\d+}",
    # Provider
    block      = "my_block",
    namespace  = "vortex.cache.fr",
    experiment = "my_experiment@{}".format(e.USER),
    vapp       = "my_vapp",
    vconf      = "my_vconf"
)
for rh in rh_list1:
    print(" -> ".join([rh.container.filename, rh.resource.nickname]))

# try to match the same files differently
print("\nFilenames matching the Regular Expression: " + r"my_file.\d.\d+:\d+")
rh_list2 = toolbox.rload(
    # Resource
    unknown    = True,
    nickname   = ["[glob:term]_[glob:num]"],
    # Container
    local      = r"my_file.{glob:num:\d}.{glob:term:\d+:\d+}",
    # Provider
    block      = "my_block",
    namespace  = "vortex.cache.fr",
    experiment = "my_experiment@{}".format(e.USER),
    vapp       = "my_vapp",
    vconf      = "my_vconf"
)
for rh in rh_list2:
    print(" -> ".join([rh.container.filename, rh.resource.nickname]))

# tidy up: remove the working directory
pprint.pprint(sh.dir())
sh.rmall(working_directory)
