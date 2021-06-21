# -*- coding: utf-8 -*-

"""
This example shows how to use a hook on a file get.

Ok 20190527 - PL + NM
Ok 20180801 - GR
"""

from __future__ import absolute_import, division, print_function, unicode_literals

# load the packages used in this example
import sys

import common
import footprints as fp
import vortex
from bronx.stdtypes import date
from vortex import toolbox

# prevent IDEs from removing seemingly unused imports
assert any([common, ])

# cleanly mix stdout and stderr
sys.stdout = sys.stderr


# set up the Vortex environment
t = vortex.ticket()
sh = t.sh
e = t.env

# change the working directory
working_directory = sh.path.join(e.HOME, "tmp", "vortex_examples_tmpdir")
sh.cd(working_directory, create=True)

# the date for this experiment
rundate = date.yesterday() + date.Period("PT3H")


# define a function which will print the size of the file
def my_hook(t, rh):
    # This is a very simple example. Of course, one can achieve many things
    # working with **t** (the current session) and **rh** (the "hooked"
    # ResourceHandler object)...
    dname = rh.container.localpath()
    print("The size of the file is: {}".format(t.sh.size(dname)))


# #### 1 - explicitely calling the hook function ###
sh.title('Example #1')

# let rh be the first resource handler returned by rload
members = 16
rh = toolbox.rload(
    # Resource
    kind       = 'mbsample',
    nbsample   = members,
    date       = rundate,
    cutoff     = "production",
    model      = "arome",
    # Provider
    block      = "clustering",
    namespace  = 'vortex.archive.fr',
    experiment = "OPER",
    vapp       = "arome",
    vconf      = "pefrance",
    # Container
    local      = "test1.json"
)[0]

# print some information
print('Complete ?', rh.complete)
print('Location :', rh.location())
print('Locate :  ', rh.locate())
print('IdCard:')
print(rh.idcard())

# get the resource
print('Get ?', rh.get())

# apply the hook defined above
my_hook(t, rh)


# #### 2 - the rload method automatically calls the hook  ###
sh.title('Example #2')

# the same rload call, except for the "hook" part (and the "local" name, obviously)
rh = toolbox.rload(
    # Resource
    kind       = 'mbsample',
    nbsample   = members,
    date       = rundate,
    cutoff     = "production",
    model      = "arome",
    # Provider
    block      = "clustering",
    namespace  = 'vortex.archive.fr',
    experiment = "OPER",
    vapp       = "arome",
    vconf      = "pefrance",
    # Container
    local      = "test2.json",
    # Hooks
    hook_size  = fp.FPTuple([my_hook, ()]),  # No extra arguments provided
)[0]

print('IdCard (with hook):')
print(rh.idcard())

# getting the resource automatically calls the hook
print('Get (with hook) ?', rh.get())


# #### 3 - Simpler syntax using toolbox.input and now = True
sh.title('Example #3')

rh = toolbox.input(
    # Resource
    kind       = 'mbsample',
    nbsample   = members,
    date       = rundate,
    cutoff     = "production",
    model      = "arome",
    # Provider
    block      = "clustering",
    namespace  = 'vortex.archive.fr',
    experiment = "OPER",
    vapp       = "arome",
    vconf      = "pefrance",
    # Container
    local      = "test3.json",
    # Hooks
    hook_size  = (my_hook, ),  # No extra arguments provided
    # Input options
    now        = True,  # The get will be done automatically
    verbose    = True,  # Nice prints...
)[0]
