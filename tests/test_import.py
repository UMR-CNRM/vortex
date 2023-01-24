import importlib
import io
import json
import os
import sys
from unittest import TestCase, main

# Otherwise os.getcwd may fail with nose
os.chdir(os.environ['HOME'])

from bronx.fancies import loggers
import footprints as fp
import vortex
import common  # @UnusedImport

non_standard_dep = {'yaml': ['bronx.datagrip.misc',
                             'bronx.fancies.multicfg',
                             'bronx.fancies.dispatch'],
                    'PIL': ['bronx.datagrip.pyexttiff', ],
                    'numpy': ['bronx.datagrip.pyexttiff',
                              'bronx.datagrip.varbc',
                              'bronx.datagrip.varbcheaders',
                              'bronx.graphics.colormapping',
                              'bronx.meteo.constants',
                              'bronx.meteo.conversion',
                              'bronx.meteo.thermo',
                              'bronx.syntax.arrays'],
                    'netCDF4': ['bronx.datagrip.netcdf', ],
                    'matplotlib': ['bronx.graphics.colormapping',
                                   'bronx.graphics.axes'],
                    'configparser': ['sandbox.util.askjeeves'],
                    }

tloglevel = 'critical'


class DynamicTerminal:

    def __init__(self, header, total):
        self.active_terminal = False
        if hasattr(sys.stdout, 'fileno'):
            try:
                if os.isatty(sys.stdout.fileno()):
                    self.active_terminal = True
            except io.UnsupportedOperation:
                pass
        self._header = header
        numberfmt = '{:0' + str(len(str(total))) + 'd}'
        self._ifmt = numberfmt + '/' + numberfmt.format(total) + ' ({!s})'

    def __enter__(self):
        if self.active_terminal:
            sys.stdout.write(self._header)
        self._iwatermark = 0
        self._icounter = 0
        return self

    def increment(self, msg):
        self._icounter += 1
        if self.active_terminal:
            display = self._ifmt.format(self._icounter, msg)
            sys.stdout.write(("\b" * self._iwatermark if self._iwatermark else '') +
                             display.ljust(max(self._iwatermark, len(display))))
            self._iwatermark = max(self._iwatermark, len(display))

    def __exit__(self, etype, value, traceback):
        if self.active_terminal:
            sys.stdout.write("\n")


class utImport(TestCase):

    def test_pyVersion(self):
        sh = vortex.sh()
        self.assertTrue(sh.python > '2.7.0')

    def _test_ignore_modules(self):
        exclude = set()
        for dep, modlist in non_standard_dep.items():
            try:
                importlib.import_module(dep)
            except ImportError:
                print("!!! {} is unavailable on this system. Skipping the import test for {!s}".
                      format(dep, modlist))
                exclude.update(modlist)
        return list(exclude)

    def test_importModules(self):
        sh = vortex.sh()
        exclude = self._test_ignore_modules()
        # Try to import all modules
        modules = sh.vortex_modules()
        with loggers.contextboundGlobalLevel(tloglevel):
            with DynamicTerminal("> importing module ", len(modules) - len(exclude)) as nterm:
                for modname in [m for m in modules if m not in exclude]:
                    nterm.increment(modname)
                    self.assertTrue(importlib.import_module(modname))
        if not os.environ.get('VORTEX_IMPORT_UNITTEST_DO_DUMPS', '1') == '0':
            # Then dump all the footprints
            tdump = fp.dump.TxtDumper()
            jdump = fp.dump.JsonableDumper()
            xdump = fp.dump.XmlDomDumper(named_nodes=('attr', 'remap'))
            collected = fp.collected_classes()
            with loggers.contextboundGlobalLevel(tloglevel):
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
                        except Exception:
                            print("\n> Json.dumps: trashstr is:\n", trashstr)
                            raise
                        # XML dump: we also try to generate the document !
                        try:
                            trashstr = xdump.dump(clsfp.as_dict(),
                                                  root='footprint',
                                                  rootattr={'class': '{:s}.{:s}'.format(cls.__module__,
                                                                                        cls.__name__)})
                            trashstr = trashstr.toprettyxml(indent='  ', encoding='utf-8')
                        except Exception:
                            print("\n> xdump.dump: clsfp.as_dict() is:\n", clsfp.as_dict())
                            raise


if __name__ == '__main__':
    main()


def get_test_class():
    return [utImport]
