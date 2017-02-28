#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

"""
Utility that manages the Uget Hack and Archive Stores.
"""

from __future__ import print_function, absolute_import, division

import cmd
import itertools
import logging
import os
import re
import StringIO
import sys
from tempfile import mkdtemp

# Automatically set the python path
vortexbase = os.path.dirname(os.path.realpath(__file__)).rstrip('/bin')
sys.path.insert(0, os.path.join(vortexbase, 'site'))
sys.path.insert(0, os.path.join(vortexbase, 'src'))

from footprints import proxy as fpx

import vortex
from vortex.tools.net import uriparse

from gco.data.stores import UgetStore
from gco.syntax.stdattrs import uget_sloppy_id_regex, UgetId
from gco.tools import genv, uenv

vortex.logger.setLevel(logging.WARNING)

sh = vortex.ticket().sh
tg = sh.target()


def query_yes_no_quit(question, default="yes"):
    """Ask a yes/no/quit question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no", "quit" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes", "no" or "quit".

    from: http://code.activestate.com/recipes/577097/
    """
    valid = {"yes": "yes", "y": "yes", "ye": "yes",
             "no": "no", "n": "no",
             "quit": "quit", "qui": "quit", "qu": "quit", "q": "quit"}
    if default is None:
        prompt = " [y/n/q] "
    elif default == "yes":
        prompt = " [Y/n/q] "
    elif default == "no":
        prompt = " [y/N/q] "
    elif default == "quit":
        prompt = " [y/n/Q] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while 1:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return default
        elif choice in valid.keys():
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes', 'no' or 'quit'.\n")


class WeakUgetStore(UgetStore):
    """Combined cache and central GCO stores."""

    _footprint = dict(
        info = 'GCO multi access',
        attr = dict(
            netloc = dict(
                values   = ['uget.weak.fr'],
            ),
        )
    )

    def alternates_netloc(self):
        """Tuple of alternates domains names, e.g. ``cache`` and ``archive``."""
        return ('uget.hack.fr', 'uget.archive.fr')


class UGetShell(cmd.Cmd):
    """Accepts commands via the normal interactive prompt or on the command line."""

    _valid_check = re.compile(r'(?P<what>data|env)\s+' + uget_sloppy_id_regex.pattern + '$')
    _valid_pull = _valid_check
    _valid_push = _valid_check
    _valid_hack = re.compile(r'(?P<gco>g)?(?P<what>data|env)\s+' +
                             r'(?P<baseshort>(?P<baseid>\S+)(?(gco)\b|@(?P<baselocation>\w+)))\s+' +
                             r'into\s+' + uget_sloppy_id_regex.pattern + '$')
    _valid_set = re.compile(r'(?P<what>storage)\s+(?P<value>\S+)$')

    _complete_basics = ['env', 'data']
    _complete_basics_plus = _complete_basics + ['genv', 'gdata']

    def __init__(self, *kargs, **kwargs):
        cmd.Cmd.__init__(self, *kargs, **kwargs)
        self._storehack = fpx.store(scheme='uget', netloc='uget.hack.fr')
        self._storehackrw = fpx.store(scheme='uget', netloc='uget.hack.fr', readonly=False)
        self._update_stores()

    def _update_stores(self, **kwargs):
        self._storearch = fpx.store(scheme='uget', netloc='uget.archive.fr', **kwargs)
        self._storeweak = fpx.store(scheme='uget', netloc='uget.weak.fr')

    @staticmethod
    def _valid_syntax(regex, line):
        mline = regex.match(line)
        if not mline:
            print('Syntax error (got < {:s} >)'.format(line))
            return None
        else:
            return mline.groupdict()

    @staticmethod
    def _error(msg):
        print('Error: {!s}'.format(msg))

    @staticmethod
    def _check_remap(rc):
        return 'Ok' if bool(rc) else 'MISSING'

    @property
    def _storelist(self):
        return itertools.izip(('Hack', 'Archive'),
                              (self._storehack, self._storearch))

    def _uri(self, store, path):
        if isinstance(path, (tuple, list)):
            path = '/'.join(path)
        return uriparse('{:s}://{:s}/{:s}'.format(store.scheme, store.netloc, path))

    def do_info(self, line):
        """Print some info on the store being used by uget.py."""
        print('Hack store   : {:s}'.format(self._storehack))
        print('Archive store: {:s}'.format(self._storearch))

    def do_set(self, line):
        """Edit some settings of uget.py."""
        mline = self._valid_syntax(self._valid_set, line)
        if mline:
            if mline['what'] == 'storage':
                self._update_stores(storage=mline['value'])

    def _complete_basics(self, text, line, begidx, endidx, guesses=_complete_basics):
        if not text:
            completions = self._complete_basics[:]
        else:
            completions = [f for f in guesses if f.startswith(text)]
        return completions

    def complete_check(self, text, line, begidx, endidx):
        return self._complete_basics(text, line, begidx, endidx)

    def do_check(self, line):
        """Check the availability of a given item."""
        mline = self._valid_syntax(self._valid_check, line)
        if mline:
            found = False
            print()
            for stname, st in self._storelist:
                uri = self._uri(st, (mline['what'], mline['shortuget']))
                chk = st.check(uri)
                found = found or chk
                print('{:7s}: {:7s} ({:s})'.format(stname, self._check_remap(chk),
                                                   st.locate(uri)))
            if mline['what'] == 'env' and found:
                print()
                print('Digging into this particular Uenv:')
                myenv = uenv.contents('uget:' + mline['shortuget'],
                                      scheme='uget', netloc='uget.weak.fr')
                for k, v in myenv.items():
                    if isinstance(v, UgetId):
                        res = ''
                        for stname, st in zip(('Hack', 'Archive'),
                                              (self._storehack, self._storearch)):
                            if st.check(self._uri(st, ('data', v.short))):
                                res += stname + ', '
                        res = res.rstrip(', ') or 'MISSING'
                    else:
                        res = 'unchecked'
                    print('  {:36s}: {:14s} ({:s})'.format(k, res, v))
                uenv.clearall()
            print()

    def do_pull(self, line):
        """Retrieve a given item.

        While trying to retrieve a cycle, it's downloaded but only displayed.
        """
        mline = self._valid_syntax(self._valid_pull, line)
        if mline:
            # name of the temporary file
            if mline['what'] == 'env':
                tofile = StringIO.StringIO()
            else:
                tofile = mline['id'] + sh.safe_filesuffix()
            # retrieve the resource"
            uri = self._uri(self._storeweak, (mline['what'], mline['shortuget']))
            try:
                rc = self._storeweak.get(uri, tofile)
            except IOError:
                rc = False
            if not rc:
                self._error("Could not get < {:s} >".format(mline['shortuget']))
            else:
                if mline['what'] == 'env':
                    print()
                    tofile.seek(0)
                    for l in tofile:
                        print(l.rstrip('\n'))
                    print()
                else:
                    sh.mv(tofile, mline['id'])

    def _single_push(self, what, shortid):
        """Push a single data to the archive store (request confirmation for overwrite)."""
        source = self._storehack.locate(self._uri(self._storehack, (what, shortid)))
        dest_uri = self._uri(self._storearch, (what, shortid))
        if self._storearch.check(dest_uri):
            res = query_yes_no_quit('< {:s} > already exists in the Archive store. Overwrite ?'.format(shortid),
                                    default='no')
            if res == 'quit':
                return False
            if res == 'no':
                return True
        rc = bool(self._storearch.put(source, dest_uri, dict()))
        if not rc:
            self._error("The file transfer to the archive failed")
        return rc

    def do_push(self, line):
        """Push an element of the Hack store to the archive.

        While trying to upload a cycle, subsequent missing data will be
        downloaded (if needed)
        """
        mline = self._valid_syntax(self._valid_push, line)
        if mline:
            # Basic checks: Does the source exists ?
            source_uri = self._uri(self._storehack, (mline['what'], mline['shortuget']))
            if not self._storehack.check(source_uri):
                self._error('< {:s} > is not available from the Hack store.'.format(mline['shortuget']))
                return
            # Store the requested resource
            rc = self._single_push(mline['what'], mline['shortuget'])
            if rc is not True:
                return rc
            # When dealing with a Uenv, also push the related Uget data
            if mline['what'] == 'env':
                print()
                print('Digging into this particular Uenv:')
                myenv = uenv.contents('uget:' + mline['shortuget'],
                                      scheme='uget', netloc='uget.weak.fr')
                for _, v in myenv.items():
                    if isinstance(v, UgetId):
                        # If the element is a Uget data available in the Hack store: upload it
                        if self._storehack.check(self._uri(self._storehack, ('data', v.short))):
                            print("Uploading: {:s}".format(v))
                            rc = self._single_push('data', v.short)
                            if rc is not True:
                                return rc
                        else:
                            rstuff_uri = self._uri(self._storearch, ('data', v.short))
                            print("{:9s}: {:s}".format(self._check_remap(self._storearch.check(rstuff_uri))), v)
                    else:
                        print("Unchecked: {:s}".format(v))
                uenv.clearall()
                print()

    def do_hack(self, line):
        """Retrieve an element and put it in the Hack store."""
        mline = self._valid_syntax(self._valid_hack, line)
        if mline:
            # Did the target element already exists ?
            dest_uri = self._uri(self._storehack, (mline['what'], mline['shortuget']))
            if self._storehack.check(dest_uri):
                res = query_yes_no_quit('< {:s} > already exists in the Hack store. Overwrite ?'.
                                        format(mline['shortuget']), default='no')
                if res in ('quit', 'no'):
                    return False
            # Ok, let's create a temporary working directory
            tdir = mkdtemp(prefix='uget_at_work')
            tfile = sh.path.join(tdir, 'uget' + sh.safe_filesuffix())
            try:
                # The source is a Uget element
                if mline['gco'] is None:
                    source_uri = self._uri(self._storehack, (mline['what'], mline['baseshort']))
                    try:
                        rc = self._storeweak.get(source_uri, tfile)
                    except IOError:
                        rc = False
                    if not rc:
                        self._error("Could not get < {:s} >".format(mline['baseshort']))
                        return False
                # The source is a GCO element
                else:
                    # The source is a genv cycle
                    if mline['what'] == 'env':
                        mygenv = genv.autofill(mline['baseshort'])
                        if not mygenv:
                            self._error("Could not get genv < {:s} >".format(mline['baseshort']))
                            return False
                        with open(tfile, 'w') as tfilefh:
                            tfilefh.writelines(['{:s}={:s}\n'.format(k, v)
                                                for k, v in mygenv.items() if k not in ('cycle', )])
                    # The source is a gget data
                    else:
                        ghost = tg.get('gco:ggetarchive', 'hendrix.meteo.fr')
                        gtool = sh.path.join(tg.get('gco:ggetpath', ''), tg.get('gco:ggetcmd', 'gget'))
                        with sh.cdcontext(tdir):
                            rc = sh.spawn([gtool, '-host', ghost, mline['baseshort']],
                                          output=False, fatal=False)
                            if not rc:
                                self._error("Could not get gget data < {:s} >".format(mline['baseshort']))
                                return False
                            sh.mv(mline['baseshort'], tfile)
                # That went great ! Store the retrived ressource inthe hack store !
                self._storehackrw.put(tfile, dest_uri, dict())
            finally:
                sh.rmtree(tdir)

    def do_EOF(self, line):
        return True

    do_q = do_quit = do_exit = do_EOF


if __name__ == '__main__':
    if len(sys.argv) > 1:
        UGetShell().onecmd(' '.join(sys.argv[1:]))
    else:
        UGetShell().cmdloop()
