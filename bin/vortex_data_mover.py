#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
vortex_data_mover.py -- Retrieve data with Vortex and put them to another location.


Note: By default, data are not pushed to their new location : the configuration
file is just read, the ResourceHandlers are generated and input data
availability is checked. This allows you to check that you configured things
correctly. When your configuration is ok, add --push to the command line.


Here is a YAML configuration file example:

    loops:
      date: 20180520-20180522-P1D
      hh_cutoff:
        period_hh_begin: 21 # For the first day, start from this HH
        period_hh_end: 6    # For the last day, end at this HH
        assim: 0-23-1       # Can be omitted, if only production cutoff are available
        production: 0-21-3  # Can be omitted, if only assim cutoff are available
      member: 0-5-1         # Can be omitted, if not sensitive

    hhcutoff_dicts:
      # These dictionaries will be used later in substitutions
      atm_histo:
        production:
          0: rangex(0-42-6)
          default: rangex(0-3-3)
        assim:
          default: rangex(0-1-1)
      atm_fp1:
        production:
          0: rangex(0-42-1)
          default: rangex(0-3-3)
        assim:
          default: rangex(0-1-1)
      atm_fp2:
        production:
          0: rangex(0-42-3)
          default: rangex(0-3-3)
        assim:
          default: rangex(0-1-1)

    defaults:
      in:
        # Define some default values here (date, cutoff, member, ... will be added
        # to them if defined in the "loops" section)
        namespace: vortex.cache.fr
        geometry: franmgsp
        model: arome
        vapp: arome
        vconf: 3dvarfr
        experiment: 7ITQ
      out:
        # Deviation to the input defaults when pushing the data
        namespace: vortex.archive.fr

    todolist:
      # Define a list of Resource-Handlers to get and put
      # First item
      - in:
          kind: historic
          basedate: ${yyyymmddhh}
          date: "[basedate]/-PT1H"
          model: surfex
          term: 1
          block: forecast
          nativefmt: fa
          format: fa
        out:
          # Deviation to the input attributes when pushing the data
          block: funnyblock  # This is just for the demo...
      # Second item
      - in:
          kind: historic
          term: ${atm_histo}  # Things defined in "hhcutoff_dicts" can be substituted
          block: forecast
          nativefmt: fa
          format: fa
      # ...
      - in:
          kind: gridpoint
          geometry: eurw1s40,frangp0025,eurw1s100  # Footprints' expansion can be used !
          # When the terms varies with the geometry, use footprints' expansion :
          term: dict(geometry:dict(eurw1s40:${atm_fp1} frangp0025:${atm_fp1} eurw1s100:${atm_fp2}))
          block: forecast
          origin: hst
          nativefmt: grib
          format: grib

"""

from __future__ import print_function, division, absolute_import, unicode_literals

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import copy
import importlib
import io
import os
import pprint
import re
import socket
import sys
import tempfile
import yaml

# Automatically set the python path
vortexbase = re.sub(os.path.sep + 'bin$', '',
                    os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(vortexbase, 'site'))
sys.path.insert(0, os.path.join(vortexbase, 'src'))

# Detect the host for special setup
fqdn = socket.getfqdn()
do_lfi_addon = False
do_rawftp = False
if re.match(r'[lps]x\w+\d+\.cnrm\.meteo.fr', fqdn):
    tmpbase = os.path.join(os.environ['HOME'], 'tmp')
elif re.match(r'(belenos|taranis)', fqdn):
    do_lfi_addon = True
    do_rawftp = True
    tmpbase = (os.environ['TMPDIR'] or
               os.environ['WORKDIR'] or
               os.path.join('/scratch/work', os.environ['LOGNAME']) or
               os.path.join('/scratch/work', os.environ['USER']))
else:
    tmpbase = os.path.join(os.environ['HOME'], 'tmp')

# Load vortex & co.
from bronx.fancies import loggers
from bronx.stdtypes import date
import footprints as fp
import vortex
import vortex.layout.dataflow
from vortex import toolbox
from vortex.syntax.stdattrs import Namespace
from vortex.data.geometries import Geometry
from vortex.util.config import AppConfigStringDecoder

import vortex.tools.folder  # @UnusedImport
import vortex.tools.grib  # @UnusedImport
import vortex.tools.lfi  # @UnusedImport

vt = vortex.ticket()
sh = vt.sh
fpx = fp.proxy
c2v = AppConfigStringDecoder()

fpx.addon(kind='allfolders', shell=sh)
fpx.addon(kind='grib', shell=sh)
if do_lfi_addon:
    fpx.addon(kind='lfi', shell=sh)

if do_rawftp:
    sh.ftraw = True  # Activate FtServ if sensible

# Main script logger
logger = loggers.getLogger(__name__)


def load_configfile(filepath):
    """Load and check the configuration file as much as possible."""
    if not sh.path.exists(filepath):
        raise IOError('The < {:s} > configuration file does not exists.'.format(filepath))
    logger.info('Reading the < %s > configuration file.', filepath)
    with io.open(filepath) as fhyaml:
        try:
            conf = yaml.load(fhyaml)
        except yaml.YAMLError:
            logger.error('Syntax error in the < %s > configuration file ', filepath)
            raise
    if not isinstance(conf, dict):
        raise ValueError('Syntax error in the < {:s} > configuration file '.format(filepath))

    # Check all kind of stuff on the config file
    for k, v in conf.items():
        if k not in ('loops', 'defaults', 'todolist', 'hhcutoff_dicts'):
            raise ValueError('The < {:s} > configuration entry is not allowed'.format(k))

        if k == 'loops':
            if not isinstance(v, dict):
                raise ValueError('"loops" must be a dictionary.')
            for lname in v:
                if lname == 'date':
                    v[lname] = date.daterangex(v[lname])
                elif lname == 'hh_cutoff':
                    if not isinstance(v[lname], dict):
                        raise ValueError('"loops[hh_cutoffs]" must be a dictionary.')
                    for cutoff in v[lname]:
                        hhs = c2v(v[lname][cutoff])
                        if isinstance(hhs, list):
                            hhs = ','.join([str(hh) for hh in hhs])
                        v[lname][cutoff] = fp.util.rangex(hhs)
                else:
                    stuff = c2v(v[lname])
                    if isinstance(hhs, list):
                        stuff = ','.join([str(s) for s in stuff])
                    v[lname] = fp.util.rangex(stuff)

        elif k == 'defaults':
            if not isinstance(v, dict):
                raise ValueError('"defaults" must be a dictionary.')
            for internal in v:
                if internal not in ('in', 'out'):
                    raise ValueError('The < {:s} > default configuration entry is not allowed'.format(internal))
            if 'in' not in v:
                raise ValueError('"defaults" must contain an "in" entry')
            if not isinstance(v['in'], dict):
                raise ValueError('defaults[in] must be a dictionary.')
            if 'out' in v and not isinstance(v['out'], dict):
                raise ValueError('defaults[out] must be a dictionary.')

        elif k == 'hhcutoff_dicts':
            if not isinstance(v, dict):
                raise ValueError('"hhcutoff_dicts" must be a dictionary.')
            for what, exp in v.items():
                if not isinstance(exp, dict):
                    raise ValueError('"hhcutoff_dicts[{:s}]" must be a dictionary.'.format(what))
                for cutoff in list(exp.keys()):
                    if not isinstance(exp[cutoff], dict):
                        raise ValueError('"hhcutoff_dicts[{:s}][{:s}]" must be a dictionary.'.format(what, cutoff))
                    exp[cutoff] = {(date.Time(hh) if hh != 'default' else hh): stuff
                                   for hh, stuff in exp[cutoff].items()}

        elif k == 'todolist':
            if not isinstance(v, list):
                raise ValueError('"todolist" must be a list.')
            for item in v:
                if not isinstance(item, dict):
                    raise ValueError('"todolist" items must be dictionaries.')
                for internal in item:
                    if internal not in ('in', 'out'):
                        raise ValueError('The < {:s} > key is not a allowed in todolist entries'.format(internal))
                    if internal in ('in', 'out'):
                        if not isinstance(item[internal], dict):
                            raise ValueError('"defaults" must be a dictionary.')

    if 'defaults' not in conf:
        conf['defaults'] = {'in': dict()}

    if 'todolist' not in conf:
        raise ValueError('No todolist provided...')

    return conf


def tweak_defaults(default_d):
    """Do some type conversions on a few special defaults."""
    for k in default_d:
        default_d[k] = c2v(default_d[k])
        if k == 'date' and not isinstance(default_d[k], date.Date):
            default_d[k] = date.Date(default_d[k])
        if 'geometry' in k and not isinstance(default_d[k], Geometry):
            default_d[k] = Geometry(tag=default_d[k])
        if k == 'namespace' and not isinstance(default_d[k], Namespace):
            default_d[k] = Namespace(default_d[k])


def tweak_attrs(attr_d, sub_arrays):
    """Call the configuration decoder on input attributes."""

    def l_cb(stuff):
        return sub_arrays[stuff]

    l_c2v = AppConfigStringDecoder(substitution_cb=l_cb)
    for k in attr_d:
        attr_d[k] = l_c2v(attr_d[k])


def bootstrap_rhs(conf):
    """Generate the resource handlers' list."""
    rhs = list()

    # Recursive calls until all loops are dealt with...
    loops = conf.get('loops', dict())

    if 'date' in loops:
        for i, a_date in enumerate(loops['date']):
            logger.info("Expending RHs for date <%s>", a_date.ymd)
            n_conf = copy.deepcopy(conf)
            del n_conf['loops']['date']
            n_conf['defaults']['in']['auto_rundate'] = a_date
            if i == 0:
                n_conf['defaults']['in']['auto_rundate_begin'] = True
            if i == len(loops['date']) - 1:
                n_conf['defaults']['in']['auto_rundate_end'] = True
            rhs.extend(bootstrap_rhs(n_conf))

    elif 'hh_cutoff' in loops:
        period_hh_begin = date.Time(loops['hh_cutoff'].pop('period_hh_begin', 0))
        period_hh_end = date.Time(loops['hh_cutoff'].pop('period_hh_end', '23:59'))
        date_begin = conf['defaults']['in'].pop('auto_rundate_begin', False)
        date_end = conf['defaults']['in'].pop('auto_rundate_end', False)
        for cutoff, hhs in loops['hh_cutoff'].items():
            for hh in hhs:
                if date_begin and hh < period_hh_begin:
                    continue
                if date_end and hh > period_hh_end:
                    continue
                logger.info("Expending RHs for cutoff <%s> and HH=%s", cutoff, str(hh))
                n_conf = copy.deepcopy(conf)
                del n_conf['loops']['hh_cutoff']
                n_conf['defaults']['in']['cutoff'] = cutoff
                auto_rundate = n_conf['defaults']['in'].pop('auto_rundate', None)
                if auto_rundate:
                    n_conf['defaults']['in']['date'] = auto_rundate + date.Time(hh)
                else:
                    n_conf['defaults']['in']['hh'] = date.Time(hh)
                rhs.extend(bootstrap_rhs(n_conf))

    else:
        # Generic loops
        if loops:
            n_conf = copy.deepcopy(conf)
            k, vrange = n_conf['loops'].popitem()
            for v in vrange:
                logger.info("Expending RHs for %s=%s", k, str(v))
                n_conf_bis = copy.deepcopy(n_conf)
                n_conf_bis['defaults']['in'][k] = v
                rhs.extend(bootstrap_rhs(n_conf_bis))

        # Go : Every loops have been expanded
        else:
            # Find out what are the defaults
            if 'defaults' in conf:
                in_defaults = conf['defaults']['in']
                tweak_defaults(in_defaults)
                out_defaults = dict(in_defaults)
                out_defaults.update(conf['defaults'].get('out', dict()))
                tweak_defaults(out_defaults)
            else:
                in_defaults = dict()
                out_defaults = dict()
            # Resolve subsitution arrays
            sub_variables = dict()
            sub_variables.update(in_defaults)
            # Shortcut for "date"
            if 'date' in in_defaults:
                sub_variables['yyyymmddhh'] = in_defaults['date'].ymdh
            if 'hhcutoff_dicts' in conf:
                if ('cutoff' in in_defaults and
                        ('date' in in_defaults or 'hh' in in_defaults)):
                    for var, spec in conf['hhcutoff_dicts'].items():
                        if 'date' in in_defaults:
                            hh = date.Time(in_defaults['date'].hour)
                        else:
                            hh = in_defaults['hh']
                        try:
                            resolved = spec[in_defaults['cutoff']].get(hh, None)
                        except KeyError:
                            logger.error('The %s cutoff is not in %s hhcutoff_dicts',
                                         in_defaults['cutoff'], var)
                            raise
                        if not resolved:
                            resolved = spec[in_defaults['cutoff']].get('default', None)
                        if resolved:
                            sub_variables[var] = resolved
                        else:
                            raise KeyError("Unable to resolve {:s} for cutoff={:s} and hh={!s}"
                                           .format(var, in_defaults['cutoff'], str(hh)))
            # Go through items and create handlers...
            for item in conf['todolist']:
                opts = dict(item)
                # Input attributes
                in_attrs_raw = opts.pop('in')
                tweak_attrs(in_attrs_raw, sub_variables)
                in_attrs = fp.util.expand(in_attrs_raw)
                # Output attributes
                out_attrs_raw = opts.pop('out', dict())
                tweak_attrs(out_attrs_raw, sub_variables)
                if out_attrs_raw and len(fp.util.expand(out_attrs_raw)) != 1:
                    raise ValueError('No expansion allowed on output parameters')
                # Go through expanded input attributes
                rhs_batch = list()
                for in_attr in in_attrs:
                    in_attr2 = dict(in_defaults)
                    in_attr2.update(in_attr)
                    try:
                        inrh = toolbox.rh(shouldfly=True, ** in_attr2)
                    except toolbox.VortexToolboxDescError:
                        logger.error("Tried to create a RH with shouldfly=True and:\n%s",
                                     pprint.pformat(in_attr2))
                        raise
                    out_attr2 = dict(out_defaults)
                    out_attr2.update(in_attr)
                    out_attr2.update(out_attrs_raw)
                    try:
                        outrh = toolbox.rh(container=inrh.container, ** out_attr2)
                    except toolbox.VortexToolboxDescError:
                        logger.error("Tried to create a RH with a container and:\n%s",
                                     pprint.pformat(out_attr2))
                        raise
                    rhs_batch.append({'in': inrh, 'out': outrh})
                rhs.append({'items': rhs_batch, 'opts': opts})

    return rhs


def just_check(todolist):
    """Go through the ResourceHandlers list and check that the resources exist"""
    failures = 0
    total = 0
    for batch in todolist:
        for item in batch['items']:
            total += 1
            try:
                rc = item['in'].check()
            except Exception:
                rc = False
            failures += int(not rc)
            logger.info('%06s: %s', '  ok  ' if rc else '**KO**', item['in'].location())
    logger.info("Check summary: %d failures / %d checks", failures, total)


def get_and_push(todolist):
    """
    Go through the ResourceHandlers list, get the resources and put them to their
    new location.
    """
    failures = 0
    total = 0
    for batch in todolist:
        for item in batch['items']:
            total += 1
            try:
                rc = item['in'].get(intent=vortex.layout.dataflow.intent.IN)
            except Exception:
                rc = False
            logger.info('get %06s: %s', '  ok  ' if rc else '**KO**', item['in'].location())
            if not rc:
                failures += 1
                logger.info('The idcard is:\n%s\n', item['in'].idcard())
                continue
            try:
                rc = item['out'].put()
            except Exception:
                rc = False
            logger.info('put %06s: %s', '  ok  ' if rc else '**KO**', item['out'].location())
            if not rc:
                failures += 1
                logger.info('The idcard is:\n%s\n', item['out'].idcard())
    logger.info("Get/Put summary: %d failures / %d items", failures, total)


if __name__ == '__main__':

    program_name = os.path.basename(sys.argv[0])
    program_shortdesc = program_name + ' -- ' + __import__('__main__').__doc__.lstrip("\n")
    program_desc = program_shortdesc

    def _process_arglist(argstr):
        # Transform a comma-separated list into a tuple
        return tuple(argstr.split(','))

    # Setup the argument parser
    parser = ArgumentParser(description=program_desc,
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--verbose", dest="verbose", action="count",
                        help="set verbosity level [default: %(default)s]")
    parser.add_argument("-p", "--extra-packages", dest="packages",
                        action="store", type=_process_arglist,
                        help="comma-separated list of extra packages to load")
    parser.add_argument("--push", dest="push", action="store_true",
                        help="actually push data (otherwise, only a check is performed)")
    parser.add_argument("configfile", action='store', help="Path to the configuration file")
    args = parser.parse_args()

    logger.info("Importing the < common > package")
    import common

    # Extra-packages
    if args.packages:
        for package in args.packages:
            logger.info("Importing the < %s > extra package", package)
            importlib.import_module(package)

    # Verbosity setup
    if args.verbose is None:
        logger.setLevel('INFO')
        loggers.getLogger('bronx').setLevel('WARNING')
        vortex.logger.setLevel('ERROR')
    if args.verbose and args.verbose >= 1:
        loggers.getLogger('bronx').setLevel('INFO')
        vortex.logger.setLevel('INFO')
    if args.verbose and args.verbose >= 2:
        logger.setLevel('DEBUG')

    # Read the YAML conf
    conf = load_configfile(args.configfile)

    # Jump to the temporary directory
    sh.mkdir(tmpbase)
    tdir = tempfile.mkdtemp(prefix='vortex_data_mover', dir=tmpbase)
    try:
        sh.cd(tdir)
        # Create all the resource handlers
        todolist = bootstrap_rhs(conf)
        logger.debug('Todo list view:\n%s', pprint.pformat(todolist))
        logger.info("Total number of RHs: %d", sum([len(td['items']) for td in todolist]))
        # Start processing...
        with sh.ftppool():
            if args.push:
                logger.info("Starting get/put sequence.")
                get_and_push(todolist)
            else:
                logger.info("Starting check")
                just_check(todolist)
    finally:
        # Some cleaning...
        sh.cd(sh.env['HOME'])
        sh.rm(tdir)
