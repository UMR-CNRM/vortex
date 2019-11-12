#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division, unicode_literals

import io
import re

import six

from bronx.fancies import loggers
from bronx.stdtypes import date
from gco.data.stores import GcoStoreConfig, GGET_DEFAULT_CONFIGFILE
from gco.tools import genv

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


def bestdate(day=None, hh=None):
    """Find out the most accurate ``today`` date."""
    return date.synop()


def slurm_parameters(t, **kw):
    """Figure out what could be nnodes, ntasks and openmp actual values."""
    e = t.env
    slurm = dict(openmp=1)
    try:
        slurm['nn'] = int(e.SLURM_NNODES)
    except (ValueError, TypeError) as pb:
        logger.warning('SLURM_NNODES: %s', str(pb))
        slurm['nn'] = 1

    try:
        slurm['nnp'] = int(re.sub(r'\(.*$', '', e.SLURM_TASKS_PER_NODE))
    except (ValueError, TypeError) as pb:
        logger.warning('SLURM_TASKS_PER_NODE: %s', str(pb))
        slurm['nnp'] = 1

    if 'OMP_NUM_THREADS' in e:
        slurm['openmp'] = e.OMP_NUM_THREADS
    else:
        try:
            guess_cpus = int(re.sub(r'\(.*$', '', e.SLURM_JOB_CPUS_PER_NODE)) // 2
            guess_tasks = int(re.sub(r'\(.*$', '', e.SLURM_TASKS_PER_NODE))
            slurm['openmp'] = guess_cpus // guess_tasks
        except (ValueError, TypeError) as pb:
            logger.warning('SLURM_JOB_CPUS_PER_NODE: %s', str(pb))

    for x in ('nn', 'nnp', 'openmp'):
        if x in kw:
            slurm[x] = kw[x]
            del kw[x]

    return slurm, kw


class MonthlyItem(object):
    r"""
    Describe a loop-generated family of files for gget.

    The real gget command includes a description of what genv values are monthly (concept
    extended to any family of loop-generated names), and how to generate all family names.
    E.g. the line::

        /^clim_\w+\.[\w\-]+\.\b[0-9]+\b$/       .m{01..12}

    means that a genv value matching the RE part ``r'clim_\w+\.[\w\-]+\.\b[0-9]+\b'``,
    say ``'clim_reunion.t127.01'`` would have the gget command get the 12 files named
    ``clim_reunion.t127.01.m01`` ``clim_reunion.t127.01.m02`` .. ``clim_reunion.t127.01.m12``.
    """
    LOOP_RE = re.compile(r'^(?P<before>.*){(?P<start>\d+)\.\.(?P<stop>\d+)}(?P<after>.*)$')

    def __init__(self, regex, loopdef):
        if regex[0] == '/':
            regex = regex[1:]
        if regex[-1] == '/':
            regex = regex[:-1]
        self.regex = re.compile(regex)

        loopmatch = self.LOOP_RE.match(loopdef)
        if loopmatch is None:
            raise ValueError('bad loop definition: "{}"'.format(loopdef))

        loopdict = loopmatch.groupdict()
        start = loopdict['start']
        stop = loopdict['stop']
        width = max(len(start), len(stop))
        self.start = int(start)
        self.stop = int(stop)
        self.fmt = loopdict['before'] + '{:0' + str(width) + 'd}' + loopdict['after']

    def is_monthly(self, value):
        return self.regex.match(value)

    def names(self, value):
        for num in range(self.start, self.stop + 1):
            yield value + self.fmt.format(num)


class MonthlyHandler(object):
    """
    Deal with gget monthly definitions (See also ``MonthlyItem``).

    The configuration is directly taken from the gget command::

        ~martinezs/apps/gco_toolbox/default/conf/gget/extension.conf

    """

    def __init__(self, configuration):
        conf = configuration.get('monthly', 'gget_monthly').split()
        self.mdefs = [MonthlyItem(regex, loopdef)
                      for (regex, loopdef) in zip(conf[0::2], conf[1::2])]

    def mdef(self, value):
        """
        Return the first ``MonthlyItem`` matching the value, if any.
        """
        for mdef in self.mdefs:
            if mdef.is_monthly(value):
                return mdef
        return None


def gget_resource_exists(t, ggetfile, monthly_handler, verbose=False):
    """Check whether a gget resource exists in the current path or not."""

    if t.sh.path.exists(ggetfile):
        return True

    # is it a loop-generated resource ?
    mdef = monthly_handler.mdef(ggetfile)
    if mdef is None:
        return False

    # all monthly files must be present
    missing = [name for name in mdef.names(ggetfile) if not t.sh.path.isfile(name)]
    if missing:
        if verbose:
            print('missing :', missing)
        return False
    return True


def freeze_cycle(t, cycle, force=False, verbose=True, genvpath='genv', gcopath='gco/tampon', logpath=None):
    """
    Retrieve a copy of all relevant gco resources for a cycle.
    The genv reference is kept in ./genv/cycle.genv.
    The resources are stored in current ``gcopath`` target path.
    Use ``force=True`` to continue in spite of errors.
    """
    sh = t.sh
    tg = sh.default_target
    defs = genv.autofill(cycle)

    # Configuration handler (untar specific options)
    ggetconfig = GcoStoreConfig(GGET_DEFAULT_CONFIGFILE)
    monthly_handler = MonthlyHandler(ggetconfig)

    # Save the genv raw output in the specified `genvpath` folder
    sh.mkdir(genvpath)
    genvconf = sh.path.join(genvpath, cycle + '.genv')
    with io.open(genvconf, mode='w', encoding='utf-8') as fp:
        fp.write(six.text_type(genv.as_rawstr(cycle=cycle)))

    # Start a log
    if logpath is None:
        logpath = 'freeze_cycle.log'
    log = io.open(logpath, mode='a', encoding='utf-8')
    log.write(six.text_type(t.line))
    log.write(six.text_type(t.prompt + ' ' + cycle + ' upgrade ' + date.now().reallynice() + '\n'))

    # Remove unwanted definitions
    for prefix in ('PACK', 'SRC'):
        for key in defs.keys():
            if key.startswith(prefix):
                del defs[key]

    # Build a list of unique resource names
    ggetnames = set()
    for v in defs.values():
        if ' ' in v:
            ggetnames |= set(v.split())
        else:
            ggetnames.add(v)

    # Perform a gget on all resources to the target directory
    gcmd = tg.get('gco:ggetcmd', 'gget')
    gpath = tg.get('gco:ggetpath', '')
    ghost = tg.get('gco:ggetarchive', 'hendrix.meteo.fr')

    gtool = sh.path.join(gpath, gcmd)

    increase = 0
    details = dict(retrieved=list(), inplace=list(), failed=list(), expanded=list())

    with sh.cdcontext(gcopath, create=True):
        for name in sorted(list(ggetnames)):
            if verbose:
                print(t.line)
                print(name, '...', end=' ')
            if gget_resource_exists(t, name, monthly_handler, verbose):
                if verbose:
                    print('already there')
                    sh.ll(name + '*')
                details['inplace'].append(name)
            else:
                try:
                    if verbose:
                        print('spawning: {} -host {} {}'.format(gtool, ghost, name))
                    sh.spawn([gtool, '-host', ghost, name], output=False)
                    increase += sh.size(name)
                    details['retrieved'].append(name)
                    mdef = monthly_handler.mdef(name)
                    if mdef is not None:
                        for generated_name in mdef.names(name):
                            sh.readonly(generated_name)
                    else:
                        sh.readonlytree(name)
                    if verbose:
                        print('ok')
                        sh.ll(name + '*')

                    if mdef is None and sh.is_tarname(name):
                        radix = sh.tarname_radix(name)
                        untaropts = ggetconfig.key_untar_properties(name)
                        if verbose:
                            print('expanding to {} with opts {}'.format(radix, untaropts))
                        unpacked = sh.smartuntar(name, radix, **untaropts)
                        if verbose:
                            print('unpacked:\n\t' + '\n\t'.join(unpacked))
                        for subfile in unpacked:
                            subfilepath = sh.path.join(radix, subfile)
                            details['expanded'].append(subfilepath)
                            increase += sh.size(subfilepath)
                        sh.readonlytree(radix)

                except Exception as error:
                    print(error)
                    log.write(six.text_type('Caught Exception: ' + str(error) + '\n'))
                    if verbose:
                        print('failed &', end=' ')
                    details['failed'].append(name)
                    if force:
                        print('continue')
                    else:
                        print('abort')
                        log.write(six.text_type('Aborted on ' + name + '\n'))
                        log.close()
                        raise

    if verbose:
        print(t.line)

    for k, v in details.items():
        log.write(six.text_type('Number of items ' + k + ' = ' + str(len(v)) + '\n'))
        for item in v:
            log.write(six.text_type(' > ' + item + '\n'))

    log.close()

    return increase, details


def unfreeze_cycle(t, delcycle, fake=True, verbose=True, genvpath='genv', gcopath='gco/tampon', logpath=None):
    """
    Remove a frozen cycle: undoes what freeze_cycle did, but without removing
    any file in use by any of the other frozen cycles ("\*.genv" in genvpath).
    """
    sh = t.sh

    # Monthly (loop-generated) configuration handler
    ggetconfig = GcoStoreConfig(GGET_DEFAULT_CONFIGFILE)
    monthly_handler = MonthlyHandler(ggetconfig)

    def genv_contents(cycle):
        """Return all files and level 0 directories for a cycle."""

        genvdict = genv.autofill(cycle)

        # these keys are always ignored
        for prefix in ('PACK', 'SRC'):
            for key in genvdict.keys():
                if key.startswith(prefix):
                    del genvdict[key]

        # corresponding files or directories
        contents = set()
        for names in genvdict.values():
            if ' ' in names:
                names = names.split()
            else:
                names = [names]
            for name in names:
                mdef = monthly_handler.mdef(name)
                if mdef is not None:
                    contents |= set(mdef.names(name))
                else:
                    contents.add(name)
                    if sh.is_tarname(name):
                        radix = sh.tarname_radix(name)
                        contents.add(radix)
        return contents

    # Rename the genv file (used as a marker of frozen cycle)
    sh.mkdir(genvpath)
    genvconf = sh.path.join(genvpath, delcycle + '.genv')
    if not fake and sh.path.isfile(genvconf):
        sh.move(genvconf, genvconf + '.removed')

    # Start a log
    if logpath is None:
        logpath = 'freeze_cycle.log'
    if fake:
        logpath = '/dev/null'
    log = io.open(logpath, mode='a', encoding='utf-8')
    log.write(six.text_type(t.line))
    log.write(six.text_type(t.prompt + ' ' + delcycle + ' UNFREEZING ' + date.now().reallynice() + '\n'))

    decrease = 0
    details = dict(removed=list(), failed=list())

    # all contents must be removed
    delitems = genv_contents(delcycle)

    # except if used by another cycle
    with sh.cdcontext(genvpath):
        for cycle in [re.sub(r'\.genv$', '', x) for x in sh.glob('*.genv')]:
            if cycle != delcycle:
                delitems -= genv_contents(cycle)

    # let's remove them
    with sh.cdcontext(gcopath):
        for delitem in delitems:
            if not sh.path.exists(delitem):
                continue
            size = sh.treesize(delitem)
            if fake:
                if verbose:
                    print('would remove:', delitem)
                details['removed'].append(delitem)
                decrease += size
            else:
                try:
                    sh.wpermtree(delitem, force=True)
                    if sh.remove(delitem):
                        if verbose:
                            print('removed:', delitem)
                        details['removed'].append(delitem)
                        decrease += size
                    else:
                        if verbose:
                            print('could not remove:', delitem)
                        details['failed'].append(delitem)
                except OSError as error:
                    print('OSError on removing:', delitem)
                    print(error)
                    details['failed'].append(delitem)

    if verbose:
        print(t.line)

    for k, v in details.items():
        log.write(six.text_type('Number of items ' + k + ' = ' + str(len(v)) + '\n'))
        for item in v:
            log.write(six.text_type(' > ' + item + '\n'))

    log.close()

    return decrease, details
