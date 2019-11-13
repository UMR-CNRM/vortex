#!${python}
# -*- coding: utf-8 -*-

import os
actual_mpirankvariable = os.environ['${mpirankvariable}']
rank = os.environ[actual_mpirankvariable]

todolist = {
${todolist}
}

me = todolist[int(rank)]
os.execl(me[0], me[0], *me[1])
