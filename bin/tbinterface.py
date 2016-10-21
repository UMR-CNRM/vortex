#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import argparse
import importlib
import json
import os
import sys
from xml.dom import minidom

# Automatically set the python path
vortexbase = os.path.dirname(os.path.abspath(__file__)).rstrip('/bin')
sys.path.insert(0, os.path.join(vortexbase, 'site'))
sys.path.insert(0, os.path.join(vortexbase, 'src'))

import footprints
import vortex  # @UnusedImport
# For the addons to be recognised
import vortex.tools.folder  # @UnusedImport
import vortex.tools.odb  # @UnusedImport
import vortex.tools.ddhpack  # @UnusedImport
import vortex.tools.lfi  # @UnusedImport


NAMESPACES_MAP = dict(swapp=('common', 'gco', 'olive'),
                      json=('common', 'gco', 'olive', 'iga', 'previmar'),
                      xml=('common', 'gco', 'olive', 'iga', 'previmar'),)

COLLECTORS_DFLT = ('container', 'provider', 'resource', 'component')


def collectors_list(colarg):
    if colarg[0] == 'all':
        return footprints.collectors.values()
    else:
        return [footprints.collectors.get(tag=clname) for clname in colarg]


def swapp_exporter(collectors, abstract, filebase):
    outstack = ['= VERSION v{}'.format(vortex.__version__),
                '= CONTEXT Research']
    if abstract:
        print('No way this exporter includes abstract classes... Ignoring the option')
    for collector in collectors_list(collectors):
        outstack.append('')
        outstack.append('= CLASS {}S'.format(collector.tag.upper()))
        for c in collector.items():
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


def json_exporter(collectors, abstract, filebase):
    dp = footprints.dump.JsonableDumper(tag='fpdump')

    def _add_entry(export_dict, c, abstract):
        fp = c.footprint_retrieve()
        export_dict[c.fullname()] = dict()
        export_dict[c.fullname()]['bases'] = ["{}.{}".format(ac.__module__, ac.__name__)
                                              for ac in c.__bases__]
        export_dict[c.fullname()]['footprint'] = dp.dump(fp)
        if abstract:
            export_dict[c.fullname()]['footprint_abstract'] = True

    for collector in collectors_list(collectors):
        export_dict = {}
        if abstract:
            for c in collector.abstract_classes.items():
                _add_entry(export_dict, c, abstract=True)
        for c in collector.items():
            _add_entry(export_dict, c, abstract=False)
        outfile = '{}_{}.json'.format(filebase, collector.tag)
        print('Output file:', outfile)
        with open(outfile, 'w') as fd:
            json.dump(export_dict, fd, indent=2, encoding='utf-8')


def xml_exporter(collectors, abstract, filebase):
    dp = footprints.dump.XmlDomDumper(tag='fpdump',
                                      named_nodes=('attr', 'remap'))

    def _add_entry(xroot, c, abstract):
        xclass = xdoc.createElement('class')
        xclass.setAttribute('name', c.fullname())
        xbases = xdoc.createElement('bases')
        for ac in c.__bases__:
            xbase = xdoc.createElement('base')
            xbaseT = xdoc.createTextNode("{}.{}".format(ac.__module__, ac.__name__))
            xbase.appendChild(xbaseT)
            xbases.appendChild(xbase)
        xclass.appendChild(xbases)
        if abstract:
            cdom = dp.dump(c.footprint_retrieve(), root='footprint',
                           rootattr=dict(abstract='True'))
        else:
            cdom = dp.dump(c.footprint_retrieve(), root='footprint')
        xclass.appendChild(cdom.firstChild)
        xroot.appendChild(xclass)

    xdoc_col_list = minidom.Document()
    col_export = xdoc_col_list.createElement('fp_export')

    for collector in collectors_list(collectors):
        xdoc = minidom.Document()
        xroot = xdoc.createElement('collector')
        xroot.setAttribute('name', collector.tag)
        xroot_col_list = xdoc_col_list.createElement('collector')
        xroot_col_list.setAttribute('name', collector.tag)
        col_export.appendChild(xroot_col_list)
        if abstract:
            for c in collector.abstract_classes.items():
                _add_entry(xroot, c, abstract=True)
        for c in collector.items():
            _add_entry(xroot, c, abstract=False)
        xdoc.appendChild(xroot)
        # Merge the DOM
        outfile = '{}_{}.xml'.format(filebase, collector.tag)
        print('Output file:', outfile)
        with open(outfile, 'w') as fd:
            fd.write(xdoc.toprettyxml(indent='  ', encoding='utf-8'))

    xdoc_col_list.appendChild(col_export)
    outfile1 = '{}.xml'.format(filebase)
    print('Output file:', outfile1)
    with open(outfile1, 'w') as fd:
        fd.write(xdoc_col_list.toprettyxml(indent='  ', encoding='utf-8'))


if __name__ == "__main__":

    def _process_arglist(argstr):
        return tuple(argstr.split(','))

    parser = argparse.ArgumentParser(description="Dump the footprints descriptions")
    parser.add_argument('-a', '--abstract', help='Also exports abstract classes',
                        action='store_true')
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
    exporter(args.collectors, args.abstract, args.filebase)
