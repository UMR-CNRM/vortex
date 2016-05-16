#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from unittest import TestCase, main
import importlib
import json

import footprints as fp
import vortex


class utImport(TestCase):

    def test_pyVersion(self):
        sh = vortex.sh()
        self.assertTrue(sh.python > '2.7')

    def test_importModules(self):
        sh = vortex.sh()
        # Try to import all modules
        for modname in sh.vortex_modules():
            print '>', modname
            self.assertTrue(importlib.import_module(modname))
        # Then dump all the footprints
        tdump = fp.dump.TxtDumper()
        jdump = fp.dump.JsonableDumper()
        xdump = fp.dump.XmlDomDumper(named_nodes=('attr', 'remap'))
        for cls in fp.collected_classes():
            clsfp = cls.footprint_retrieve()
            # Normal txt dump: easy
            trashstr = tdump.dump(clsfp)
            # Jsonable dump: we check that it's actually jsonable !
            trashstr = jdump.dump(clsfp)
            trashstr = json.dumps(trashstr)
            # XML dump: we also try to generate the document !
            trashstr = xdump.dump(clsfp.as_dict(),
                                  root='footprint',
                                  rootattr={'class': '{:s}.{:s}'.format(cls.__module__,
                                                                        cls.__name__)})
            trashstr = trashstr.toprettyxml(indent='  ', encoding='utf-8')


if __name__ == '__main__':
    main()
    vortex.exit()


def get_test_class():
    return [utImport]
