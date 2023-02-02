import re
from unittest import TestCase, main

from bronx.fancies import dump
from bronx.fancies.dump import TxtDumper, JsonableDumper, XmlDomDumper,\
    OneLineTxtDumper


class Foo:
    # noinspection PyUnusedLocal
    def __init__(self, *u_args, **kw):
        self.__dict__.update(kw)

    def __str__(self):
        return "Hello I'm Foo"

    def __repr__(self):
        return "The Foo"


class DTestAsDict:

    def as_dict(self):
        return dict(me='AsDict')


class DTestProxyDict(dict):
    pass


class DTestProxySet(set):
    pass


class DTestProxyList(list):
    pass


class DTestProxyTuple(tuple):
    pass


class DTestAsDump:

    def as_dump(self):
        return "Simply as_dump said"


complex1 = ['a_string',
            dict(c=Foo()),
            [DTestProxySet((None,)), ]]
complex2 = complex1 + [Foo, str, DTestAsDump()]

expected_ldump = """
      a = 1,
      toto = Hello I'm Foo,"""

expected_complex2_xml = """<?xml version="1.0" ?>
<me>
  <generic_item>a_string</generic_item>
  <generic_item>
    <c>
      <generic_object>
        <overview>Hello I'm Foo</overview>
        <type>{name:s}.Foo</type>
      </generic_object>
    </c>
  </generic_item>
  <generic_item>
    <generic_item>
      <generic_object>
        <overview>{noneset:s}</overview>
        <type>{name:s}.DTestProxySet</type>
      </generic_object>
    </generic_item>
  </generic_item>
  <generic_item>
    <class>{name:s}.Foo</class>
  </generic_item>
  <generic_item>
    <builtin>str</builtin>
  </generic_item>
  <generic_item>
    <generic_object>
      <overview>Simply as_dump said</overview>
      <type>{name:s}.DTestAsDump</type>
    </generic_object>
  </generic_item>
</me>
""".format(name=__name__, noneset=re.sub(r'^<(.*)>$', r'\1',
                                         str(DTestProxySet((None, )))))

# Remove indentation
expected_complex2_xml = ''.join(re.split(r'\n\s*', expected_complex2_xml))


expected_txt_dict = """{me:s}.DTestAsDict::<<
              __dict__:: dict(
                      me = 'AsDict',
                  )
          >>"""

expected_txt_Pdict = """{me:s}.DTestProxyDict::<<
              as_dict:: dict(
                      me = 'AsDict',
                  )
          >>"""

expected_txt_Plist = """{me:s}.DTestProxyList::<<
              as_list:: [1, 2]
          >>"""

expected_txt_Ptuple = """{me:s}.DTestProxyTuple::<<
              as_tuple:: (1, 2)
          >>"""

expected_txt_Pset = """{me:s}.DTestProxySet::<<
              as_set:: set([1])
          >>"""

expected_complex2_txt = """['a_string', dict(
              c = {me:s}.Foo::Hello I'm Foo,
          ), [{me:s}.DTestProxySet::<<
                      as_set:: set([None])
                  >>], {me:s}.Foo, str, {me:s}.DTestAsDump::Simply as_dump said]"""

expected_complex2_oneline = (
    "['a_string', dict(c = Foo::Hello I'm Foo,), " +
    "[DTestProxySet::<<as_set:: set([None])>>], " +
    "{me:s}.Foo, str, DTestAsDump::Simply as_dump said]")


class utDump(TestCase):

    def test_dump_basics(self):
        # Types
        self.assertFalse(dump.is_an_instance(Foo))
        self.assertTrue(dump.is_an_instance(Foo()))

        class FooBis(Foo):
            pass

        self.assertFalse(dump.is_an_instance(FooBis))
        self.assertTrue(dump.is_class(Foo))
        self.assertTrue(dump.is_class(FooBis))
        # Lightdump
        self.assertEqual(dump.lightdump(dict(toto=Foo(), a=1)), expected_ldump)

    def assertJsonableDumper(self, obj, expected):
        jd = JsonableDumper()
        if isinstance(expected, dict):
            self.assertDictEqual(jd.cleandump(obj), expected)
        elif isinstance(expected, list):
            self.assertListEqual(jd.cleandump(obj), expected)
        else:
            self.assertEqual(jd.cleandump(obj), expected)

    def test_dump_json(self):
        # Elementary dumps...
        self.assertJsonableDumper(Foo(), __name__ + ".Foo::Hello I'm Foo")
        self.assertJsonableDumper(Foo, __name__ + ".Foo")
        self.assertJsonableDumper(str, "str")
        self.assertJsonableDumper(1, 1)
        self.assertJsonableDumper("Toto", "Toto")
        self.assertJsonableDumper(DTestAsDict(), dict(me='AsDict'))
        self.assertJsonableDumper(DTestProxyDict(me='AsDict'), dict(me='AsDict'))
        self.assertJsonableDumper(list((1, 2)), [1, 2, ])
        self.assertJsonableDumper(DTestProxyList((1, 2)), [1, 2, ])
        self.assertJsonableDumper((1, 2), [1, 2, ])
        self.assertJsonableDumper(DTestProxyTuple((1, 2)), [1, 2, ])
        self.assertJsonableDumper({1}, [1, ])
        self.assertJsonableDumper(DTestProxySet((1,)), [1, ])
        self.assertJsonableDumper(DTestAsDump(), __name__ + ".DTestAsDump::Simply as_dump said")
        self.assertJsonableDumper(None, "None")
        # Complex dump
        self.assertJsonableDumper(complex1,
                                  ['a_string',
                                   dict(c=__name__ + ".Foo::Hello I'm Foo"),
                                   [["None", ]]
                                   ])
        # In Vortex, an extensive test is carried out in test_import

    def test_dump_xml(self):
        xd = XmlDomDumper()
        xdoc = xd.cleandump(complex2, "me")
        res = ''.join(re.split(r'\n\s*', xdoc.toxml()))
        self.assertEqual(res, expected_complex2_xml)
        # In Vortex, an extensive test is carried out in test_import

    def assertTxtDumper(self, obj, expected):
        td = TxtDumper()
        # print(td.cleandump(obj))
        # Indentation
        self.assertEqual(td._indent(nextline=False), '')
        self.assertEqual(td._indent(nextline=False, level=2), '')
        self.assertEqual(td._indent(), '\n      ')
        self.assertEqual(td._indent(level=1), '\n          ')
        # Other
        self.assertEqual(td.cleandump(obj),
                         td.indent_first * td.indent_space +
                         expected.format(me=__name__))

    def test_dump_txt(self):
        # Elementary dumps...
        self.assertTxtDumper(Foo(), "{me:s}.Foo::Hello I'm Foo")
        self.assertTxtDumper(Foo, "{me:s}.Foo")
        self.assertTxtDumper(str, "str")
        self.assertTxtDumper(1, "1")
        self.assertTxtDumper("Toto", "'Toto'")
        self.assertTxtDumper(DTestAsDict(), expected_txt_dict)
        self.assertTxtDumper(DTestProxyDict(me='AsDict'), expected_txt_Pdict)
        self.assertTxtDumper(list((1, 2)), "[1, 2]")
        self.assertTxtDumper(DTestProxyList((1, 2)), expected_txt_Plist)
        self.assertTxtDumper((1, 2), "(1, 2)")
        self.assertTxtDumper(DTestProxyTuple((1, 2)), expected_txt_Ptuple)
        self.assertTxtDumper({1}, "set([1])")
        self.assertTxtDumper(DTestProxySet((1,)), expected_txt_Pset)
        self.assertTxtDumper(DTestAsDump(),
                             "{me:s}.DTestAsDump::Simply as_dump said")
        self.assertTxtDumper(None, "None")
        # Complex dump
        self.assertTxtDumper(complex2, expected_complex2_txt)

    def test_dump_onelinetxt(self):
        td = OneLineTxtDumper()
        self.assertEqual(td.cleandump(complex2),
                         expected_complex2_oneline.format(me=__name__))


if __name__ == '__main__':
    main(verbosity=2)
