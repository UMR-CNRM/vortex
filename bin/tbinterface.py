#!/usr/bin/env python
# -*- coding: utf-8 -*-

import footprints

import vortex, common, gco, olive


def catdump(thiscollector):
    for c in thiscollector.items():
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
        print c.fullname().ljust(40), ':', ' '.join(sorted(attrx)), '/', ' '.join(sorted(attro))


print '= VERSION', 'v' + vortex.__version__
print '= CONTEXT Research'

for clname in ( 'container', 'provider', 'resource', 'component' ):
    print
    print '= CLASS', (clname+'s').upper()
    catdump(footprints.collector(clname))
