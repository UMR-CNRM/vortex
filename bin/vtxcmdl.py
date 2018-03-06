#!/usr/bin/env python2.7
# encoding: utf-8
'''
Invokes get/put on resource handlers created form the command-line options.

Any option specified on the command line (except -h and -v) will be used as
attributes by the ```vortex.toolbox.rload``` function in order to create the
resource handlers.

The only mandatory attribute is --local but some commonly used attributes
have default values (see the list below).

This scripts only supports two notations for the command line:
`--attribute=value` or `--atribute value`.
'''

from __future__ import print_function

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

One can see that namespace, vapp, vconf, model and nativefmt are automaticaly
taken from the defaults. The user can override the defaults from the
command-line.

The `rangex` utility function can be specified directly on the command-line.
For example, --term='rangex(0-6-1)' on the command-line, will result in
term = [0, 1, 2, 3, 4, 5, 6] in the ``vortex.toolbox.rload``` call.

Environment variables:

Some of the defaults can be changed bythe mean of environment varialbes:
  * --namespace default is control by VORTEX_NAMESPACE
  * --vapp default is control by VORTEX_VAPP
  * --vconf default is control by VORTEX_VCONF

'''

import sys
import os
import re
import traceback
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

# Automatically set the python path
vortexbase = re.sub(os.path.sep + 'bin$', '',
                    os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(vortexbase, 'site'))
sys.path.insert(0, os.path.join(vortexbase, 'src'))

import footprints as fp
from bronx.system import interrupt
import vortex

# Main script logger
logger = fp.loggers.getLogger(__name__)


class ExtraArgumentError(Exception):
    def __init__(self, msg='Incorrect extra arguments. Please check your command line"'):
        super(ExtraArgumentError, self).__init__(msg)


def vortex_delayed_init(t):
    '''Setup footprints'''
    import common, olive, gco  # @UnusedImport
    # Load shell addons
    import vortex.tools.folder  # @UnusedImport
    import vortex.tools.grib  # @UnusedImport
    vortex.proxy.addon(kind='allfolders', shell=t.sh)  # @UndefinedVariable
    vortex.proxy.addon(kind='grib', shell=t.sh)  # @UndefinedVariable


def actual_action(action, t, args):
    '''Performs the action request by the user (get/put).'''
    from vortex import toolbox
    rhanlers = toolbox.rload(** vars(args))
    with t.sh.ftppool():
        for n, rh in enumerate(rhanlers):
            t.sh.subtitle("Resource Handler {:02d}/{:02d}".format(n + 1, len(rhanlers)))
            rh.quickview()
            if rh.complete:
                rst = False
                try:
                    rst = getattr(rh, action)()
                except (KeyboardInterrupt, interrupt.SignalInterruptError):
                    if action == 'get':
                        # Get ride of incomplete files
                        logger.warning("The transfer was interrupted. Cleaning %s.",
                                       rh.container.localpath())
                        t.sh.remove(rh.container.localpath(), fmt=args.format)
                    raise
                finally:
                    if rst:
                        print("\n:-) Action '{}' on the resource handler went fine".format(action))
                    else:
                        print("\n:-( Action '{}' on the resource handler ended badly".format(action))
            else:
                raise ValueError("The resource handler could not be fully defined.")


def argvalue_rewrite(value):
    '''Detect and process special values in arguments.'''
    if value.startswith('rangex'):
        value = re.split('\s*,\s*', value[7:-1])
        return fp.util.rangex(* value)
    else:
        return value


def process_remaining(margs, rargs):
    '''Process all the remainging arguments and add them to the margs namespace.

    All the remaining arguments must conform to the following convention:

      * --key=value
      * --key value
    '''
    re_arg0 = re.compile('--(\w+)(?:=(.*))?$')
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


def main():
    '''Process command line options.'''

    program_name = os.path.basename(sys.argv[0])
    program_shortdesc = program_name + ' -- ' + __import__('__main__').__doc__.lstrip("\n")
    program_desc = program_shortdesc

    # Setup argument parser
    parser = ArgumentParser(description=program_desc, epilog=argparse_epilog,
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--verbose", dest="verbose", action="count",
                        help="set verbosity level [default: %(default)s]")
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
    parser.add_argument('--any_attribute', dest='dummyattribute',
                        metavar='any_value...', action='append')

    # Process arguments
    args = process_remaining(* parser.parse_known_args())
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
    interrupt.logger.setLevel(loglevel_main)
    vortex.logger.setLevel(loglevel_main)
    fp.logger.setLevel(loglevel_fp)
    del args.verbose

    # Process the action (get/true)
    program_match = re.match('vtx(get|put)(?:\.py)?$', program_name)
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
    for key, value in vars(args).iteritems():
        logger.debug('  + {} = {!s}'.format(key, value))

    try:
        t.sh.signal_intercept_on()
        vortex_delayed_init(t)
        actual_action(action, t, args)
        t.sh.signal_intercept_off()

    except (KeyboardInterrupt, interrupt.SignalInterruptError) as e:
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        return 1

    except Exception, e:
        traceback.print_exc()
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
