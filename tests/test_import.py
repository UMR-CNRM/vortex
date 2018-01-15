#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from unittest import TestCase, main
import importlib
import json
import sys

import footprints as fp
import vortex

fp.loggers.getLogger('vortex').setLevel('ERROR')
fp.loggers.getLogger('common').setLevel('ERROR')

non_standard_dep = {'yaml': ['bronx.fancies.dispatch', ], }


class DynamicTerminal(object):

    def __init__(self, header, total):
        self._header = header
        numberfmt = '{:0' + str(len(str(total))) + 'd}'
        self._ifmt = numberfmt + '/' + numberfmt.format(total) + ' ({!s})'

    def __enter__(self):
        sys.stdout.write(self._header)
        self._iwatermark = 0
        self._icounter = 0
        return self

    def increment(self, msg):
        self._icounter += 1
        display = self._ifmt.format(self._icounter, msg)
        sys.stdout.write(("\b" * self._iwatermark if self._iwatermark else '') +
                         display.ljust(max(self._iwatermark, len(display))))
        self._iwatermark = max(self._iwatermark, len(display))

    def __exit__(self, etype, value, traceback):
        sys.stdout.write("\n")


class utImport(TestCase):

    def test_pyVersion(self):
        sh = vortex.sh()
        self.assertTrue(sh.python > '2.7')

    def _test_ignore_modules(self):
        exclude = list()
        for dep, modlist in non_standard_dep.items():
            try:
                importlib.import_module(dep)
            except ImportError:
                print("!!! {} is unavailable on this system. Skipping the import test for {!s}".
                      format(dep, modlist))
                exclude.extend(modlist)
        return exclude

    def test_importModules(self):
        sh = vortex.sh()
        exclude = self._test_ignore_modules()
        # Try to import all modules
        modules = sh.vortex_modules()
        with DynamicTerminal("> importing module ", len(modules) - len(exclude)) as nterm:
            for modname in [m for m in modules if m not in exclude]:
                nterm.increment(modname)
                self.assertTrue(importlib.import_module(modname))
        # Then dump all the footprints
        tdump = fp.dump.TxtDumper()
        jdump = fp.dump.JsonableDumper()
        xdump = fp.dump.XmlDomDumper(named_nodes=('attr', 'remap'))
        collected = fp.collected_classes()
        with DynamicTerminal("> dumping all collectable classes ", len(collected)) as nterm:
            for cls in collected:
                nterm.increment(cls.__name__)
                clsfp = cls.footprint_retrieve()
                # Normal txt dump: easy
                trashstr = tdump.dump(clsfp)
                # Jsonable dump: we check that it's actually jsonable !
                trashstr = jdump.dump(clsfp)
                try:
                    trashstr = json.dumps(trashstr)
                except:
                    print("\n> Json.dumps: trashstr is:\n", trashstr)
                    raise
                # XML dump: we also try to generate the document !
                try:
                    trashstr = xdump.dump(clsfp.as_dict(),
                                          root='footprint',
                                          rootattr={'class': '{:s}.{:s}'.format(cls.__module__,
                                                                                cls.__name__)})
                    trashstr = trashstr.toprettyxml(indent='  ', encoding='utf-8')
                except:
                    print("\n> xdump.dump: clsfp.as_dict() is:\n", clsfp.as_dict())
                    raise


if __name__ == '__main__':
    main()
    vortex.exit()


def get_test_class():
    return [utImport]
