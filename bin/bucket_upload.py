#!/usr/bin/env python3

"""
Upload a given bucket to another storage.
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
from bronx.system.hash import HashAdapter
import footprints as fp
from footprints import proxy as fpx

import vortex
from vortex.tools.net import uriparse

import ecmwf.tools.addons
import gco
import olive

assert ecmwf.tools.addons
assert gco
assert olive

vtx_t = vortex.ticket()
vtx_sh = vtx_t.sh
vtx_env = vtx_t.env

BUCKET_STORAGE = '{bucket:s}.bucket.localhost'

HASH_ALGORITHMS = HashAdapter.algorithms()

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
    parser.add_argument("-v", "--verbose", dest="verbose", action="count",
                        help="set verbosity level [default: %(default)s]")
    parser.add_argument('--ecmwf', action="store_true",
                        help='Load ECMWF addons.')
    parser.add_argument('--force', action="store_true",
                        help='Overwrite existing data.')
    parser.add_argument('bucket',
                        help='The bucket for input data.')
    parser.add_argument('targetstorage',
                        help='The storage where bucket data will be sent.')
    # Process arguments
    return parser.parse_args()


def generic_setup(args):
    """Setup a few very generic things."""
    locale.setlocale(locale.LC_ALL,
                     os.environ.get('VORTEX_DEFAULT_ENCODING',
                                    'en_US.UTF-8'))
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
    # ECMWF ?
    if args.ecmwf:
        fpx.addon(sh=vtx_sh, kind='ecmwf')


@contextlib.contextmanager
def isolate():
    """Create a proper/unique temporary directory."""
    with tempfile.TemporaryDirectory(prefix='bucket_upload_', dir='.') as tmpdir:
        with vtx_sh.cdcontext(tmpdir):
            yield tmpdir


def crawl_bucket_root(bucketstorage):
    first_lev = bucketstorage.list('')
    if not isinstance(first_lev, list):
        raise OSError("The '{:s}' bucket is missing or malformed ({:s})"
                      .format(bucketstorage.bucketname, bucketstorage.fullpath('')))
    for a_scheme in sorted(first_lev):
        second_level = bucketstorage.list(a_scheme)
        if isinstance(second_level, list):
            for a_netloc in sorted(second_level):
                third_level = bucketstorage.list(vtx_sh.path.join(a_scheme, a_netloc))
                if isinstance(third_level, list):
                    for a_head in sorted(third_level):
                        xcontent = bucketstorage.list(vtx_sh.path.join(a_scheme, a_netloc, a_head))
                        if isinstance(xcontent, list) and xcontent:
                            logger.info('Crawling into scheme=%s, netloc=%s, storehead=%s',
                                        a_scheme, a_netloc, a_head)
                    yield a_scheme, a_netloc, a_head


def _crawl_generic(bucketstorage, a_scheme, a_netloc, a_head, item):
    xitem = vtx_sh.path.join(a_scheme, a_netloc, a_head, item)
    my_lev = bucketstorage.list(xitem)
    if my_lev is None:
        raise OSError('Unexpected missing directory: {:s}'
                      .format(bucketstorage.fullpath(xitem)))
    if isinstance(my_lev, list):
        for subitem in sorted(my_lev):
            yield from _crawl_generic(
                bucketstorage, a_scheme, a_netloc, a_head,
                vtx_sh.path.join(item, subitem)
            )
    else:
        if not any([item.endswith('.' + hashalgo) for hashalgo in HASH_ALGORITHMS]):
            logger.info('Input found: %s (scheme=%s, netloc=%s)', item, a_scheme, a_netloc)
            yield item


def crawl_scheme_netloc_head(bucketstorage, a_scheme, a_netloc, a_head):
    yield from _crawl_generic(bucketstorage, a_scheme, a_netloc, a_head, item='')


def input_hash_check(bucketstorage, xitem):
    # Check for any kind of hash file
    hashalgo = None
    for a_hashalgo in HASH_ALGORITHMS:
        if bucketstorage.list(xitem + '.' + a_hashalgo) is True:
            hashalgo = a_hashalgo
    # Check against the hash file (if possible)
    if hashalgo:
        full_xitem = bucketstorage.fullpath(xitem)
        hadapter = HashAdapter(hashalgo)
        if hadapter.filecheck(full_xitem, full_xitem + '.' + hashalgo):
            logger.info('%s verified against hash file (%s)', xitem, hashalgo)
        else:
            raise OSError('{:s} is inconsistent with its hashfile ({:s}).'
                          .format(full_xitem, hashalgo))


if __name__ == "__main__":
    args = parse_command_line()
    generic_setup(args)

    # Create the bucket storage object
    bstorage = fpx.archive(kind='std',
                           storage=BUCKET_STORAGE.format(bucket=args.bucket),
                           tube='inplace',
                           readonly=True)

    error_list = []

    with isolate():

        for scheme, netloc, head in crawl_bucket_root(bstorage):

            # Target Store object
            target_store = fpx.store(scheme=scheme,
                                     netloc=netloc,
                                     storehead=head,
                                     storage=args.targetstorage,
                                     readonly=False)

            for item in crawl_scheme_netloc_head(bstorage, scheme, netloc, head):
                xitem = vtx_sh.path.join(scheme, netloc, head, item)
                bucket_item = bstorage.fullpath(xitem)
                logger.debug('Input data location: %s', bucket_item)
                target_uri_str = '{:s}://{:s}/{:s}'.format(scheme, netloc, item)
                logger.debug('Target URI         : %s', target_uri_str)
                target_uri = uriparse(target_uri_str)
                do_upload = True

                if not args.force:
                    do_upload = not target_store.check(target_uri)
                    if not do_upload:
                        logger.info("The target already exists (%s). Skipping.",
                                    target_store.locate(target_uri))

                if do_upload:
                    try:
                        input_hash_check(bstorage, xitem)
                        rc_upload = target_store.put(bucket_item, target_uri)
                    except OSError:
                        logger.exception("Exception caught during upload.")
                        rc_upload = False
                    if rc_upload:
                        logger.info("%s Uploaded", xitem)
                    else:
                        error_list.append(xitem)
                        logger.error("%s upload FAILED", xitem)

        if error_list:
            logger.critical("%d upload error(s) occured:\n%s",
                            len(error_list), '\n'.join(error_list))
            raise OSError("Some of the upload failed.")
