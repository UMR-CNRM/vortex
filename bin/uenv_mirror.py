#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fetch an Uenv (and its content) and re-archive it in a
bucket or directly in ECMWF's ECFS archive.
"""

from __future__ import print_function, absolute_import, division, unicode_literals

DOC_EPILOG = """
The data are retrieved for the default storage. It may be tweaked using the
VORTEX_ARCHIVE_HOST environment variable.

When used at ECMWF (depending on the default storage or the VORTEX_ARCHIVE_HOST
environment variable), you will probably want to access a remote mass-archive
using ectrans. This will probably require the --ec-gateway and --ec-association
options.

The "Uenv" your are targeting may fetch some data using the GCO's "gget" tool.
If you want to re-archive them, you will have to provide an alternative Uget
location where they will be stored (e.g. --gdata-target=mylocation will cause
the gget element "foo.01" to be re-archived in "uget:foo.01@mylocation").
"""

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
import footprints as fp
from footprints import proxy as fpx

import vortex
from vortex.tools.net import uriparse, uriunparse
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

U_ECFS_TARGET_STORAGE = 'ecfs.ecmwf.int'
U_BUCKET_TARGET_STORAGE = '{bucket:s}.bucket.localhost'

# Main script logger
logger = loggers.getLogger(__name__)


def parse_command_line():
    """Deal with the command line."""
    # Program description
    program_name = os.path.basename(sys.argv[0])
    program_shortdesc = program_name + ' -- ' + __import__('__main__').__doc__.lstrip("\n")
    program_desc = program_shortdesc
    # Setup argument parser
    parser = argparse.ArgumentParser(description=program_desc,
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=DOC_EPILOG)
    parser.add_argument("-v", "--verbose", dest="verbose", action="count",
                        help="set verbosity level [default: %(default)s]")
    dest_group = parser.add_mutually_exclusive_group(required=True)
    dest_group.add_argument('--to-ecfs', dest='ecfs', action='store_true',
                            help='Re-archive data to ECFS')
    dest_group.add_argument('--to-bucket', dest='bucket',
                            help='Re-archive data to a bucket')
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
    if args.association:
        vtx_env.ECTRANS_REMOTE_ARCHIVE = args.association
    if args.gateway:
        vtx_env.ECTRANS_GATEWAY_HOST = args.gateway
        fpx.addon(sh=vtx_sh, kind='ecmwf')
    locale.setlocale(locale.LC_ALL,
                     os.environ.get('VORTEX_DEFAULT_ENCODING',
                                    str('en_US.UTF-8')))
    # Setup logger verbosity
    if args.verbose is None:
        (loglevel_me, loglevel_main, loglevel_fp) = ('INFO', 'ERROR', 'ERROR')
    elif args.verbose == 1:
        (loglevel_me, loglevel_main, loglevel_fp) = ('DEBUG', 'INFO', 'INFO')
    elif args.verbose == 2:
        (loglevel_me, loglevel_main, loglevel_fp) = ('DEBUG', 'DEBUG', 'INFO')
    else:
        (loglevel_me, loglevel_main, loglevel_fp) = ('DEBUG', 'DEBUG', 'DEBUG')
    loggers.setGlobalLevel(loglevel_main)
    logger.setLevel(loglevel_me)
    fp.logger.setLevel(loglevel_fp)
    del args.verbose


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
    uget_out_st = fpx.store(scheme=U_SCHEME, netloc=U_NETLOC,
                            storage=(U_ECFS_TARGET_STORAGE if args.ecfs
                                     else U_BUCKET_TARGET_STORAGE.format(bucket=args.bucket)),
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
        if uget_out_st.check(uget_target):
            logger.info("The target uenv already exists ... Doing nothing")
        else:
            logger.info('Mirroring the uenv file < %s >', cycle)
            with tempfile.NamedTemporaryFile(dir='.') as fhtmp:
                uget_default_st.get(uget_target, fhtmp.name, dict())
                uget_out_st.put(fhtmp.name, uget_target, dict())

        for k, v in slurp.items():

            logger.info('Processing entry < %s >', k)
            with isolate():

                rc = True
                todo = []

                # Uget Data
                if isinstance(v, AbstractUgetId):
                    target = u_uri('data', v)
                    try:
                        if uget_out_st.check(target):
                            logger.info("The target already exists < %s >... Doing nothing", v)
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
                            if uget_out_st.check(target):
                                logger.info("The target already exists < %s >... Doing nothing", v)
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
                            logger.info("Mutltiple data will be fetched < %s > (monthly ?)", v)
                            reftodo = [(xv, u_uri('data',
                                                  AbstractUgetId('uget:{:s}@{:s}'.format(xv, args.gdata))))
                                       for xv in mdef.names(v)]
                        # Actually getting data
                        rc = True
                        for xv, xtarget in reftodo:
                            if uget_out_st.check(xtarget):
                                logger.info("The target already exists < %s >... Doing nothing", xv)
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
                            logger.info("Uploading to < %s >",
                                        uriunparse(list(target.values())[:6]))
                            rc = rc and uget_out_st.put(xv, target)
                        if not rc:
                            logger.critical("Unable to upload data for < %s >.", v)
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
