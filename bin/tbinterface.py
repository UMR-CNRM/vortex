#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import argparse
import importlib
import json
from xml.dom import minidom

import footprints
import vortex


NAMESPACES_MAP = dict(swapp=('common', 'gco', 'olive'),
                      json=('common', 'gco', 'olive', 'iga', 'previmar'),
                      xml=('common', 'gco', 'olive', 'iga', 'previmar'),)

COLLECTORS_DFLT = ('container', 'provider', 'resource', 'component')


def swapp_exporter(collectors, filebase):
    outstack = ['= VERSION v{}'.format(vortex.__version__),
                '= CONTEXT Research']
    for clname in collectors:
        outstack.append('')
        outstack.append('= CLASS {}S'.format(clname.upper()))
        for c in footprints.collectors.get(tag=clname).items():
            attrx = list()
            attro = list()
            attrs = c.footprint_retrieve().attr
            for a in attrs.keys():
                if 'values' in attrs[a]:
                    extra = a + '(' + ','.join([str(x) for x in attrs[a]['values']]) + ')'
                else:
                    extra = a
                if attrs[a]['optional']:
                    attro.append(extra)
                else:
                    attrx.append(extra)
            outstack.append('{:s} : {:s} / {:s}'.format(c.fullname().ljust(40),
                                                        ' '.join(sorted(attrx)),
                                                        ' '.join(sorted(attro))))
    print('Output file:', filebase + '.tbi')
    with open(filebase + '.tbi', 'w') as fd:
        fd.write('\n'.join(outstack))


def json_exporter(collectors, filebase):
    dp = footprints.dump.JsonableDumper(tag='fpdump')
    for clname in collectors:
        export_dict = {}
        for c in footprints.collectors.get(tag=clname).items():
            fp = c.footprint_retrieve()
            export_dict[c.fullname()] = dict()
            export_dict[c.fullname()]['bases'] = ["{}.{}".format(ac.__module__, ac.__name__)
                                                  for ac in c.__bases__]
            export_dict[c.fullname()]['footprint'] = dp.dump(fp)
        outfile = '{}_{}.json'.format(filebase, clname)
        print('Output file:', outfile)
        with open(outfile, 'w') as fd:
            json.dump(export_dict, fd, indent=2, encoding='utf-8')


def xml_exporter(collectors, filebase):
    dp = footprints.dump.XmlDomDumper(tag='fpdump',
                                      named_nodes=('attr', 'remap'))
    for clname in collectors:
        xdoc = minidom.Document()
        xroot = xdoc.createElement('collector')
        xroot.setAttribute('name', clname)
        for c in footprints.collectors.get(tag=clname).items():
            xclass = xdoc.createElement('class')
            xclass.setAttribute('name', c.fullname())
            xbases = xdoc.createElement('bases')
            for ac in c.__bases__:
                xbase = xdoc.createElement('base')
                xbaseT = xdoc.createTextNode("{}.{}".format(ac.__module__, ac.__name__))
                xbase.appendChild(xbaseT)
                xbases.appendChild(xbase)
            xclass.appendChild(xbases)
            cdom = dp.dump(c.footprint_retrieve(),
                           root='footprint')
            xclass.appendChild(cdom.firstChild)
            xroot.appendChild(xclass)
        xdoc.appendChild(xroot)
        # Merge the DOM
        outfile = '{}_{}.xml'.format(filebase, clname)
        print('Output file:', outfile)
        with open(outfile, 'w') as fd:
            fd.write(xdoc.toprettyxml(indent='  ', encoding='utf-8'))


if __name__ == "__main__":

    def _process_arglist(argstr):
        return tuple(argstr.split(','))

    parser = argparse.ArgumentParser(description="Dump the footprints descriptions")
    parser.add_argument('-f', '--format', help='Output format [default: %(default)s]',
                        action='store', default='swapp', choices=['swapp', 'json', 'xml'])
    parser.add_argument('-c', '--collectors', action='store', type=_process_arglist,
                        help=("Coma separated list of collectors to dump " +
                              "[default: {:s}]").format(','.join(COLLECTORS_DFLT)),
                        default=COLLECTORS_DFLT)
    parser.add_argument('-n', '--namespaces', action='store', type=_process_arglist,
                        help=("Coma separated list of namespaces to consider " +
                              "[default: depend on the format]"), default=())
    parser.add_argument('-o', '--filebase', action='store',
                        help="Basename of the output file", default="tbinterface")
    args = parser.parse_args()

    thenamespaces = args.namespaces if len(args.namespaces) else NAMESPACES_MAP[args.format]
    for namespace in thenamespaces:
        print('Importing: {}'.format(namespace))
        importlib.import_module(namespace)

    exporter = vars()['{}_exporter'.format(args.format)]
    exporter(args.collectors, args.filebase)
