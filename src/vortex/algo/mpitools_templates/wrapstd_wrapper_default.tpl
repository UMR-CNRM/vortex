#!${python}

import os
import sys

rank = os.environ['${mpirankvariable}']

# Redirect stdout and stderr in a very very crude manner
if int(rank) > 0:
    stdout_fno = sys.stdout.fileno()
    stderr_fno = sys.stderr.fileno()
    red_outputs = os.open('vwrap_stdeo.{:06d}'.format(int(rank)),
                          os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    os.dup2(red_outputs, stdout_fno)
    os.dup2(red_outputs, stderr_fno)
    os.close(red_outputs) 

os.execl(sys.argv[1], *sys.argv[1:])
