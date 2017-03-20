#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division

import io
import re

import footprints
from gco.tools import genv
from vortex.tools import date
from gco.data.stores import GcoStoreConfig, GGET_DEFAULT_CONFIGFILE


#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


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
        slurm['nnp'] = int(re.sub('\(.*$', '', e.SLURM_TASKS_PER_NODE))
    except (ValueError, TypeError) as pb:
        logger.warning('SLURM_TASKS_PER_NODE: %s', str(pb))
        slurm['nnp'] = 1

    if 'OMP_NUM_THREADS' in e:
        slurm['openmp'] = e.OMP_NUM_THREADS
    else:
        try:
            guess_cpus = int(re.sub('\(.*$', '', e.SLURM_JOB_CPUS_PER_NODE)) // 2
            guess_tasks = int(re.sub('\(.*$', '', e.SLURM_TASKS_PER_NODE))
            slurm['openmp'] = guess_cpus // guess_tasks
        except (ValueError, TypeError) as pb:
            logger.warning('SLURM_JOB_CPUS_PER_NODE: %s', str(pb))

    for x in ('nn', 'nnp', 'openmp'):
        if x in kw:
            slurm[x] = kw[x]
            del kw[x]

    return slurm, kw


def gget_resource_exists(t, ggetfile, monthly=False, verbose=False):
    """Check whether a gget resource exists in the current path or not."""

    if t.sh.path.exists(ggetfile):
        return True

    if not monthly:
        return False

    # all monthly files must be present
    months = [ggetfile + '.m{:02d}'.format(m) for m in range(1, 13)]
    missing = [month for month in months if not t.sh.path.isfile(month)]
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
    tg = sh.target()
    defs = genv.autofill(cycle)
    # Configuration handler (untar specific options)
    ggetconfig = GcoStoreConfig(GGET_DEFAULT_CONFIGFILE)

    # Save genv raw output in specified `genvpath` folder
    sh.mkdir(genvpath)
    genvconf = sh.path.join(genvpath, cycle + '.genv')
    with io.open(genvconf, mode='w', encoding='utf-8') as fp:
        fp.write(unicode(genv.as_rawstr(cycle=cycle)))

    # Start a log
    if logpath is None:
        logpath = 'freeze_cycle.log'
    log = io.open(logpath, mode='a', encoding='utf-8')
    log.write(unicode(t.line))
    log.write(unicode(t.prompt + ' ' + cycle + ' upgrade ' + date.now().reallynice() + '\n'))

    # Remove unwanted definitions
    for prefix in ('PACK', 'SRC'):
        for key in defs.keys():
            if key.startswith(prefix):
                del defs[key]

    # Build a list of unique resource names
    ggetnames = set()
    monthly = set()
    for (k, v) in defs.iteritems():
        ismonthly = k.startswith('CLIM_') or k.endswith('_MONTHLY')
        if ' ' in v:
            vset = set(v.split())
            ggetnames |= vset
            if ismonthly:
                monthly |= vset
        else:
            ggetnames.add(v)
            if ismonthly:
                monthly.add(v)

    # Perform gget on all resources to target directory
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
            if gget_resource_exists(t, name, name in monthly, verbose):
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
                    if name in monthly:
                        for month in range(1, 13):
                            sh.readonly('{}.m{:02d}'.format(name, month))
                    else:
                        sh.readonlytree(name)
                    if verbose:
                        print('ok')
                        sh.ll(name + '*')

                    if sh.is_tarname(name):
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
                    log.write(unicode('Caught Exception: ' + str(error) + '\n'))
                    if verbose:
                        print('failed &', end=' ')
                    details['failed'].append(name)
                    if force:
                        print('continue')
                    else:
                        print('abort')
                        log.write(unicode('Aborted on ' + name + '\n'))
                        log.close()
                        raise

    if verbose:
        print(t.line)

    for k, v in details.items():
        log.write(unicode('Number of items ' + k + ' = ' + str(len(v)) + '\n'))
        for item in v:
            log.write(unicode(' > ' + item + '\n'))

    log.close()

    return increase, details


def unfreeze_cycle(t, delcycle, fake=True, verbose=True, genvpath='genv', gcopath='gco/tampon', logpath=None):
    """
    Remove a frozen cycle: undoes what freeze_cycle did, but without removing
    any file in use by any of the other frozen cycles ("\*.genv" in genvpath).
    """
    sh = t.sh

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
        for (k, names) in genvdict.iteritems():
            ismonthly = k.startswith('CLIM_') or k.endswith('_MONTHLY')
            if ' ' in names:
                names = names.split()
            else:
                names = [names]
            for name in names:
                if ismonthly:
                    assert isinstance(name, basestring)
                    contents |= {name + '.m{:02d}'.format(m) for m in range(1, 13)}
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
    log.write(unicode(t.line))
    log.write(unicode(t.prompt + ' ' + delcycle + ' UNFREEZING ' + date.now().reallynice() + '\n'))

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
        log.write(unicode('Number of items ' + k + ' = ' + str(len(v)) + '\n'))
        for item in v:
            log.write(unicode(' > ' + item + '\n'))

    log.close()

    return decrease, details
