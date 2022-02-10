#!/usr/bin/env python3
# encoding: utf-8

"""
Invokes get/put/prestage on resource handlers created form the command-line options.

Any option specified on the command line (except -h and -v) will be used as
attributes by the ```vortex.toolbox.rload``` function in order to create the
resource handlers.

The only mandatory attribute is --local but some commonly used attributes
have default values (see the list below).

This scripts only supports two notations for the command line:
`--attribute=value` or `--atribute value`.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import locale
import os
import re
import sys
import traceback
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

argparse_epilog = '''
Examples:

vtxget.py --local toto_[geometry:area]_[term] --kind=gridpoint --format=grib \\
  --geometry=antil0025 --origin=historic --experiment=OPER --block=forecast \\
  --date=2016050100 --term=0,12,24 --cutoff=prod --vapp=arome --vconf=antilles

will results in the following ``vortex.toolbox.rload``` call:

vortex.toolbox.rload(local='toto_[geometry:area]_[term]',
                     kind='gridpoint',
                     format='grib',
                     geometry='antil0025',
                     origin='historic',
                     experiment='OPER',
                     block='forecast',
                     date='2016050100',
                     term='0,12,24',
                     cutoff='production',
                     namespace='vortex.cache.fr',
                     vapp='arome',
                     vconf='antilles',
                     model='[vapp]',
                     nativefmt='[format]')

One can see that namespace, vapp, vconf, model and nativefmt are automatically
taken from the defaults. The user can override the defaults from the
command-line.

The `rangex` utility function can be specified directly on the command-line.
For example, --term='rangex(0-6-1)' on the command-line, will result in
term = [0, 1, 2, 3, 4, 5, 6] in the ``vortex.toolbox.rload``` call.

The `daterangex` utility is also available, e.g. this would generate the
dates from 2017 Jan. 1st, 18h (included) to 2017 Jan. 3rd, 6h (included)
by step of 6h:
  --date=daterangex('2017010118','2017010306','PT6H')

Environment variables:

Some of the defaults can be changed by means of environment variables:
  * --namespace default is controlled by VORTEX_NAMESPACE
  * --vapp default is controlled by VORTEX_VAPP
  * --vconf default is controlled by VORTEX_VCONF

'''
import importlib

# Automatically set the python path
vortexbase = re.sub(os.path.sep + 'bin$', '',
                    os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(vortexbase, 'site'))
sys.path.insert(0, os.path.join(vortexbase, 'src'))

locale.setlocale(locale.LC_ALL, os.environ.get('VORTEX_DEFAULT_ENCODING', str('en_US.UTF-8')))

import footprints as fp
from bronx.fancies import loggers
from bronx.system import interrupt
from bronx.stdtypes import date
import vortex

# Main script logger
logger = loggers.getLogger(__name__)


class ExtraArgumentError(Exception):
    """Exception raised when incorrect arguments are provided."""

    def __init__(self, msg='Incorrect extra arguments. Please check your command line"'):
        super(ExtraArgumentError, self).__init__(msg)


def vortex_delayed_init(t, loadedmods=None):
    """Setup footprints"""
    import common
    import olive
    import gco
    # Load shell addons
    import vortex.tools.folder
    import vortex.tools.grib
    # prevent the IDE from considering these unused (footprint declarations)
    assert any([common, olive, gco, vortex.tools.folder, vortex.tools.grib])
    vortex.proxy.addon(kind='allfolders', shell=t.sh)
    vortex.proxy.addon(kind='grib', shell=t.sh)
    if loadedmods:
        for m in loadedmods:
            importlib.import_module(m)


def actual_action(action, t, args, fatal=True):
    """Performs the action request by the user (get/put/prestage)."""
    from vortex import toolbox
    rhandlers = toolbox.rload(**vars(args))
    with t.sh.ftppool():
        for n, rh in enumerate(rhandlers):
            t.sh.subtitle("Resource Handler {:02d}/{:02d}".format(n + 1, len(rhandlers)))
            rh.quickview()
            if rh.complete:
                rst = False
                try:
                    rst = getattr(rh, action)()
                except (KeyboardInterrupt, interrupt.SignalInterruptError):
                    if action == 'get':
                        # Get rid of incomplete files
                        logger.warning("The transfer was interrupted. Cleaning %s.",
                                       rh.container.localpath())
                        t.sh.remove(rh.container.localpath(), fmt=args.format)
                    raise
                except Exception as e:
                    logger.warning("An exception was caught: %s.", str(e))
                    rst = False
                    if fatal:
                        raise
                finally:
                    if rst:
                        print("\n:-) Action '{}' on the resource handler went fine".format(action))
                    else:
                        print("\n:-( Action '{}' on the resource handler ended badly".format(action))
                if not rst:
                    if fatal:
                        raise IOError("... stopping everything since fatal is True and rst={!s}".format(rst))
                    else:
                        print("... but going on since fatal is False.")
            else:
                raise ValueError("The resource handler could not be fully defined.")

        # Finish the action by actually sending the pre-staging request
        if action == 'prestage':
            ctx = t.context
            ctx.prestaging_hub.flush()


def argvalue_rewrite(value):
    """Detect and process special values in arguments."""
    if value.startswith('rangex'):
        value = re.split(r'\s*,\s*', value[7:-1])
        return fp.util.rangex(*value)
    elif value.startswith('daterangex'):
        value = re.split(r'\s*,\s*', value[11:-1])
        return date.daterangex(*value)
    else:
        return value


def process_remaining(margs, rargs):
    """Process all the remaining arguments and add them to the margs namespace.

    All the remaining arguments must conform to the following convention:

      * --key=value
      * --key value
    """
    re_arg0 = re.compile(r'--(\w+)(?:=(.*))?$')
    while len(rargs):
        argmatch = re_arg0.match(rargs.pop(0))
        if argmatch is None:
            raise ExtraArgumentError()
        else:
            key = argmatch.group(1)
            value = None if argmatch.group(2) is None else argmatch.group(2)
        if value is None:
            if len(rargs) > 0:
                value = rargs.pop(0)
                if value.startswith('--'):
                    raise ExtraArgumentError()
            else:
                raise ExtraArgumentError()
        setattr(margs, key, argvalue_rewrite(value))
    return margs


def clist(ss):
    """Convert a string with comma to a list of strings"""
    if ss:
        return ss.split(",")


def main():
    """Process command line options."""

    program_name = os.path.basename(sys.argv[0])
    program_shortdesc = program_name + ' -- ' + __import__('__main__').__doc__.lstrip("\n")
    program_desc = program_shortdesc

    # Setup argument parser
    parser = ArgumentParser(description=program_desc, epilog=argparse_epilog,
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--verbose", dest="verbose", action="count",
                        help="set verbosity level [default: %(default)s]")
    parser.add_argument("-p", "--prestage", dest="prestage", action="store_true",
                        help="during a get action, prestage data first")
    parser.add_argument("--no-fatal", dest="fatal", action="store_false",
                        help="do not fail if the action do not succeed (just print a warning)")
    parser.add_argument("--local", dest="local", action="store", required=True,
                        help="path to the resource on the local filesystem")
    parser.add_argument("--format", dest="format", action="store", default="unknown",
                        help="Format of the local resource [default: %(default)s]")
    parser.add_argument("--namespace", dest="namespace", action="store",
                        default=os.environ.get('VORTEX_NAMESPACE',
                                               'vortex.archive.fr'),
                        help="provider's namespace  [default: %(default)s]")
    parser.add_argument("--vapp", dest="vapp", action="store",
                        default=os.environ.get('VORTEX_VAPP', 'arpege'),
                        help="provider's vapp [default: %(default)s]")
    parser.add_argument("--vconf", dest="vconf", action="store",
                        default=os.environ.get('VORTEX_VCONF', '4dvarfr'),
                        help="provider's vapp [default: %(default)s]")
    parser.add_argument("--model", dest="model", action="store", default='[vapp]',
                        help="model attribute used in some resources and providers [default: %(default)s]")
    parser.add_argument("--nativefmt", dest="nativefmt", action="store",
                        default='[format]',
                        help="nativefmt attribute used in some resources [default: %(default)s]")
    parser.add_argument("--loadedmods", type=clist,
                        help="comma-separated list of modules to be imported to setup more footprints [default: %(default)s]")
    parser.add_argument('--any_attribute', dest='dummyattribute',
                        metavar='any_value...', action='append')
    parser.add_argument('--ftraw', dest='ftraw', action ='store_true', help="Enable the use of ftput/ftget methods to perform transfers")
    parser.add_argument('--noftraw', dest='noftraw', action='store_false', help="Disable the use of ftget/ftput methods to perform transfers")
    parser.set_defaults(ftraw=None)
    # Process arguments
    args = process_remaining(*parser.parse_known_args())
    del args.dummyattribute

    # Setup logger verbosity
    if args.verbose is None:
        (loglevel_main, loglevel_fp) = ('WARNING', 'WARNING')
    elif args.verbose == 1:
        (loglevel_main, loglevel_fp) = ('INFO', 'INFO')
    elif args.verbose == 2:
        (loglevel_main, loglevel_fp) = ('DEBUG', 'INFO')
    else:
        (loglevel_main, loglevel_fp) = ('DEBUG', 'DEBUG')
    loggers.setGlobalLevel(loglevel_main)
    fp.logger.setLevel(loglevel_fp)
    del args.verbose

    # is it Fatal
    fatal = args.fatal
    del args.fatal

    # do some pre-staging before get actions
    prestage = args.prestage
    del args.prestage

    # automatically fill genv if need be
    args.gautofill = True

    # Process the action (get/true)
    program_match = re.match(r'vtx(get|put|prestage)(?:\.py)?$', program_name)
    if program_match is None:
        raise NotImplementedError("Unrecognised script name.")
    else:
        action = program_match.group(1)

    # Use args to create Vortex's resource handlers.
    t = vortex.ticket()
    logger.info('Root directory = %s', t.glove.siteroot)
    logger.info('Path directory = %s', t.glove.sitesrc)
    logger.info('Conf directory = %s', t.glove.siteconf)
    logger.debug('Requested action = %s', action)
    logger.debug('Current working directory = %s', os.getcwd())
    logger.debug('Detailed list or arguments')
    for key, value in vars(args).items():
        logger.debug('  + {} = {!s}'.format(key, value))
    if args.ftraw:
        if not t.sh.default_target.istransfertnode:
            raise ValueError("Transfert Nodes are mandatory for ftraw option")
        t.sh.ftraw = True
    try:
        with interrupt.SignalInterruptHandler(emitlogs=False):
            vortex_delayed_init(t, loadedmods=args.loadedmods)
            if action == 'get' and prestage:
                actual_action('prestage', t, args, fatal=fatal)
            actual_action(action, t, args, fatal=fatal)

    except (KeyboardInterrupt, interrupt.SignalInterruptError) as e:
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        return 1

    except Exception as e:
        traceback.print_exc()
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
