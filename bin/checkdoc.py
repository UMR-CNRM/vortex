#!/usr/bin/env python
# -*- coding: utf-8 -*-

import inspect, re, sys

import vortex
sh = vortex.sh()

opts = sh.rawopts(
    defaults = dict(
        verbose = 'on',
        mkrst = 'off',
    )
)

sh.header('Checking vortex ' + vortex.__version__ + 'library documentation')
print ' > Options:', opts

from vortex.utilities.introspection import Sherlock
intro = Sherlock()

def rstcreate(rstf, mname, m):
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
        '.. versionadded:: 0.7',
        '',
        'Package',
        '-------',
        '',
        '.. autodata:: __all__',
        '',
        'Classes',
        '-------',
        ''
    ]
    with open(rstf, 'w') as fdoc:
        for docline in newdoc:
            fdoc.write(docline + "\n")
            if opts['verbose']:
                print docline
    return sh.path.exists(rstf) and sh.size(rstf) > 100

def rstfind(pattern, lines):
    return bool([x for x in lines if re.search(pattern, x) ])

report = dict(
    mkrst = list(),
    todo = list(),
    quid = list(),
    nope = list(),
    miss = list(),
)

print '=' * 80
print 'MODULES REVIEW'

for modname, loaded in sh.vortex_loaded_modules():
    print '---'
    if not loaded:
        sh.import_module(modname)
    m = sys.modules[modname]
    rst = intro.rstfile(m)
    rstloc = intro.rstshort(rst)
    okdoc = sh.path.exists(rst)
    print modname, '(', 'loaded:', loaded, '/', 'doc:', okdoc, ')'

    if opts['verbose']:
        print ' >', m.__file__
        print ' >', rst

    if not okdoc:
        if opts['mkrst']:
            report['mkrst'].append(rstloc)
            okdoc = rstcreate(rst, modname, m)

    if okdoc:
        rstinfo = list()
        with open(rst, 'r') as fdrst:
            rstinfo = fdrst.readlines()
        if rstfind('TODO', rstinfo):
            report['todo'].append(rstloc)
    else:
        report['nope'].append(rstloc)

    for objname, objptr1 in intro.getlocalmembers(m).iteritems():
        thedoc = inspect.getdoc(objptr1)
        if not thedoc:
            report['miss'].append(modname + ': ' + objname)
        elif re.search('docstring|todo', thedoc, re.IGNORECASE):
            report['quid'].append(modname + ': ' + objname)
        if inspect.isclass(objptr1):
            for objmeth, objptr2 in intro.getlocalmembers(objptr1, m).iteritems():
                thedoc = inspect.getdoc(objptr2)
                if not thedoc:
                    report['miss'].append(modname + ': ' + objname + '.' + objmeth)
                elif re.search('docstring|todo', thedoc, re.IGNORECASE):
                    report['quid'].append(modname + ': ' + objname + '.' + objmeth)

for k, v in sorted(report.iteritems()):
    print '=' * 80
    print 'REPORT /', k, '(', len(v), ')'
    for reportrst in v:
        print ' >', reportrst
