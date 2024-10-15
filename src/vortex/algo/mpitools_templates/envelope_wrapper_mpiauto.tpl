#!${python}

import os
import sys

sys.path.append('${sitepath}')

actual_mpirankvariable = os.environ['${mpirankvariable}']
rank = os.environ[actual_mpirankvariable]

todolist = {
${todolist}
}

bindinglist = {
${bindinglist}
}

if bindinglist:
    from bronx.system.cpus import set_affinity
    set_affinity(bindinglist[int(rank)])
    # Also bind threads
    os.environ['OMP_PROC_BIND'] = 'true'

me = todolist[int(rank)]
if me[2]:
    os.environ['OMP_NUM_THREADS'] = str(me[2])

os.execl(me[0], me[0], *me[1])
