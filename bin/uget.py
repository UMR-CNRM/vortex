#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Utility that manages the Uget Hack and Archive Stores.
"""

from __future__ import print_function, absolute_import, division, unicode_literals
import six

import cmd
from six.moves import configparser
import io
import itertools
import locale
import logging
import os
import re
import stat
import sys
from tempfile import mkdtemp

# Automatically set the python path
vortexbase = re.sub(os.path.sep + 'bin$', '',
                    os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(vortexbase, 'site'))
sys.path.insert(0, os.path.join(vortexbase, 'src'))

locale.setlocale(locale.LC_ALL, os.environ.get('VORTEX_DEFAULT_ENCODING', str('en_US.UTF-8')))

from bronx.fancies.display import query_yes_no_quit, print_tablelike
from bronx.syntax.decorators import nicedeco
from bronx.stdtypes.tracking import MappingTracker
from footprints import proxy as fpx

import vortex
from vortex.tools.net import uriparse
from vortex.tools.systems import ExecutionError

from gco.data.stores import UgetStore
from gco.syntax.stdattrs import UgetId
from gco.tools import genv, uenv

vortex.logger.setLevel(logging.WARNING)

sh = vortex.ticket().sh
gl = vortex.ticket().glove
tg = sh.target()


# A decorator that fills the method documentation with the standard UgetId
# description
def ugetid_doc(func):
    """The 'UgetId' identifies a Uget element. Its formed of an *element_name* and
          of a *location* : it looks like 'element_name@location'. The @location part
          may be omitted. In such a case the default_location is used (see the
          'set' and 'info' commands)."""
    func.__doc__ = re.sub(r'\bUGETID_DOC\b', ugetid_doc.__doc__, func.__doc__)
    return func


#  A decorator that enables FTP connection pooling for a given method
@nicedeco
def ftp_pooling(func):
    def ftp_pooling_wrapper(*args, **kwargs):
        with sh.ftppool():
            return func(*args, **kwargs)
    return ftp_pooling_wrapper


class WeakUgetStore(UgetStore):
    """Combined hack and central Uget stores."""

    _footprint = dict(
        info = 'Uget weak access',
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

    _valid_partial_ugetid = r'(?:u(?:get|env):)?(?P<shortuget>(?P<id>\S+?)(?:@(?P<location>\w+))?\b)'
    _valid_partial_baseid = r'(?:(?(gco)|u(?:get|env):))?(?P<baseshort>(?P<baseid>\S+?)(?(gco)\b|(?:@(?P<baselocation>\w+))?\b))'
    _valid_check = re.compile(r'(?P<what>data|env)\s+' + _valid_partial_ugetid + '$')
    _valid_pull = _valid_check
    _valid_push = _valid_check
    _valid_list = re.compile(r'(?P<what>data|env)(?:\s+from\s+(?P<listlocation>\w+))?(?:\s+matching\s+(?P<grep>.*))?\s*$')
    _valid_diff = re.compile(r'env\s+' + _valid_partial_ugetid + r'(?:\s+wrt\s+(?:' +
                             r'(?P<gco>g)?(?P<what>env)\s+' + _valid_partial_baseid + '|'
                             r'(?P<parent>parent)'
                             r'))?\s*$')
    _valid_hack = re.compile(r'(?P<gco>g)?(?P<what>data|env)\s+' + _valid_partial_baseid + r'\s+' +
                             r'into\s+' + _valid_partial_ugetid + '$')
    _valid_set = re.compile(r'(?:(?P<what1>storage|location)\s+(?P<value>\S+)|' +
                            r'(?P<what2>ftuser)\s+(?P<user>\S+)\s+for\s+(?P<target>\S+))$')
    _valid_bootstraphack = re.compile(r'(?P<bootlocation>\w+)')

    _config_file = sh.path.join(gl.configrc, 'uget-client-defaults.ini')

    _complete_basics_raw = ['env', 'data']
    _complete_basics_plus = _complete_basics_raw + ['genv', 'gdata']

    _push_res_fmt = "{:9s}: {:s}"
    _push_res_mfmt = "{:9s}: {:s} for month: {:02d}"

    _hack_commentline_fmt = '# Created by uget.py from an existing {:s}: {:s}\n'
    _hack_commentline_re = re.compile(r'^\s*#\s+Created\s+by\s+uget\.py\s+from\s+an\s+existing\s+(?:(?P<gco>g)|u)env:\s+' +
                                      _valid_partial_baseid + r'\s*$')

    def __init__(self, *kargs, **kwargs):
        cmd.Cmd.__init__(self, *kargs, **kwargs)
        if six.PY2:
            self._config = configparser.SafeConfigParser()
        else:
            self._config = configparser.ConfigParser()
        # Read the configuration
        if sh.path.exists(self._config_file):
            with io.open(self._config_file, 'r') as fhconf:
                self._config.readfp(fhconf)
        else:
            # Or create a void one...
            self._config.add_section('cli')
            self._cliconfig_set('storage', None)
            self._cliconfig_set('location', None)
        # Initialise the stores
        self._storehack = fpx.store(scheme='uget', netloc='uget.hack.fr')
        self._storehackrw = fpx.store(scheme='uget', netloc='uget.hack.fr', readonly=False)
        self._update_stores(storage=self._cliconfig_get('storage'))

    # A whole bunch of utility functions

    @staticmethod
    def _error(msg):
        """Print out an error message."""
        print('Error: {!s}'.format(msg))
        print()

    def _cliconfig_get(self, key):
        """Get a variable from the configuration file."""
        value = self._config.get('cli', key)
        return None if value == 'None' else value  # None string are converted to None objects

    def _cliconfig_set(self, key, value):
        """Set a variable in the configuration file."""
        value = 'None' if value is None else value  # None string are converted to None objects
        return self._config.set('cli', key, value)

    def _locationconfig_set(self, location, key, value):
        """Set a variable in the configuration file."""
        if value not in (None, 'None', 'none'):
            if not self._config.has_section('location_' + location):
                self._config.add_section('location_' + location)
            return self._config.set('location_' + location, key, value)
        else:
            if self._config.has_section('location_' + location):
                self._config.remove_option('location_' + location, key)
            return True

    def _locationconfig_get(self, location, key):
        """Set a variable in the configuration file."""
        if self._config.has_section('location_' + location):
            if self._config.has_option('location_' + location, key):
                return self._config.get('location_' + location, key)
        return None

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
                if loc in gdict and gdict[l_id] and gdict[loc] is None:
                    if gdict.get('gco', False) and shortid.startswith('base'):
                        continue
                    gdict[loc] = self._cliconfig_get('location')
                    if gdict[loc] is None:
                        print('Syntax error (got < {:s} >) but location is not set'
                              .format(self.lastcmd, line))
                        print()
                        return None
                    gdict[shortid] = '{:s}@{:s}'.format(gdict[l_id], gdict[loc])
            return gdict

    @staticmethod
    def _check_remap(rc):
        """Converts a return code to a string."""
        return 'Ok' if bool(rc) else 'MISSING'

    @property
    def _storelist(self):
        """Iterate over the hack and archive stores."""
        if six.PY2:
            return itertools.izip(('Hack', 'Archive'),
                                  (self._storehack, self._storearch))
        else:
            return zip(('Hack', 'Archive'), (self._storehack, self._storearch))

    def _uri(self, store, path):
        """Build up an URI given the store object and the path."""
        if isinstance(path, (tuple, list)):
            path = '/'.join(path)
        # Detect the location and tries to find a corresponding username
        username = ''
        m_path = re.search(r'@(\w+)$', path)
        if m_path:
            ftuser = self._locationconfig_get(m_path.group(1), 'ftuser')
            if ftuser:
                username = ftuser + '@'
        return uriparse('{:s}://{:s}{:s}/{:s}'.format(store.scheme, username, store.netloc, path))

    def _instore_check(self, store, ugetid, what='data'):
        """Look for a given *ugetid* in *store*.

        Extends the lookup to monthly element if sensible.
        """
        barerc = store.check(self._uri(store, (what, ugetid.short)))
        if what == 'data' and not barerc:
            monthchecked = list()
            for m in range(1, 13):
                monthchecked.append(bool(store.check(self._uri(store,
                                                               (what, ugetid.monthlyshort(m))))))
            if any(monthchecked):
                return [(monthchecked[m - 1], ugetid.monthlyshort(m))
                        for m in range(1, 13)]
            else:
                return [(False, ugetid.short), ]
        else:
            return [(bool(barerc), ugetid.short), ]

    def _single_check(self, store_checks):
        """Synthesise the result of several _instore_check calls."""
        chk_target = None
        # What are we looking for, monthly data or not ?
        for stname, _ in self._storelist:
            if any([chk[0] for chk in store_checks[stname]]):
                chk_target = store_checks[stname]
                break
        if chk_target:
            res_stack = list()
            expectedlen = len(chk_target)
            for i in range(expectedlen):
                res = ''
                for stname, _ in self._storelist:
                    checks = store_checks[stname]
                    if len(checks) == expectedlen and checks[i][0]:
                        res += stname + ', '
                res_stack.append((chk_target[i][1],
                                  (res.rstrip(', ') or 'MISSING')))
            return res_stack
        else:
            # The element is missing everywhere
            return [(store_checks[stname][0][1], 'MISSING'), ]

    def _single_push(self, what, shortid):
        """Push a single data to the archive store (request confirmation for overwrite)."""
        source = self._storehack.locate(self._uri(self._storehack, (what, shortid)),
                                        dict(auto_repack=True))
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

    def _generate_diff_tracker(self, mline):
        """Creates a diff tracker given the parsed *mline* user input."""
        # Target
        targetenv = self._uenv_contents(mline['shortuget'])
        if not targetenv:
            self._error("Could not get env < {:s} >".format(mline['shortuget']))
            return (None, None, None)

        # Find out what is the reference
        ref_cb = None  # Default is no reference
        refenv = dict()
        if mline['what'] is None:
            # Look for comment line that contains informations about the parent env
            if mline['parent']:
                # Fetch the target uenv file
                uenvfile = six.BytesIO()
                uri = self._uri(self._storeweak, ('env', mline['shortuget']))
                # Should always work since self._uenv_contents was called before...
                self._storeweak.get(uri, uenvfile)
                uenvfile.seek(0)
                for l in [l.decode(encoding='utf-8', errors='ignore')
                          for l in uenvfile.readlines()]:
                    cmatch = self._hack_commentline_re.match(l.rstrip('\n'))
                    if cmatch:
                        ref_cb = self._genv_contents if cmatch.group('gco') else self._uenv_contents
                        ref_element = cmatch.group('baseshort')
                        break
                if ref_cb is None:
                    self._error('Unable to find the parent env of < {:s} >'
                                .format(mline['shortuget']))
                    return (None, None, None)
                else:
                    print('The parent {:s}env is: {:s}'.format(cmatch.group('gco') or '', ref_element))
        else:
            ref_cb = self._genv_contents if mline['gco'] else self._uenv_contents
            ref_element = mline['baseshort']

        # Fetch the reference
        if ref_cb is not None:
            refenv = ref_cb(ref_element)
            if not refenv:
                self._error("Could not get env or genv < {:s} >".format(ref_element))
                return (None, None, None)

        track = MappingTracker(refenv, targetenv)
        return targetenv, refenv, track

    def _export_element_check(self, elt):
        """For a given *elt* build the list of things to export."""
        try:
            ugetid = UgetId(elt)
        except ValueError:
            if ' ' in elt:
                return ['(unexpanded list off uget/gget elements)', ]
            else:
                return [elt, ]
        else:
            uri = self._uri(self._storearch, ('data', ugetid.short))
            reslist = list()
            rc = self._storearch.check(uri)
            if not rc:
                m_list = list()
                for m in range(1, 13):
                    m_uri = self._uri(self._storearch, ('data', ugetid.monthlyshort(m)))
                    m_list.append((bool(self._storearch.check(m_uri)), m_uri))
                if any([m_test[0] for m_test in m_list]):
                    reslist.extend(m_list)
                else:
                    reslist.append((False, uri))
            else:
                reslist.append((True, uri))
            return [re.sub(r'^\w+@', '', self._storearch.locate(r[1]))
                    if r[0] else '!!!MISSING!!!'
                    for r in reslist]

    # Cmd.Cmd related stuff

    def _complete_basics(self, text, line, begidx, endidx, guesses=_complete_basics_raw):
        """Deals with auto-completion for the first level of keywords."""
        sline = line.split()
        if len(sline) == 1 or (len(sline) == 2 and sline[1] not in guesses):
            completions = guesses
        else:
            completions = []
        return [f for f in completions if not text or f.startswith(text)]

    def _complete_diff_export(self, text, line, begidx, endidx):
        """Auto-completion for the *diff* or *export* command."""
        sline = line.split()
        # First keyword
        if len(sline) == 1 or (len(sline) == 2 and sline[1] not in ('env', )):
            completions = ('env', )
        # Third keyword
        elif len(sline) == 3 or (len(sline) == 4 and sline[3] not in ('wrt', )):
            completions = ('wrt', )
        # Forth keyword
        elif len(sline) == 4 or (len(sline) == 5 and sline[4] not in ('env', 'genv', 'parent')):
            completions = ('env', 'genv', 'parent')
        # Forth keyword
        else:
            completions = ()
        return [f for f in completions if not text or f.startswith(text)]

    def _uenv_contents(self, shortid):
        try:
            theenv = uenv.contents('uget:' + shortid, scheme='uget', netloc='uget.weak.fr')
        except (IOError, OSError, uenv.UenvError) as e:
            self._error('Error getting uenv data: {!s}'.format(e))
            uenv.clearall()
            theenv = None
        return theenv

    def _genv_contents(self, cycle):
        try:
            theenv = genv.autofill(cycle)
        except (OSError, IOError, ExecutionError) as e:
            self._error('Error getting genv data: {!s}'.format(e))
            genv.clearall()
            theenv = None
        return theenv

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

    # Definition of actual uget.py commands

    def do_info(self, line):
        """
        Print some info on the uget.py command-line interface.

        The default location is used if no location is specified in a UgetId
        (i.e. an UgetID looks like: element_name@location. If @location is
        omitted, the default one is used).
        """
        print('Default location: {!s}'.format(self._cliconfig_get('location')))
        print('Hack store      : {!s}'.format(self._storehack))
        print('Archive store   : {!s}'.format(self._storearch))
        ftuser_associations = [s for s in self._config.sections()
                               if s.startswith('location_') and self._config.has_option(s, 'ftuser')]
        if ftuser_associations:
            print('FT association  :')
            locations = [s[9:] for s in ftuser_associations]
            usernames = [self._config.get(s, 'ftuser') for s in ftuser_associations]
            print_tablelike('  location < {:s} > associated with logname < {:s} >', locations, usernames)
        print()

    def complete_set(self, text, line, begidx, endidx):
        """Auto-completion for the *set* command."""
        sline = line.split()
        # First keyword
        first_choices = ['storage', 'location', 'ftuser']
        if len(sline) == 1 or (len(sline) == 2 and sline[1] not in first_choices):
            completions = first_choices
        # Second keyword
        elif sline[1] == 'ftuser' and (len(sline) == 3 or
                                       (len(sline) == 4 and sline[3] not in ('for', ))):
            completions = ('for', )
        else:
            completions = ()
        return [f for f in completions if not text or f.startswith(text)]

    def do_set(self, line):
        """
        Edit the settings of the uget.py command-line interface.

        First syntax: set (storage|location) somevalue

        * somevalue may be 'None'
        * 'set storage' refers to the hostname where the Uget archive is located
          (if None, the Vortex default is used)
        * 'set location' refers to the default location for any UgetID. (i.e.
          an UgetID looks like 'element_name@location'. If @location is omitted,
          the default one is used).

        Second syntax: set ftuser username for a_location

        * 'set ftuser' tells uget.py to use 'username' when connectind to the
          uget's archive store when working with location 'a_location'
        * If 'username' is 'None', any existing association for 'a_location' is
          deleted
        * By default, for a given location, if no username is associated, the current
          username (taken from the environment variable $LOGNAME) is used.

        Note: The uget.py settings are persistent from one session to another
        (they are stored on disk in a configuration file).
        """
        mline = self._valid_syntax(self._valid_set, line)
        if mline:
            if mline['what1'] == 'storage':
                self._cliconfig_set('storage', mline['value'])
                self._update_stores(storage=self._cliconfig_get('storage'))
            elif mline['what1'] == 'location':
                self._cliconfig_set('location', mline['value'])
            elif mline['what2'] == 'ftuser':
                self._locationconfig_set(mline['target'], 'ftuser', mline['user'])
            with open(self._config_file, 'w') as fpconf:
                self._config.write(fpconf)

    def complete_check(self, text, line, begidx, endidx):
        """Auto-completion for the *check* command."""
        return self._complete_basics(text, line, begidx, endidx)

    @ftp_pooling
    @ugetid_doc
    def do_check(self, line):
        """
        Check the availability of a given Uget element.

        Syntax: check (data|env) UgetId

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
                myenv = self._uenv_contents(mline['shortuget'])
                if not myenv:
                    return False
                outlist = list()
                for k, v in sorted(myenv.items()):
                    if isinstance(v, UgetId):
                        chkres = {stname: self._instore_check(st, v)
                                  for stname, st in self._storelist}
                        rstack = self._single_check(chkres)
                        for i, res in enumerate(rstack):
                            if len(rstack) > 1:
                                outlist.append((k, res[1],
                                                'uget:{:s} for month: {:02d}'.format(res[0], i + 1)))
                            else:
                                outlist.append((k, res[1], 'uget:{:s}'.format(res[0])))
                    else:
                        outlist.append((k, 'Unchecked', v))
                uenv.clearall()
                print_tablelike('  {:s}: {:s}  ({:s})', * zip(* outlist))
            print()

    def complete_list(self, text, line, begidx, endidx):
        """Auto-completion for the *hack* command."""
        sline = line.split()
        # First keyword
        if len(sline) == 1 or (len(sline) == 2 and sline[1] not in self._complete_basics_raw):
            completions = self._complete_basics_raw
        # Second keyword
        elif len(sline) == 2 or (len(sline) == 3 and sline[2] not in ('from', 'matching')):
            completions = ('from', 'matching')
        # Forth keyword
        elif (len(sline) >= 4 and sline[2] != 'matching' and
              (len(sline) == 4 or (len(sline) == 5 and sline[4] != 'matching'))):
            completions = ('matching', )
        else:
            completions = ()
        return [f for f in completions if not text or f.startswith(text)]

    @ftp_pooling
    def do_list(self, line):
        """
        List the archived available stuff for a given location.

        Syntax: list (data|env) [from location] [matching regex]

        * 'list data' will list all the constant data for a given location
        * 'list env' will list all the environment files for a given location
        * 'from location' may be omitted. In such a case the default_location is used
          (see the 'set' and 'info' commands)
        * the 'matching regex' part of the command can be used to filter the results
          (optional)
        """
        mline = self._valid_syntax(self._valid_list, line)
        if mline:
            actuallocation = mline['listlocation'] or self._cliconfig_get('location')
            if not actuallocation:
                print('Syntax error (got < {:s} >) but location is not set'.format(self.lastcmd, line))
                print()
                return None
            uri = self._uri(self._storearch, (mline['what'], '@' + actuallocation))
            stuff = self._storearch.list(uri, options=dict())
            if mline['grep']:
                regex = re.compile(mline['grep'])
                stuff = [s for s in stuff if regex.search(s)]
            for element in stuff:
                print(element)
            print()

    complete_diff = _complete_diff_export

    @ftp_pooling
    @ugetid_doc
    def do_diff(self, line):
        """
        Compare a Uget environment with another Uget environment or genv.

        Syntax: diff env UgetId [wrt ((env|genv) RefId|parent)]

        * UGETID_DOC
        * The optional *wrt (env|get)* clause is intended to specify a reference uenv or
          genv cycle to compare to.
        * The *wrt parent* allows to read in the uenv file which uenv/genv was
          used by the *hack* commabnd to create it.
        """
        mline = self._valid_syntax(self._valid_diff, line)
        if mline:
            targetenv, refenv, track = self._generate_diff_tracker(mline)
            if targetenv is None:
                return False
            print()
            if not (track.created or track.deleted or track.updated):
                print('There are no differences !')
                print()
            if track.created:
                print('CREATED ENTRIES:')
                todo = [(k, targetenv[k]) for k in sorted(track.created)]
                print_tablelike('  {:s} = {:s}', * zip(* todo))
                print()
            if track.deleted:
                print('DELETED ENTRIES:')
                for k in sorted(track.deleted):
                    todo = [(k, refenv[k]) for k in sorted(track.deleted)]
                print_tablelike('  {:s} (previously: {:s})', * zip(* todo))
                print()
            if track.updated:
                print('UPDATED ENTRIES:')
                for k in sorted(track.updated):
                    todo = [(k, targetenv[k], refenv[k]) for k in sorted(track.updated)]
                print_tablelike('  {:s}={:s} (previously: {:s})', * zip(* todo))
                print()

    complete_export = _complete_diff_export

    @ftp_pooling
    @ugetid_doc
    def do_export(self, line):
        """
        Export a Uget environment (with respect to another Uget environment or genv).

        Syntax: export env UgetId [wrt ((env|genv) RefId|parent)]

        * UGETID_DOC
        * The optional *wrt* clause is intended to specify a reference uenv or
          genv cycle to compare to.
        * The *wrt parent* allows to read in the uenv file which uenv/genv was
          used by the *hack* commabnd to create it.
        """
        mline = self._valid_syntax(self._valid_diff, line)
        if mline:
            targetenv, _, track = self._generate_diff_tracker(mline)
            if targetenv is None:
                return False
            print()
            if not (track.created or track.deleted or track.updated):
                print('There are no differences !')
                print()
            else:
                print('NB: Uenv keys starting with MASTER_ are omitted.')
                print()
                for (category, cfilter) in zip(('NAMELISTS', 'CONSTANTS'),
                                               (lambda k: re.match('^NAMELIST', k),
                                                lambda k: not (re.match('^NAMELIST', k) or
                                                               re.match('^MASTER', k)))):

                    def applyfilter(keys):
                        return [k for k in keys if cfilter(k)]

                    if applyfilter(track.created):
                        print('----- CREATED {:s}: -----'.format(category))
                        for k in sorted(applyfilter(track.created)):
                            print("\n* {:s}".format(k))
                            for p in self._export_element_check(targetenv[k]):
                                print(p)
                        print()
                    if applyfilter(track.deleted):
                        print('----- DELETED {:s}: -----'.format(category))
                        print()
                        for k in sorted(applyfilter(track.deleted)):
                            print(k)
                        print()
                    if applyfilter(track.updated):
                        print('----- UPDATED {:s}: -----'.format(category))
                        for k in sorted(applyfilter(track.updated)):
                            print("\n* {:s}".format(k))
                            for p in self._export_element_check(targetenv[k]):
                                print(p)
                        print()

    def complete_pull(self, text, line, begidx, endidx):
        """Auto-completion for the *pull* command."""
        return self._complete_basics(text, line, begidx, endidx)

    @ftp_pooling
    @ugetid_doc
    def do_pull(self, line):
        """
        Retrieve an Uget element.

        Syntax: pull (data|env) UgetId

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
                tofile = six.BytesIO()
            else:
                tofile = mline['id'] + sh.safe_filesuffix()
            # retrieve the resource"
            uri = self._uri(self._storeweak, (mline['what'], mline['shortuget']))
            try:
                rc = self._storeweak.get(uri, tofile, dict(auto_repack=True))
            except IOError:
                rc = False
            if not rc:
                self._error("Could not get < {:s} >".format(mline['shortuget']))
            else:
                if mline['what'] == 'env':
                    print()
                    tofile.seek(0)
                    for l in tofile:
                        print(l.decode(encoding='utf-8', errors='ignore').rstrip('\n'))
                    print()
                else:
                    sh.mv(tofile, mline['id'])

    def complete_push(self, text, line, begidx, endidx):
        """Auto-completion for the *push* command."""
        return self._complete_basics(text, line, begidx, endidx)

    @ftp_pooling
    @ugetid_doc
    def do_push(self, line):
        """
        Push an element from the Hack store to the archive store.

        Syntax: push (data|env) UgetId

        * 'push data' will push the constant data described by UgetId.
        * 'push env' will push the environment file (also refered as Uenv)
          described by UgetId.
        * UGETID_DOC

        While uploading an environment file, its content will be scanned and
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
                myenv = self._uenv_contents(mline['shortuget'])
                if not myenv:
                    return False
                for _, v in sorted(myenv.items()):
                    if isinstance(v, UgetId):
                        chkres = self._instore_check(self._storehack, v)
                        if len(chkres) == 1 and chkres[0][0]:
                            # "Simple" non-monthly case
                            print(self._push_res_fmt.format("Uploading", 'uget:' + chkres[0][1]))
                            rc = self._single_push('data', chkres[0][1])
                            if rc is not True:
                                return rc
                        elif len(chkres) > 1:
                            # Monthly stuff
                            for i, res in enumerate(chkres):
                                if res[0]:
                                    print(self._push_res_fmt.format("Uploading", 'uget:' + res[1]))
                                    rc = self._single_push('data', res[1])
                                    if rc is not True:
                                        return rc
                                else:
                                    # Missing in Hack, check in the archive...
                                    rstuff_uri = self._uri(self._storearch, ('data', res[1]))
                                    print(self._push_res_mfmt.format(self._check_remap(self._storearch.check(rstuff_uri)),
                                                                     'uget:' + res[1], i + 1))
                        else:
                            # Not in Hack, check in the archive
                            chkarch = self._instore_check(self._storearch, v)
                            for i, chk in enumerate(chkarch):
                                if len(chkarch) > 1:
                                    print(self._push_res_mfmt.format(self._check_remap(chk[0]),
                                                                     'uget:' + chk[1], i + 1))
                                else:
                                    print(self._push_res_fmt.format(self._check_remap(chk[0]),
                                                                    'uget:' + chk[1]))
                    else:
                        print(self._push_res_fmt.format('Unckecked', v))
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

    @ftp_pooling
    @ugetid_doc
    def do_hack(self, line):
        """
        Retrieve an element and place it in the Hack store.

        Syntax: hack (data|env|gdata|genv) SourceId into UgetId

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
                # Clean previous stuff...
                self._storehackrw.delete(dest_uri, dict())
            # Ok, let's create a temporary working directory
            tdir = mkdtemp(prefix='uget_at_work')
            tfile = sh.path.join(tdir, 'uget' + sh.safe_filesuffix())
            try:
                if mline['gco'] is None:
                    # The source is a Uget element
                    source_element = mline['baseid']
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
                    source_element = mline['baseid']
                    if mline['what'] == 'env':
                        mygenv = self._genv_contents(source_element)
                        if not mygenv:
                            self._error("Could not get genv < {:s} >".format(source_element))
                            return False
                        with io.open(tfile, 'w') as tfilefh:
                            tfilefh.writelines(['{:s}={:s}\n'.format(k, v)
                                                for k, v in sorted(mygenv.items()) if k not in ('cycle', )])
                    # The source is a gget data
                    else:
                        ghost = tg.get('gco:ggetarchive', 'hendrix.meteo.fr')
                        gtool = sh.path.join(tg.get('gco:ggetpath', ''), tg.get('gco:ggetcmd', 'gget'))
                        with sh.cdcontext(tdir):
                            rc = sh.spawn([gtool, '-host', ghost, source_element],
                                          output=False, fatal=False)
                            if not rc:
                                self._error("Could not get gget data < {:s} >".format(source_element))
                                return False
                            sh.mv(source_element, tfile)
                # The destination filename
                dest_loc = self._storehack.locate(dest_uri)
                # If the file is a tar file, check the content... and potentially
                # rename the first level directory.
                if sh.is_tarname(dest_loc):
                    tarbase_loc = sh.tarname_radix(sh.path.basename(dest_loc))
                    # With uget/gget, we might end up with a directory...
                    if sh.path.isdir(tfile):
                        with sh.cdcontext(tdir):
                            sh.mv(tfile, tarbase_loc)
                            sh.tar(sh.path.basename(dest_loc), tarbase_loc)
                            sh.mv(sh.path.basename(dest_loc), tfile)
                    else:
                        loctmp = mkdtemp(prefix='untar_', dir=tdir)
                        with sh.cdcontext(loctmp, clean_onexit=True):
                            sh.untar(tfile)
                            unpacked = sh.glob('*')
                            if len(unpacked) == 1 and unpacked[0] == sh.tarname_radix(source_element):
                                sh.mv(unpacked[0], tarbase_loc)
                                sh.tar(sh.path.basename(dest_loc), tarbase_loc)
                                sh.mv(sh.path.basename(dest_loc), tfile)
                else:
                    if sh.path.isdir(tfile):
                        self._error('A directory was retireved: this should not happened ! ' +
                                    'Maybe you forgot the .tar/.tgz extension for the target element.')
                        return False
                if mline['what'] == 'env':
                    # Add a comment line at the beginning of the new environment file
                    finalenv = six.BytesIO()
                    finalenv.write(self._hack_commentline_fmt
                                   .format('genv' if mline['gco'] else 'uenv', mline['baseshort'])
                                   .encode(encoding='utf-8'))
                    with io.open(tfile, 'rb') as fhini:
                        finalenv.write(fhini.read())
                    finalenv.seek(0)
                    tfile = finalenv
                # That went great ! Store the retrieved resource in the hack store !
                self._storehackrw.put(tfile, dest_uri, dict())
                # Give write permissions to the user (that's kind of dirty for a cache but that's hacking !)
                st = sh.stat(dest_loc).st_mode
                sh.chmod(dest_loc, st | stat.S_IWUSR)
            finally:
                sh.rmtree(tdir)

    @ftp_pooling
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
        if to_delete:
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
        else:
            print('There is nothing to clean...')

    def do_bootstrap_hack(self, line):
        """
        For a given location, create the appropriate directory structure in the
        hack store.

        syntax: bootstrap_hack location
        """
        mline = self._valid_syntax(self._valid_bootstraphack, line)
        if mline:
            basedir = sh.path.join(self._storehack.cache.entry, mline['bootlocation'])
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
