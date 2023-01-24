import copy
from unittest import main
import os
import sys

if __name__ == '__main__':
    sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from .test_generic import _BaseDataContentTest

from bronx.stdtypes import date as bdate
from common.data import logs


JSON_T = """[
    {
        "kind": 1,
        "stages": [
            "load",
            "get"
        ],
        "stage": "get",
        "alternate": null,
        "role": "TheGuess",
        "intent": "in",
        "fatal": true,
        "rh": {
            "container": {
                "actualfmt": "fa",
                "cwdtied": false,
                "mode": "rb",
                "maxreadsize": 209715200,
                "filename": "ICMSHSCREINIT"
            },
            "resource": {
                "cutoff": "assim",
                "term": "03:00",
                "nativefmt": "fa",
                "geometry": "franmgsp325",
                "kind": "historic",
                "date": "201805210000",
                "clscontents": [
                    "vortex.data.contents",
                    "FormatAdapter"
                ],
                "model": "arome"
            },
            "options": {
                "insitu": false
            },
            "provider": {
                "namebuild": [
                    "vortex.util.names",
                    "VortexNameBuilder"
                ],
                "namespace": "vortex.multi.fr",
                "member": 1,
                "experiment": "X332",
                "expected": false,
                "vconf": "aefrance",
                "block": "addsurf",
                "vapp": "arome"
            }
        }
    },
    {
        "kind": 1,
        "stages": [
            "load",
            "get"
        ],
        "stage": "get",
        "alternate": null,
        "role": "Namelist",
        "intent": "inout",
        "fatal": true,
        "rh": {
            "container": {
                "actualfmt": "ascii",
                "cwdtied": false,
                "mode": "rb",
                "maxreadsize": 209715200,
                "filename": "IASI_CLDDET.NL"
            },
            "resource": {
                "binary": "arome",
                "kind": "namelist",
                "nativefmt": "foo",
                "gvar": "NAMELIST_AROME",
                "source": "namel_cloud_detect",
                "date": "201805210300",
                "clscontents": [
                    "common.data.namelists",
                    "NamelistContent"
                ],
                "model": "arome"
            },
            "options": {
                "insitu": false
            },
            "provider": {
                "genv": "al42_arome-op2.36",
                "gnamespace": "gco.multi.fr",
                "vconf": "aefrance",
                "gspool": "tampon",
                "vapp": "arome"
            }
        }
    },
    {
        "kind": 1,
        "stages": [
            "load",
            "get"
        ],
        "stage": "get",
        "alternate": "Namelist",
        "role": null,
        "intent": "inout",
        "fatal": true,
        "rh": {
            "container": {
                "actualfmt": "ascii",
                "cwdtied": false,
                "mode": "rb",
                "maxreadsize": 209715200,
                "filename": "namchannels_cris331"
            },
            "resource": {
                "binary": "arpege",
                "kind": "namelist",
                "nativefmt": "foo",
                "gvar": "NAMELIST_ARPEGE",
                "source": "namelistcris331",
                "date": "201805210300",
                "clscontents": [
                    "common.data.namelists",
                    "NamelistContent"
                ],
                "model": "arome"
            },
            "options": {
                "insitu": false,
                "channel": "cris331"
            },
            "provider": {
                "genv": "cy42_op2.69",
                "gnamespace": "gco.multi.fr",
                "vconf": "aefrance",
                "gspool": "tampon",
                "vapp": "arome"
            }
        }
    }
]"""


class UtRhListContent(_BaseDataContentTest):

    _data = (JSON_T, )

    def test_basics(self):
        ct = logs.SectionsJsonListContent()
        ct.slurp(self.insample[0])
        self.assertEqual(ct.size, 3)
        self.assertIsInstance(ct.data, logs.SectionsSlice)
        ctbis = copy.deepcopy(ct)
        self.assertIsNot(ctbis, ct)
        self.assertEqual(ctbis.data, ct.data)

    def test_filters(self):
        ct = logs.SectionsJsonListContent()
        ct.slurp(self.insample[0])
        f1 = ct.filter(role='Namelist')
        self.assertEqual(len(f1), 2)
        f1 = ct.filter(role='Namelist', genv="cy42_op2.69")
        self.assertEqual(len(f1), 1)
        self.assertEqual(f1[0]['rh']['resource']['source'], "namelistcris331")
        f1 = ct.filter(role='Namelist', source='namel_cloud_detect')
        self.assertEqual(len(f1), 1)
        with self.assertRaises(ValueError):
            ct.uniquefilter(role='Namelist')
        with self.assertRaises(ValueError):
            ct.uniquefilter(role='gruik')
        f2 = ct.uniquefilter(role='the guess')
        self.assertEqual(len(f2), 1)
        f3 = ct.filter(genv=['al42_arome-op2.36', 'cy42_op2.69'])
        self.assertEqual(len(f3), 2)
        f4 = ct.filter(filename=1)
        self.assertEqual(len(f4), 0)
        f5 = ct.filter(term=bdate.Time(3))
        self.assertEqual(len(f5), 1)
        f5 = ct.filter(term=[bdate.Time(0), bdate.Time(3), bdate.Time(6)])
        self.assertEqual(len(f5), 1)
        f6 = ct.filter(term=lambda x: 0 < bdate.Time(x) < 4)
        self.assertEqual(f5, f6)
        # Basedate mechanism
        f6 = ct.filter(baseterm=bdate.Time(3))
        self.assertEqual(f5, f6)
        f6 = ct.filter(baseterm=bdate.Time(3), basedate='201805210000')
        self.assertEqual(f5, f6)
        f6 = ct.filter(baseterm=bdate.Time(0), basedate='201805210300')
        self.assertEqual(f5, f6)
        f6 = ct.filter(baseterm=bdate.Time(0), basedate=bdate.Date('201805210300'))
        self.assertEqual(f5, f6)
        f6 = ct.filter(baseterm=bdate.Time(0), basedate='201805210000/PT3H')
        self.assertEqual(f5, f6)

    def test_attributes(self):
        ct = logs.SectionsJsonListContent()
        ct.slurp(self.insample[0])
        # Empty stuff
        f1 = ct.filter(role='gruik')
        with self.assertRaises(AttributeError):
            f1.date
        # Unique case
        f2 = ct.uniquefilter(role='the guess')
        self.assertEqual(f2.vapp, 'arome')
        self.assertEqual(f2.member, 1)
        self.assertEqual(f2.date, '201805210000')
        self.assertEqual(f2.actualfmt, 'fa')
        self.assertEqual(f2.kind, 'historic')
        with self.assertRaises(AttributeError):
            f2.gruik
        # Multiple stuff
        f3 = ct.filter(role='Namelist')
        self.assertEqual(f3.indexes, ['sslice0', 'sslice1'])
        self.assertEqual(f3.source(dict(sliceindex=f3.indexes[0]), dict()),
                         f3[0]['rh']['resource']['source'])
        self.assertEqual(f3.source(dict(), dict(sliceindex=f3.indexes[1])),
                         f3[1]['rh']['resource']['source'])
        with self.assertRaises(AttributeError):
            f3.gruik(dict(sliceindex=f3.indexes[1]), dict())
        with self.assertRaises(AttributeError):
            f3.source(dict(), dict())


if __name__ == '__main__':
    main(verbosity=2)
