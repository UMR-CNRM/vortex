from contextlib import contextmanager
import copy
from datetime import datetime
from io import StringIO
import gc
from unittest import TestCase, main
import sys

from footprints import dump, reporting

expected_flat_d = {'why: Outcast value': {'attribute: someint': {'FakeClass2': 'args: 7'}},
                   'why: Could not reclass': {'attribute: thirdint': {'FakeClass2': "args: ('int', 'not_a_number')"}},
                   'why: Not a subclass': {'attribute: otherint': {'FakeClass1': 'args: 11', 'FakeClass2': 'args: 11'}},
                   'why: Not in values': {'attribute: kind': {'FakeClass1': 'args: rock', 'FakeClass2': 'args: rock'}}}
expected_flat = """- - - - -

FlatReport shuffle ['why', 'attribute']
{:s}

""".format(dump.fulldump(expected_flat_d))

expected_ordered = """     attribute_name = kind
         why = Not in values
             class : FakeClass1 (rock)
             class : FakeClass2 (rock)
     attribute_name = someint
         why = Outcast value
             class : FakeClass2 (7)
     attribute_name = otherint
         why = Not a subclass
             class : FakeClass1 (11)
             class : FakeClass2 (11)
     attribute_name = thirdint
         why = Could not reclass
             class : FakeClass2 (('int', 'not_a_number'))
"""

expected_dumper = """
     class : FakeClass1 (rock)
     class : FakeClass2 (rock)
             attribute_name = kind | why = Not in values
    ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

     class : FakeClass2 (7)
             attribute_name = someint | why = Outcast value
    ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

     class : FakeClass1 (11)
     class : FakeClass2 (11)
             attribute_name = otherint | why = Not a subclass
    ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

     class : FakeClass2 (('int', 'not_a_number'))
             attribute_name = thirdint | why = Could not reclass
    ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
"""

expected_xml_last = """<collector name="fake" stamp="2000-01-01T00:00:00">
    <class name="FakeClass1">
        <attribute args="11" name="otherint" why="Not a subclass"/>
        <attribute args="rock" name="kind" why="Not in values"/>
    </class>
    <class name="FakeClass2">
        <attribute args="11" name="otherint" why="Not a subclass"/>
        <attribute args="7" name="someint" why="Outcast value"/>
        <attribute args="rock" name="kind" why="Not in values"/>
        <attribute args="('int', 'not_a_number')" name="thirdint" why="Could not reclass"/>
    </class>
</collector>"""

expected_xml = ("""<?xml version="1.0" ?>
<report tag="tests_fp_reporting_fake1">
""" + "\n".join(['    ' + s for s in expected_xml_last.split("\n")]) +
                "\n</report>\n")

expected_xml_last += "\n"


@contextmanager
def capture(command, *args, **kwargs):
    out, sys.stdout = sys.stdout, StringIO()
    try:
        command(*args, **kwargs)
        sys.stdout.seek(0)
        yield sys.stdout.read()
    finally:
        sys.stdout = out


class FakeCollector:
    tag = 'fake'


class _FakeClassBase:

    @classmethod
    def fullname(cls):
        return cls.__name__


class FakeClass1(_FakeClassBase):
    pass


class FakeClass2(_FakeClassBase):
    pass


class utReporting(TestCase):

    def _get_fake_report(self, weak=False):
        report = reporting.get(tag="tests_fp_reporting_fake1", new=True, weak=weak)
        with self.assertRaises(reporting.FootprintBadLogEntry):
            report.add(ridiculous=FakeClass1)
        with self.assertRaises(reporting.FootprintBadLogEntry):
            report.add(candidate=FakeClass1)
        report.add(collector=FakeCollector(), stamp=datetime(2000, 1, 1, 0, 0, 0))
        with self.assertRaises(reporting.FootprintBadLogEntry):
            report.add(attribute='otherint', why=reporting.REPORT_WHY_SUBCLASS, args=11)
        report.add(candidate=FakeClass1)
        report.add(attribute='otherint', why=reporting.REPORT_WHY_SUBCLASS, args=11)
        report.add(attribute='kind', why=reporting.REPORT_WHY_OUTSIDE, args='rock')
        report.add(candidate=FakeClass2)
        report.add(attribute='otherint', why=reporting.REPORT_WHY_SUBCLASS, args=11)
        report.add(attribute='someint', why=reporting.REPORT_WHY_OUTCAST, args=7)
        report.add(attribute='kind', why=reporting.REPORT_WHY_OUTSIDE, args='rock')
        report.add(attribute='thirdint', why=reporting.REPORT_WHY_RECLASS, args=('int',
                                                                                 'not_a_number'))
        last_asdict = {'FakeClass1': {'kind': {'args': 'rock', 'why': 'Not in values'},
                                      'otherint': {'args': 11, 'why': 'Not a subclass'}},
                       'FakeClass2': {'kind': {'args': 'rock', 'why': 'Not in values'},
                                      'otherint': {'args': 11, 'why': 'Not a subclass'},
                                      'someint': {'args': 7, 'why': 'Outcast value'},
                                      'thirdint': {'args': ('int', 'not_a_number'),
                                                   'why': 'Could not reclass'}}}
        return report, last_asdict

    def test_reporting_methods(self):
        rv = reporting.get()
        self.assertIsInstance(rv, reporting.FootprintLog)
        self.assertEqual(rv.tag, 'default')

        rv = list(reporting.keys())
        for r in ['default', 'footprint-garbage']:
            self.assertIn(r, rv)

        rv = reporting.get(tag='void')
        self.assertIsInstance(rv, reporting.FootprintLog)
        self.assertEqual(rv.tag, 'void')
        self.assertTrue(rv.weak)
        self.assertEqual(rv.info(), 'Report Void:')

        rv = reporting.get(tag='footprint-garbage')
        self.assertIsInstance(rv, reporting.FootprintLog)
        self.assertEqual(rv.tag, 'footprint-garbage')

    def test_reporting_null(self):
        rv = reporting.NullReport()
        self.assertIsInstance(rv, reporting.NullReport)

        rv = reporting.NullReport(1, 2, foo=3)
        self.assertIsInstance(rv, reporting.NullReport)

        rv.add('any', 2)
        self.assertEqual(len(rv), 1)

        rv.add(foo=3)
        self.assertEqual(len(rv), 2)

        rv.add('more', extra='hello')
        self.assertEqual(len(rv), 4)

    def test_reporting_logentry(self):
        # Test the node property
        rv, last_ad = self._get_fake_report(weak=True)
        gc.collect()
        self.assertIsNone(rv.last.node)
        rv, last_ad = self._get_fake_report()
        gc.collect()
        last = rv.last
        self.assertIsInstance(last.node, FakeCollector)
        # Iterator on collector
        self.assertListEqual([c.name for c in list(last)],
                             ['FakeClass1', 'FakeClass2'])
        # ITerator on class
        self.assertListEqual([c['name'] for c in list(list(last)[0])],
                             ['otherint', 'kind'])
        # as_dict on both classes an collectors
        self.assertDictEqual(last.as_dict(), last_ad)

    def test_reporting_log(self):
        rv, last_ad = self._get_fake_report()
        # Try XML... but do not test output :-(
        rv.as_xml()
        xmlreport = rv.as_xml()
        self.assertEqual(xmlreport.dump_all(), expected_xml)
        self.assertEqual(xmlreport.dump_last(), expected_xml_last)
        expected_iter = dict()
        for logentry in rv.last:
            expected_iter.update({logentry.name + '_' + line['name']: line['why']
                                  for line in logentry})
        reformatted_report = dict()
        for line in xmlreport.iter_last():
            reformatted_report[line['classname'] + '_' + line['name']] = line['why']
        self.assertDictEqual(reformatted_report, expected_iter)

        # Global as_dict
        self.assertDictEqual(rv.as_dict(stamp=False), dict(fake_0001=last_ad))
        # Whynot
        tmp_last = copy.copy(last_ad)
        del tmp_last['FakeClass2']
        self.assertDictEqual(rv.whynot('Class1'), tmp_last)
        # Iterator
        self.assertListEqual(list(rv), [rv.last, ])

    def test_reporting_reports(self):
        rv, last_ad = self._get_fake_report()

        # Flat Report
        flatreport = rv.last.as_flat()
        flatreport.reshuffle(['why', 'attribute'], skip=False)
        with capture(flatreport.fulldump) as output:
            self.assertEqual("\n".join([o.rstrip(' ') if i < 3 else o
                                        for i, o in enumerate(output.split("\n"))]),
                             expected_flat)

        # Factorized report
        fr = rv.last.as_tree(ordering=(
            # Impose attribute ordering otherwise the test is not safe
            (('name', ), ('kind', 'someint', 'otherint', 'thirdint')),
            (('why', 'only'), (reporting.REPORT_WHY_MISSING,
                               reporting.REPORT_WHY_INVALID,
                               reporting.REPORT_WHY_OUTSIDE,
                               reporting.REPORT_WHY_OUTCAST,
                               reporting.REPORT_WHY_RECLASS,
                               reporting.REPORT_WHY_SUBCLASS,
                               reporting.REPORT_ONLY_NOTFOUND,
                               reporting.REPORT_ONLY_NOTMATCH))))
        with capture(fr.orderedprint) as output:
            self.assertEqual(output, expected_ordered)
        with capture(fr.dumper) as output:
            self.assertEqual(output, expected_dumper)


if __name__ == '__main__':
    main(verbosity=2)
