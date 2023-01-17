#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Check the documentation and generates missing RST files.
"""

from __future__ import print_function, absolute_import, division, unicode_literals

import inspect
import os
import re
import string
import sys

# Automatically set the python path
vortexbase = re.sub('{0:}project{0:}bin$'.format(os.path.sep), '',
                    os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(vortexbase, 'site'))
sys.path.insert(0, os.path.join(vortexbase, 'src'))


from argparse import ArgumentParser

from bronx.fancies import loggers

import vortex
from vortex.util.introspection import Sherlock

_DOC_TEMPLATES = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                               '../templates'))


_KEY_TRANSLATION = {'dstr': 'Missing docstring',
                    'miss': 'Autoclass cause missing in the rst file',
                    'mkrst': 'Rst file has been created',
                    'nope': 'Unabled to find a suitable rst file',
                    'quid': 'a "TODO" was detected in the class/method docstring',
                    'todo': 'a "TODO" was detected in the rst file'}

_DEFAULT_AUTHOR = "The Vortex Team"
_ALT_AUTHORS = {'bronx': "The Vortex Team & many contributors"}


def process_template(tplname, **subdict):
    tplfile = os.path.join(_DOC_TEMPLATES, tplname)
    with open(tplfile, 'r', encoding='utf-8') as fhd:
        tplobj = fhd.read()
    tplobj = string.Template(tplobj)
    return tplobj.substitute(subdict)


def doc_dive(obj):
    if obj.__doc__ is not None:
        doclines = [l.strip() for l in obj.__doc__.split('\n')]
        oneliner = []
        while doclines and not doclines[0]:
            doclines.pop(0)
        for l in doclines:
            if not l:
                break
            oneliner.append(l)
        return ' '.join(oneliner).rstrip('.')
    else:
        return 'TODO description'


def create_rst(rst, modname, module):
    print(' > Creating', rst)

    if re.search(r'__init__.py$', module.__file__):
        tplfile = 'doc_package_template.tpl'
    else:
        tplfile = 'doc_module_template.tpl'

    oneliner = doc_dive(module)
    if modname.split('.', 1)[0] in _ALT_AUTHORS:
        author = _ALT_AUTHORS[modname.split('.', 1)[0]]
    else:
        author = _DEFAULT_AUTHOR
    if hasattr(module, '__all__'):
        alltext = "\n.. autodata:: __all__"
    else:
        alltext = ''

    infos = dict(modname=modname,
                 moddoc=oneliner,
                 moddoc_eq=('=' * (len(oneliner) + len(modname))),
                 author=author,
                 all=alltext, versionadd=vortex.__nextversion__)

    therst = process_template(tplfile, **infos)

    if not os.path.exists(os.path.dirname(rst)):
        os.makedirs(os.path.dirname(rst))
    with open(rst, 'w', encoding='utf-8') as fdoc:
        fdoc.write(therst)
    return os.path.exists(rst)


def rstfind(pattern, lines):
    return bool([x for x in lines if re.search(pattern, x, re.IGNORECASE)])


def inspect_rst(rst, rstloc, report):
    rstnames = set()
    with open(rst, 'r', encoding='utf-8') as fdrst:
        rstinfo = fdrst.readlines()
        if rstfind('TODO', rstinfo):
            report['todo'].append(rstloc)
        for rstauto in [x for x in rstinfo if x.startswith('.. auto')]:
            autokind, _, rstentry = rstauto.partition(':: ')
            rstnames.add((re.sub(r'.. auto(\w+)', r'\1', autokind), rstentry.strip()))
    return rstnames


def generate_rst_assist(objname, objtype):
    if objtype == 'class':
        return process_template('doc_assist_class.tpl', name=objname)
    else:
        return process_template('doc_assist_function.tpl', name=objname)


def generate_console_report(report, light=False):
    print('=' * 80)
    print('MODULES REVIEW')
    print()
    if light:
        print('REPORT /', 'miss', '/', _KEY_TRANSLATION.get('miss', 'miss'),
              '(', len(report['miss']), ')')
        print()
        for name, hint in report['miss']:
            print(' >', name)
            print()
            print(hint)
            print()
    else:
        for k, v in sorted(report.items()):
            print('=' * 80)
            print('REPORT /', k, '/', _KEY_TRANSLATION.get(k, k), '(', len(v), ')')
            for reportrst in v:
                if isinstance(reportrst, tuple):
                    reportrst = reportrst[0]
                print(' >', reportrst)
            print()


def generate_rst_report(rstoutput, report):
    with open(rstoutput, 'w', encoding='utf-8') as fh:
        fh.write(process_template('doc_rst_reporthead.tpl'))
        for k, v in sorted(report.items()):
            if k == 'mkrst':
                continue
            header = '\n{} - {} ({:d})\n'.format(k, _KEY_TRANSLATION.get(k, k), len(v))
            fh.writelines([header,
                           '-' * len(header) + '\n',
                           ] +
                          ['* {}\n'.format(reportrst[0] if isinstance(reportrst, tuple) else reportrst)
                           for reportrst in v])


def check_module(rstnames, rstloc, modulename, module, report):
    intro = Sherlock()
    for objname, objptr1 in intro.getlocalmembers(module).items():
        objtype = 'class' if inspect.isclass(objptr1) else 'function'
        if ((objtype, objname) not in rstnames) and (not objname.startswith('_')):
            report['miss'].append((rstloc + ': ' + objname,
                                   generate_rst_assist(objname, objtype)))
        thedoc = inspect.getdoc(objptr1)
        if not thedoc:
            report['dstr'].append(modulename + ': ' + objname)
        elif re.search('docstring|todo|not documented yet', thedoc, re.IGNORECASE):
            report['quid'].append(modulename + ': ' + objname)
        # Dig into classes methods
        if inspect.isclass(objptr1):
            for objmeth, objptr2 in intro.getlocalmembers(objptr1, module).items():
                thedoc = inspect.getdoc(objptr2)
                if not thedoc:
                    if (not ((re.match('__.*__$', objmeth)) or
                             (re.match('_(get|set)', objmeth)) or
                             (objmeth in ('iteritems', 'keys')))):
                        report['dstr'].append(modulename + ': ' + objname + '.' + objmeth)
                elif re.search('docstring|todo|not documented yet', thedoc, re.IGNORECASE):
                    report['quid'].append(modulename + ': ' + objname + '.' + objmeth)


def main():
    """Process command line options."""

    program_name = os.path.basename(sys.argv[0])
    program_shortdesc = program_name + ' -- ' + __import__('__main__').__doc__.lstrip("\n")
    program_desc = program_shortdesc

    # Setup the argument parser
    parser = ArgumentParser(description=program_desc)
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true",
                        help="Set verbosity flag.")

    parser.add_argument("--discard", dest="discard", action='store', default='taylorism',
                        help="Ignore some of the packages")
    parser.add_argument("--fail", dest="fail", action="store_true",
                        help="Return a non-zero error code on failure.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--light", dest="light", action="store_true",
                       help="Only check for missing stuff...")
    group.add_argument("--mkrst", dest="mkrst", action="store_true",
                       help="Build missing RST files.")
    group.add_argument("--gen-report", dest="genreport", action="store",
                       help="Generate the report in RST format.")

    args = parser.parse_args()

    # Discard may be a list
    args.discard = args.discard.split(',')

    sh = vortex.sh()

    intro = Sherlock()

    report = dict(
        mkrst=list(),
        todo=list(),
        quid=list(),
        nope=list(),
        dstr=list(),
        miss=list(),
    )

    for modulename, loaded in sh.vortex_loaded_modules():
        if any([modulename.startswith(d) for d in args.discard]):
            continue
        if not loaded:
            with loggers.contextboundGlobalLevel('error'):
                sh.import_module(modulename)

        module = sys.modules[modulename]
        rst = intro.rstfile(module)
        okdoc = sh.path.exists(rst)
        rstloc = intro.rstshort(rst)

        if args.verbose:
            print('--- ', modulename, '(', 'loaded:', loaded, '/', 'doc:', okdoc, ')')

        rstnames = set()
        if okdoc:
            rstnames = inspect_rst(rst, rstloc, report)

        check_module(rstnames, rstloc, modulename, module, report)

        if args.mkrst and not okdoc:
            report['mkrst'].append(rstloc)
            if not create_rst(rst, modulename, module):
                report['nope'].append(rstloc)

    if args.genreport:
        generate_rst_report(args.genreport, report)
    else:
        generate_console_report(report, args.mkrst or args.light)

    if args.fail:
        if report['miss'] or (not (args.light or args.mkrst) and
                              any([len(item) for item in report.values()])):
            sys.exit(1)


if __name__ == "__main__":
    main()
