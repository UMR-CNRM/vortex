#!/usr/bin/env python
# -*- coding: utf-8 -*-

import inspect
import os
import re
import sys

# Automatically set the python path
vortexbase = os.path.dirname(os.path.abspath(__file__)).rstrip('/project/bin')
sys.path.insert(0, os.path.join(vortexbase, 'site'))
sys.path.insert(0, os.path.join(vortexbase, 'src'))

import vortex

sh = vortex.sh()

opts = sh.rawopts(
    defaults = dict(
        verbose = 'off',
        mkrst = 'on',
        missingonly = 'off',
        generaterst = '',
        discard = 'taylorism',
    )
)

# Do not create new rst file when generating a report
if opts['generaterst']:
    opts['mkrst'] = False

opts['discard'] = opts['discard'].split(',')

sh.header('Checking vortex ' + vortex.__version__ + ' library documentation')
print ' > Options:', opts

from vortex.util.introspection import Sherlock
intro = Sherlock()


def rstcreate(rstf, modname):
    print ' > Creating', rstf
    header = ':mod:`' + modname + '` --- TODO Module Header'
    newdoc = [
        header,
        '=' * len(header),
        '',
        '.. automodule:: '  + modname,
        '   :synopsis: TODO Module Synopsis',
        '',
        '.. moduleauthor:: The Vortex Team',
        '.. sectionauthor:: The Vortex Team',
        '.. versionadded:: ' + vortex.__version__,
        '',
        'Package',
        '-------',
        '',
        '.. autodata:: __all__',
        '',
        '',
        'Modules',
        '-------',
        '',
        'Included Modules',
        '----------------',
        '',
        'Classes',
        '-------',
        '',
    ]
    with open(rstf, 'w') as fdoc:
        for docline in newdoc:
            fdoc.write(docline + "\n")
            if opts['verbose']:
                print docline
    return sh.path.exists(rstf) and sh.size(rstf) > 100


def rstfind(pattern, lines):
    return bool([x for x in lines if re.search(pattern, x)])

report = dict(
    mkrst = list(),
    todo = list(),
    quid = list(),
    nope = list(),
    dstr = list(),
    miss = list(),
)

print '=' * 80
print 'MODULES REVIEW'

for modulename, loaded in sh.vortex_loaded_modules():
    if not all([modulename.startswith(d) for d in opts['discard']]) == False:
        continue
    if opts['verbose']:
        print '---'
    if not loaded:
        sh.import_module(modulename)
    m = sys.modules[modulename]
    rst = intro.rstfile(m)
    rstloc = intro.rstshort(rst)
    okdoc = sh.path.exists(rst)
    if opts['verbose']:
        print modulename, '(', 'loaded:', loaded, '/', 'doc:', okdoc, ')'
        print ' >', m.__file__
        print ' >', rst

    if not okdoc:
        if opts['mkrst']:
            report['mkrst'].append(rstloc)
            okdoc = rstcreate(rst, modulename)

    rstnames = set()
    if okdoc:
        rstinfo = list()
        with open(rst, 'r') as fdrst:
            rstinfo = fdrst.readlines()
        if rstfind('TODO', rstinfo):
            report['todo'].append(rstloc)
        for rstauto in [x for x in rstinfo if x.startswith('.. auto')]:
            autokind, sep, rstentry = rstauto.partition(':: ')
            rstnames.add(rstentry.strip())
    else:
        report['nope'].append(rstloc)

    for objname, objptr1 in intro.getlocalmembers(m).iteritems():
        if (objname not in rstnames) and (not objname.startswith('_')):
            report['miss'].append(rstloc + ': ' + objname)
        thedoc = inspect.getdoc(objptr1)
        if not thedoc:
            report['dstr'].append(modulename + ': ' + objname)
        elif re.search('docstring|todo|not documented yet', thedoc, re.IGNORECASE):
            report['quid'].append(modulename + ': ' + objname)
        if inspect.isclass(objptr1):
            for objmeth, objptr2 in intro.getlocalmembers(objptr1, m).iteritems():
                thedoc = inspect.getdoc(objptr2)
                if not thedoc:
                    if (not ((re.match('__.*__$', objmeth)) or
                             (re.match('_(get|set)', objmeth)) or
                             (objmeth in ('iteritems', 'keys')))):
                        report['dstr'].append(modulename + ': ' + objname + '.' + objmeth)
                elif re.search('docstring|todo|not documented yet', thedoc, re.IGNORECASE):
                    report['quid'].append(modulename + ': ' + objname + '.' + objmeth)

key_translation = {'dstr': 'Missing docstring',
                   'miss': 'Autoclass cause missing in the rst file',
                   'mkrst': 'Rst file has been created',
                   'nope': 'Unabled to find a suitable rst file',
                   'quid': 'a "TODO" was detected in the class/method docstring',
                   'todo': 'a "TODO" was detected in the rst file'}

if not opts['generaterst']:
    for k, v in sorted(report.iteritems()):
        if opts['missingonly'] and k != 'miss':
            continue
        print '=' * 80
        print 'REPORT /', k, '/', key_translation.get(k, k), '(', len(v), ')'
        for reportrst in v:
            print ' >', reportrst

else:
    fh = open(opts['generaterst'], 'w')
    fh.writelines([
        '%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n',
        'Documentation checker report\n',
        '%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n',
        '\n',
        'Here is the automatic output of the documentation checker\n',
        '\n'])
    for k, v in sorted(report.iteritems()):
        if k == 'mkrst':
            continue
        header = '\n{} - {} ({:d})\n'.format(k, key_translation.get(k, k), len(v))
        fh.writelines([header,
                       '-' * len(header) + '\n',
                       ] +
                      ['* {}\n'.format(reportrst)  for reportrst in v])
    fh.close()
