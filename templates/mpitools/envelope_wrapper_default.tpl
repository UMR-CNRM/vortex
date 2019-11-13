#!${python}
# -*- coding: utf-8 -*-

import os
rank = os.environ['${mpirankvariable}']

todolist = {
${todolist}
}

me = todolist[int(rank)]
os.execl(me[0], me[0], *me[1])
