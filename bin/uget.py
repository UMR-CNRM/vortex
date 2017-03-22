#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

"""
Utility that manages the Uget Hack and Archive Stores.
"""

from __future__ import print_function, absolute_import, division

import cmd
import ConfigParser
import itertools
import logging
import os
import re
import stat
import StringIO
import sys
from tempfile import mkdtemp

# Automatically set the python path
vortexbase = re.sub(os.path.sep + 'bin$', '',
                    os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(vortexbase, 'site'))
sys.path.insert(0, os.path.join(vortexbase, 'src'))

from footprints import proxy as fpx

import vortex
from vortex.tools.net import uriparse

from gco.data.stores import UgetStore
from gco.syntax.stdattrs import UgetId
from gco.tools import genv, uenv

vortex.logger.setLevel(logging.WARNING)

sh = vortex.ticket().sh
gl = vortex.ticket().glove
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


# A decorator that fills the method documentation with the standard UgetId
# description
def ugetid_doc(func):
    """The 'UgetId' identifies a Uget element. Its formed of an *element_name* and
          of a *location* : it looks like 'element_name@location'. The @location part
          may be omitted. In such a case the default_location is used (see the
          'set' and 'info' commands)."""
    func.__doc__ = re.sub(r'\bUGETID_DOC\b', ugetid_doc.__doc__, func.__doc__)
    return func


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

    _valid_partial_ugetid = r'(?P<shortuget>(?P<id>\S+?)(?:@(?P<location>\w+))?\b)'
    _valid_check = re.compile(r'(?P<what>data|env)\s+' + _valid_partial_ugetid + '$')
    _valid_pull = _valid_check
    _valid_push = _valid_check
    _valid_hack = re.compile(r'(?P<gco>g)?(?P<what>data|env)\s+' +
                             r'(?P<baseshort>(?P<baseid>\S+?)(?(gco)\b|(?:@(?P<baselocation>\w+))?\b))\s+' +
                             r'into\s+' + _valid_partial_ugetid + '$')
    _valid_set = re.compile(r'(?P<what>storage|location)\s+(?P<value>\S+)$')
    _valid_bootstraphack = re.compile(r'(?P<location>\w+)')

    _config_file = sh.path.join(gl.configrc, 'uget-client-defaults.ini')

    _complete_basics = ['env', 'data']
    _complete_basics_plus = _complete_basics + ['genv', 'gdata']

    def __init__(self, *kargs, **kwargs):
        cmd.Cmd.__init__(self, *kargs, **kwargs)
        self._config = ConfigParser.SafeConfigParser()
        # Read the configuration
        if sh.path.exists(self._config_file):
            with open(self._config_file) as fhconf:
                self._config.readfp(fhconf)
        else:
            # Or create a void one...
            self._config.add_section('cli')
            self._cliconfig_set('storage', None)
            self._cliconfig_set('location', None)
        # Initiaalise the stores
        self._storehack = fpx.store(scheme='uget', netloc='uget.hack.fr')
        self._storehackrw = fpx.store(scheme='uget', netloc='uget.hack.fr', readonly=False)
        self._update_stores(storage=self._cliconfig_get('storage'))

    def _cliconfig_get(self, key):
        """Get a variable from the configuration file."""
        value = self._config.get('cli', key)
        return None if value == 'None' else value  # None string are converted to None objects

    def _cliconfig_set(self, key, value):
        """Set a variable in the configuration file."""
        value = 'None' if value is None else value  # None string are converted to None objects
        return self._config.set('cli', key, value)

    def _update_stores(self, **kwargs):
        """Re-create the archive stores (using the **kwargs** options)."""
        self._storearch = fpx.store(scheme='uget', netloc='uget.archive.fr', **kwargs)
        self._storearchrw = fpx.store(scheme='uget', netloc='uget.archive.fr',
                                      readonly=False, **kwargs)
        self._storeweak = fpx.store(scheme='uget', netloc='uget.weak.fr', **kwargs)

    def _valid_syntax(self, regex, line):
        """Check that the user input matches **regex**.

        If not, an error message is issued and the help is displayed.
        Upon success, the default location is dealt with here and the named
        matching groups are returned as a dictionary.
        """
        mline = regex.match(line)
        if not mline:
            # We are in trouble !
            print('Syntax error (got < {:s} >)'.format(self.lastcmd))
            print()
            print('"{:s}" command help:'.format(self.lastcmd.split()[0]))
            self.onecmd('help {:s}'.format(self.lastcmd.split()[0]))
            print()
            return None
        else:
            gdict = mline.groupdict()
            # If a location is requested, deal with it
            for shortid, l_id, loc in zip(('shortuget', 'baseshort'),
                                          ('id', 'baseid'), ('location', 'baselocation')):
                if loc in gdict and gdict[loc] is None:
                    gdict[loc] = self._cliconfig_get('location')
                    if loc is None:
                        print('Syntax error (got < {:s} >) but location is not set'
                              .format(self.lastcmd, line))
                        print()
                        return None
                    gdict[shortid] = '{:s}@{:s}'.format(gdict[l_id], gdict[loc])
            return gdict

    @staticmethod
    def _error(msg):
        """Print out an error message."""
        print('Error: {!s}'.format(msg))
        print()

    @staticmethod
    def _check_remap(rc):
        """Converts a return code to a string."""
        return 'Ok' if bool(rc) else 'MISSING'

    @property
    def _storelist(self):
        """Iterate over the hack and archive stores."""
        return itertools.izip(('Hack', 'Archive'),
                              (self._storehack, self._storearch))

    def _uri(self, store, path):
        """Build up an URI given the store object and the path."""
        if isinstance(path, (tuple, list)):
            path = '/'.join(path)
        return uriparse('{:s}://{:s}/{:s}'.format(store.scheme, store.netloc, path))

    def cmdloop(self, intro=None):
        """Catch Ctrl-C."""
        going_on = True
        while going_on:
            try:
                cmd.Cmd.cmdloop(self, intro=intro)
                going_on = False
            except KeyboardInterrupt:
                print(' [Ctrl-C was caught...]')

    def precmd(self, line):
        """Add a blank line before doing anything."""
        print()
        return cmd.Cmd.precmd(self, line)

    def do_info(self, line):
        """
        Print some info on the uget.py command-line interface.

        The default location is used if no location is specified in a UgetId
        (i.e. an UgetID looks like: element_name@location. If @location is
        omitted, the default one is used).
        """
        print('Default location: {!s}'.format(self._cliconfig_get('location')))
        print('Hack store      : {:s}'.format(self._storehack))
        print('Archive store   : {:s}'.format(self._storearch))
        print()

    def _complete_basics(self, text, line, begidx, endidx, guesses=_complete_basics):
        """Deals with auto-completion for the first level of keywords."""
        sline = line.split()
        if len(sline) == 1 or (len(sline) == 2 and sline[1] not in guesses):
            completions = guesses
        else:
            completions = []
        return [f for f in completions if not text or f.startswith(text)]

    def complete_set(self, text, line, begidx, endidx):
        """Auto-completion for the *set* command."""
        return self._complete_basics(text, line, begidx, endidx,
                                     guesses=('storage', 'location'))

    def do_set(self, line):
        """
        Edit the settings of the uget.py command-line interface.

        Syntax: set [storage|location] somevalue

        * somevalue may be 'None'
        * 'set storage' refers to the hostname where the Uget archive is located
          (if None, the Vortex default is used)
        * 'set location' refers to the default location for any UgetID. (i.e.
          an UgetID looks like 'element_name@location'. If @location is omitted,
          the default one is used).

        Note: The uget.py settings are persistent from one session to another
        (they are stored on disk in a configuration file).
        """
        mline = self._valid_syntax(self._valid_set, line)
        if mline:
            if mline['what'] == 'storage':
                self._cliconfig_set('storage', mline['value'])
                self._update_stores(storage=self._cliconfig_get('storage'))
            elif mline['what'] == 'location':
                self._cliconfig_set('location', mline['value'])
            with open(self._config_file, 'w') as fpconf:
                self._config.write(fpconf)

    def complete_check(self, text, line, begidx, endidx):
        """Auto-completion for the *check* command."""
        return self._complete_basics(text, line, begidx, endidx)

    @ugetid_doc
    def do_check(self, line):
        """
        Check the availability of a given Uget element.

        Syntax: check [data|env] UgetId

        * 'check data' will look for constant data described by UgetId
        * 'check env' will look for an environment file (also refered as Uenv)
          such an environment file contains a mapping between keys and constant
          data
        * UGETID_DOC
        * The check is perfomed both in the Hack store and in the Archive store
        * When looking for an environment file, all of the Uget elements listed
          in the environment file are also checked for.
        """
        mline = self._valid_syntax(self._valid_check, line)
        if mline:
            found = False
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
                        for stname, st in self._storelist:
                            if st.check(self._uri(st, ('data', v.short))):
                                res += stname + ', '
                        res = res.rstrip(', ') or 'MISSING'
                    else:
                        res = 'unchecked'
                    print('  {:36s}: {:14s} ({:s})'.format(k, res, v))
                uenv.clearall()
            print()

    def complete_pull(self, text, line, begidx, endidx):
        """Auto-completion for the *pull* command."""
        return self._complete_basics(text, line, begidx, endidx)

    @ugetid_doc
    def do_pull(self, line):
        """
        Retrieve an Uget element.

        Syntax: pull [data|env] UgetId

        * 'pull data' will retrieve the constant data described by UgetId. (it
          will be retrieved as a local file named after the 'element_name' part
          of the UgetId).
        * 'pull env' will retrieve the environment file (also refered as Uenv)
          described by UgetId. The contained of the environment file will be
          displayed on the screen but no local file is created.
        * UGETID_DOC
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

    def complete_push(self, text, line, begidx, endidx):
        """Auto-completion for the *push* command."""
        return self._complete_basics(text, line, begidx, endidx)

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
        rc = bool(self._storearchrw.put(source, dest_uri, dict()))
        if not rc:
            self._error("The file transfer to the archive failed")
        return rc

    @ugetid_doc
    def do_push(self, line):
        """
        Push an element from the Hack store to the archive store.

        Syntax: push [data|env] UgetId

        * 'push data' will push the constant data described by UgetId.
        * 'push env' will push the environment file (also refered as Uenv)
          described by UgetId.
        * UGETID_DOC

        While uploading an environement file, its content will be scanned and
        new UgetId will also be uploaded.
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
                            print("{:9s}: {:s}".format(self._check_remap(self._storearch.check(rstuff_uri)), v))
                    else:
                        print("Unchecked: {:s}".format(v))
                uenv.clearall()
                print()

    def complete_hack(self, text, line, begidx, endidx):
        """Auto-completion for the *hack* command."""
        sline = line.split()
        # First keyword
        if len(sline) == 1 or (len(sline) == 2 and line[1] not in self._complete_basics_plus):
            completions = self._complete_basics_plus
        # Third keyword
        elif (sline[1] in self._complete_basics_plus and
              (len(sline) == 3 or (len(sline) == 4 and sline[3] != 'into'))):
            completions = ('into', )
        else:
            completions = ()
        return [f for f in completions if not text or f.startswith(text)]

    @ugetid_doc
    def do_hack(self, line):
        """
        Retrieve an element and place it in the Hack store.

        Syntax: hack [data|env|gdata|genv] SourceId into UgetId

        * The kacked element may originate from different sources:
          * hack data: A Uget element is looked for (in such a case,
            'SourceId' must be a valid UgetId)
          * hack env: A Uget environment file is looked for (in such
            a case, 'SourceId' must be a valid UgetId)
          * hack gdata: A Gget element is looked for (in such a case
            'SourceId' must be a valid gget identifier).
          * hack genv: A genv cycle is looked for (in such a case
            'SourceId' must be a valid genv identifier).
        * Once the source element is retrieved, it is saved to the Hack
          store using the UgetId identifier
        * UGETID_DOC

        Note: In order for hack gdata/genv to work properly, the gget and genv
        commands must be properly configured on your system.
        """
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
                    source_uri = self._uri(self._storeweak, (mline['what'], mline['baseshort']))
                    if mline['shortuget'] == mline['baseshort']:
                        self._error('The SourceId and destination Uget cannot be the same.')
                        return False
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
                # Give write permissions to the user (that's kind of dirty for a cache but that's hacking !)
                dest_loc = self._storehack.locate(dest_uri)
                st = sh.stat(dest_loc).st_mode
                sh.chmod(dest_loc, st | stat.S_IWUSR)
            finally:
                sh.rmtree(tdir)

    def do_clean_hack(self, line):
        """
        Remove all the element of the Hack store that are available in the Archive store.
        """
        to_delete = list()
        s_uris = [f.lstrip('/').split('/') for f in self._storehack.cache.catalog()]
        h_uris = [self._uri(self._storehack, (f[1], '{:s}@{:s}'.format(f[2], f[0])))
                  for f in s_uris]
        a_uris = [self._uri(self._storearch, (f[1], '{:s}@{:s}'.format(f[2], f[0])))
                  for f in s_uris]
        for h_uri, a_uri in zip(h_uris, a_uris):
            if self._storearch.check(a_uri, dict()):
                to_delete.append(h_uri)
        to_delete.sort()
        print('The following elements will be deleted:')
        for h_uri in to_delete:
            print('  {:s}'.format(h_uri['path']))
        res = query_yes_no_quit('Please, confirm...', default='no')
        if res in ('quit', 'no'):
            print('aborting...')
            return False
        for h_uri in to_delete:
            self._storehackrw.delete(h_uri, dict())

    def do_bootstrap_hack(self, line):
        """
        For a given location, create the appropriate directory structure in the
        hack store.

        syntax: bootstrap_hack location
        """
        mline = self._valid_syntax(self._valid_bootstraphack, line)
        if mline:
            basedir = sh.path.join(self._storehack.cache.entry, mline['location'])
            for d in ('env', 'data'):
                finaldir = sh.path.join(basedir, d)
                sh.mkdir(finaldir)
                print('{:s} created (if necessary).'.format(finaldir))

    def do_EOF(self, line):
        """
        Just quit the command-line interface.
        """
        return True

    do_q = do_quit = do_exit = do_EOF


if __name__ == '__main__':
    if len(sys.argv) > 1:
        UGetShell().onecmd(' '.join(sys.argv[1:]))
    else:
        UGetShell().cmdloop()
