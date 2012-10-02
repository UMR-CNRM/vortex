#!/bin/env python
# -*- coding:Utf-8 -*-

import os, sys, re
import vortex
import common.data, iga.data
from vortex.utilities import dispatch


t = vortex.ticket()
t.warning()


# Assumed that FIFO pipes are created by parent process
fdir = sys.argv[1]
ppid = sys.argv[2]

fifobase = os.path.join(fdir, 'fifo.')
rfifo = fifobase + 'r' + ppid
wfifo = fifobase + 'w' + ppid
pfifo = fifobase + 'p' + ppid

# Pre-compiled items for auto-promotion of booleans values
istrue = re.compile('on|true|ok', re.IGNORECASE)
isfalse = re.compile('off|false|ko', re.IGNORECASE)

# Local store for set variables
sto = dict(fdir=fdir, ppid=ppid, rfifo=rfifo, wfifo=wfifo, last=None)
log = list()
anonymous = 0

# Get a nice default dispatcher
dispatcher = dispatch.Dispatcher()

# Listen until 'exit'
listen = True

while ( listen ):

    # Raw input from FIFO... could be something more sophisticated !
    rp = open(rfifo, 'r')
    cmdline = rp.read()
    rp.close()

    # Assumes that first item is process id
    args = cmdline.split()
    if not args:
        args = [ '-1', os.environ['HOME'] ]
    pid = args.pop(0)
    pwd = args.pop(0)
    os.chdir(pwd)

    # Defines a default action that could be to show the current session id
    if not args:
        args = [ 'default' ]
    cmd = args.pop(0).lower()

    
    if ( cmd == 'exit' ):
        
        # The only magic command is 'exit'
        listen = False
        print 'Vortex Dispatch[{0:s}]: exit'.format(pid)
        (rc, rmsg, results) = ( 0, 'Bye ' + ppid + '...', None )
        log.append((rc, cmd))

    elif ( cmd == 'vars' or cmd == 'sto' ):

        # Display internal storage
        if sto:
            (rc, rmsg, results) = dispatcher.echo(t, sto)
        else:
            (rc, rmsg, results) = (0, 'Internal store is empty', None)
        results = sto['last']
        log.append((rc, cmd))

    elif ( cmd == 'log' ):

        # Display log history
        (rc, rmsg, results) = ( 0, "\n".join(map(lambda x: str(x), log)), sto['last'] )

    elif ( cmd == 'last' ):

        # Display last result
        (rc, rmsg, results) = ( 0, str(sto['last']), sto['last'] )

    elif ( cmd == 'clear' ):

        # Clear data from internal storage
        if args:
            for a in args:
                del sto[a]
            (rc, rmsg, results) = (0, 'Remove from internal store ' + str(args), args)
        else:
            sto = dict(fdir=fdir, ppid=ppid, rfifo=rfifo, wfifo=wfifo, last=None)
            (rc, rmsg, results) = (0, 'Internal store is clear', sto['last'])
        log.append((rc, cmd))

    else:
        
        # Try hard to make a proper dict of the raw arguments
        opts = dict()
        target = None

        for a in args:
        
            # Key = Value pairs are expected
            kv = a.split('=', 1)
            key = kv[0]
            if len(kv) < 2:
                value = None
            else:
                value = kv[1]
            
            # Avoid undefined values
            if value == None:
                if key in sto:
                    value = sto[key]
                else:
                    value = True
            
            # True/False boolean promotion
            if type(value) == str and istrue.match(value):
                value = True
            elif type(value) == str and isfalse.match(value):
                value = False

            # Result from command could be stored or value replaced ?
            if key == 'set':
                target = value
            else:
                if type(value) == str and value in sto:
                    value = sto[value]
                opts[key] = value
            
        # At least... launch the command    
        print 'Vortex Dispatch[{0:s}]: {1:s} {2:s}'.format(pid, cmd, opts)
        realcmd = getattr(dispatcher, cmd, None)
        if realcmd and callable(realcmd):
            try:
                (rc, rmsg, results) = realcmd(t, opts)
            except Exception as e:
                (exc_type, exc_value, exc_traceback) = sys.exc_info()
                errormsg = (
                    'Something bad happened: ' + str(e),
                    str(exc_type),
                    str(exc_traceback)
                )
                (rc, rmsg, results) = ( 1, "\n".join(errormsg), None )
            finally:
                log.append((rc, cmd, opts))
            if target:
                sto[target] = results
        else:
            (rc, rmsg, results) = ( 1, 'Could not find command <' + cmd + '>', None )
            log.append((rc, cmd, opts))

    sto['last'] = results

    # Well... someone is probably waiting on the output pipe !
    wp = open(wfifo, 'w')
    wp.write(rmsg + "\n")
    wp.close()

os.unlink(rfifo)
os.unlink(wfifo)
os.unlink(pfifo)

print t.prompt, 'Duration time =', t.duration()
print t.line
