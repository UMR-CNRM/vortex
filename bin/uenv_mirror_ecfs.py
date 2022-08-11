#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fetch an Uenv (and its content) and re-archive it in the ECFS archive.
"""

from __future__ import print_function, absolute_import, division, unicode_literals

import argparse
import contextlib
import locale
import os
import re
import sys
import tempfile

# Automatically set the python path
vortexbase = re.sub(os.path.sep + 'bin$', '',
                    os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(vortexbase, 'site'))
sys.path.insert(0, os.path.join(vortexbase, 'src'))

from bronx.fancies import loggers
from footprints import proxy as fpx

import vortex
from vortex.tools.net import uriparse
from vortex.tools.systems import ExecutionError

import ecmwf.tools.addons
from gco.data.stores import GGET_DEFAULT_CONFIGFILE, GcoStoreConfig
from gco.syntax.stdattrs import AbstractUgetId
from gco.tools import uenv
from iga.util.swissknife import MonthlyHandler

assert ecmwf.tools.addons

vtx_t = vortex.ticket()
vtx_sh = vtx_t.sh
vtx_env = vtx_t.env

U_SCHEME = 'uget'
U_NETLOC = 'uget.archive.fr'

G_SCHEME = 'gget'
G_NETLOC = 'gco.meteo.fr'

U_TARGET_STORAGE = 'ecfs.ecmwf.int'

# Main script logger
logger = loggers.getLogger(__name__)


def parse_command_line():
    """Deal with the command line."""
    # Program description
    program_name = os.path.basename(sys.argv[0])
    program_shortdesc = program_name + ' -- ' + __import__('__main__').__doc__.lstrip("\n")
    program_desc = program_shortdesc
    # Setup argument parser
    parser = argparse.ArgumentParser(description=program_desc)
    parser.add_argument('--ec-gateway', dest='gateway',
                        help='The ecaccess gateway hostname.')
    parser.add_argument('--ec-association', dest='association',
                        help='The ecaccess association name (to access MF archive).')
    parser.add_argument('--gdata-target', dest='gdata',
                        help='The target location for gget elements.')
    parser.add_argument('cycles', nargs='+',
                        help='The uenv cycles that need to be mirrored')
    # Process arguments
    return parser.parse_args()


def generic_setup(args):
    """Setup a few very generic things."""
    if args.gateway:
        vtx_env.ECTRANS_GATEWAY_HOST = args.gateway
    if args.association:
        vtx_env.ECTRANS_REMOTE_ARCHIVE = args.association
    locale.setlocale(locale.LC_ALL,
                     os.environ.get('VORTEX_DEFAULT_ENCODING',
                                    str('en_US.UTF-8')))
    fpx.addon(sh=vtx_sh, kind='ecmwf')


@contextlib.contextmanager
def isolate():
    """Create a proper/unique temporary directory."""
    with tempfile.TemporaryDirectory(prefix='uenv_ecfs_mirror_', dir='.') as tmpdir:
        with vtx_sh.cdcontext(tmpdir):
            yield tmpdir


def u_uri(what, where):
    """Creates an uget URI."""
    return uriparse('{:s}://{:s}/{:s}/{:s}'.format(U_SCHEME,
                                                   U_NETLOC,
                                                   what,
                                                   where.short))


def g_uri(where):
    """Creates a gget URI."""
    return uriparse('{:s}://{:s}/tampon/{:s}'.format(G_SCHEME,
                                                     G_NETLOC,
                                                     where))


def uenv_mirror(cycle, args):
    """Actualy miror *cycle."""
    cycle = AbstractUgetId(cycle)
    # Create Uget stores
    uget_default_st = fpx.store(scheme=U_SCHEME, netloc=U_NETLOC)
    uget_ecfs_st = fpx.store(scheme=U_SCHEME, netloc=U_NETLOC,
                             storage=U_TARGET_STORAGE,
                             readonly=False)
    if args.gdata:
        # If gget mirroring is requested, create the ad-hoc store
        ggetconfig = GcoStoreConfig(GGET_DEFAULT_CONFIGFILE)
        monthly_handler = MonthlyHandler(ggetconfig)
        gget_default_st = fpx.store(scheme=G_SCHEME, netloc=G_NETLOC)

    with isolate():

        logger.info('Reading the uenv file < %s >', cycle)
        slurp = uenv.contents(cycle, scheme=U_SCHEME, netloc=U_NETLOC)

        uget_target = u_uri('env', cycle)
        if uget_ecfs_st.check(uget_target):
            logger.info("The target uenv already exists ... Doing nothing (%s)",
                        uget_target)
        else:
            logger.info('Mirroring the uenv file < %s >', cycle)
            with tempfile.NamedTemporaryFile(dir='.') as fhtmp:
                uget_default_st.get(uget_target, fhtmp.name, dict())
                uget_ecfs_st.put(fhtmp.name, uget_target, dict())

        for k, v in slurp.items():

            logger.info('Processing entry < %s >', k)
            with isolate():

                rc = True
                todo = []

                # Uget Data
                if isinstance(v, AbstractUgetId):
                    target = u_uri('data', v)
                    try:
                        if uget_ecfs_st.check(target):
                            logger.info("The target already exists for < %s >... Doing nothing (%s)",
                                        v, target)
                            rc = True
                        else:
                            # The void extension avoid automatic untars...
                            rc = uget_default_st.get(target, v.id + '.void', dict())
                            if rc:
                                todo.append((v.id + '.void', target))
                    except (IOError, ExecutionError):
                        rc = False
                    if not rc:
                        logger.info('Looking for a monthly version of < %s >', v)
                        rc = True
                        for i in range(12):
                            suffix = '.m{:02d}'.format(i + 1)
                            target = u_uri('data',
                                           AbstractUgetId('uget:{0.id:s}{1:s}@{0.location:s}'
                                                          .format(v, suffix)))
                            if uget_ecfs_st.check(target):
                                logger.info("The target already exists for < %s >... Doing nothing (%s)",
                                            v, target)
                            else:
                                try:
                                    rc = rc and uget_default_st.get(target, v.id + suffix, dict())
                                    if rc:
                                        todo.append((v.id + suffix, target))
                                except (IOError, ExecutionError):
                                    rc = False
                            if not rc:
                                break

                # Gget data
                else:
                    if args.gdata:
                        # Is it a loop-generated resource ?
                        mdef = monthly_handler.mdef(v)
                        if mdef is None:
                            reftodo = [(v, u_uri('data',
                                                 AbstractUgetId('uget:{:s}@{:s}'.format(v, args.gdata))))]
                        else:
                            logger.info("Mutltiple data will be fetched for < %s > (monthly ?)", v)
                            reftodo = [(xv, u_uri('data',
                                                  AbstractUgetId('uget:{:s}@{:s}'.format(xv, args.gdata))))
                                       for xv in mdef.names(v)]
                        # Actually getting data
                        rc = True
                        for xv, xtarget in reftodo:
                            if uget_ecfs_st.check(xtarget):
                                logger.info("The target already exists for < %s >... Doing nothing (%s)",
                                            xv, xtarget)
                            else:
                                try:
                                    rc = rc and gget_default_st.get(g_uri(xv), xv, dict())
                                    # Create a tar file from directories
                                    if rc and vtx_sh.path.isdir(xv):
                                        rc = rc and vtx_sh.tar(xv + '.tgz', xv)
                                        rc = rc and vtx_sh.rm(xv)
                                        rc = rc and vtx_sh.mv(xv + '.tgz', xv)
                                    if rc:
                                        todo.append((xv, xtarget))
                                except (IOError, ExecutionError):
                                    rc = False
                            if not rc:
                                break
                if rc:
                    if todo:
                        rc = True
                        for xv, target in todo:
                            logger.debug("Uploading to < %s >", target)
                            rc = rc and uget_ecfs_st.put(xv, target)
                        if not rc:
                            logger.info("Unable to upload data for < %s >.", v)
                            raise IOError('Unable to upload data for {!s}'.format(v))
                    else:
                        logger.info('Nothing to do for < %s >', v)
                else:
                    logger.critical('Unable to fetch < %s >.', v)
                    raise IOError('Unable to fetch {!s}'.format(v))


if __name__ == "__main__":
    args = parse_command_line()
    generic_setup(args)
    for cycle in args.cycles:
        uenv_mirror(cycle, args)
