import json
from unittest import TestCase, main

from bronx.stdtypes.date import Date
import bronx.stdtypes.xtemplates as xtpl
import bronx.syntax.minieval as minie


JSON_TEST = """{
    "logging": {
        "categories": "Trace,Info, Debug, Warning, Error"
    },
    "variables": {
        "variables": "0"
    },
    "expver": "OOPS",
    "ensemble": [
        {
            "state": { "__bronx_tpl_engine__": "loop",
                       "__loopiterator__": "members",
                       "__loopvariables__": "member",
                       "__body__": {
                            "namelist": "{{'naml_write_dx_m{:03d}'.format(member)}}",
                            "ifile": "0",
                            "expver": "unused",
                            "filename": "{{'ICMSHM{:03d}+0000'.format(member)}}",
                            "physics": {
                                "__bronx_tpl_engine__": "loop",
                               "__loopiterator__": "physics[member]",
                               "__loopvariables__": "physic",
                               "__body__": "{{physic + 1}}",
                               "__body_last__": "{{physic + 100}}"
                            }
                     },
            "inflation": 1.0,
            "variables": "1",
            "members": "{{len(members)}}"
            }
        }
    ],
    "state": {
        "date": "{{now.subPT3H.ymdh}}",
        "ifile": "0",
        "variables": "0",
        "expver": "OOPS"
    },
    "linear_variables": {
        "variables": "1"
    },
    "window_length": "PT6H",
    "Jb": {
        "date": "{{now.ymdh}}",
        "namelist": "naml_bmatrix",
        "covariance": "static"
    }
}"""

JSON_TEST_REF = {
    'Jb': {'covariance': 'static',
           'date': '2019010100',
           'namelist': 'naml_bmatrix'},
    'ensemble': [{'state': [{'expver': 'unused',
                             'filename': 'ICMSHM000+0000',
                             'ifile': '0',
                             'namelist': 'naml_write_dx_m000',
                             'physics': [2, 3, 103]},
                            {'expver': 'unused',
                             'filename': 'ICMSHM001+0000',
                             'ifile': '0',
                             'namelist': 'naml_write_dx_m001',
                             'physics': [11, 12, 112]}]}],
    'expver': 'OOPS',
    'linear_variables': {'variables': '1'},
    'logging': {'categories': 'Trace,Info, Debug, Warning, Error'},
    'state': {'date': '2018123121',
              'expver': 'OOPS',
              'ifile': '0',
              'variables': '0'},
    'variables': {'variables': '0'},
    'window_length': 'PT6H'}


class UtXTemplates(TestCase):

    def assert_render(self, tpl, dataout, **kwvars):
        dt = xtpl.DefaultTemplate(tpl)
        self.assertEqual(dt.render(** kwvars), dataout)

    def test_basics(self):
        # Do nothing...
        for cstr in ('moi', 'm{{fgtp}}oi', '{{moi}'):
            a = dict(a=1, b=[1, 2, 3], c=cstr)
            self.assert_render(a, a)
        # Substitution...
        self.assert_render(dict(a=1, b=[1, 2, 3], c='{{member}}'),
                           dict(a=1, b=[1, 2, 3], c=2),
                           member=2)
        self.assert_render(dict(a=1, b=[1, '{{member}}', 3], c='{{member}}'),
                           dict(a=1, b=[1, 2, 3], c=2),
                           member=2)
        self.assert_render({'a': 1, '{{member}}': [1, '{{member}}', 3], 'c': '{{member}}'},
                           {'a': 1, 2: [1, 2, 3], 'c': 2},
                           member=2)
        self.assert_render(dict(a=1, b=[1, 2, 3], c='{{len(members)}}'),
                           dict(a=1, b=[1, 2, 3], c=10),
                           members=list(range(0, 10)))
        self.assert_render(dict(a=1, b=[1, 2, 3],
                                c=[1, '{{",".join(["mb{:02d}".format(m) for m in sorted(members)])}}']),
                           dict(a=1, b=[1, 2, 3], c=[1, 'mb00,mb01,mb02,mb03']),
                           members=[0, 2, 3, 1])

    def assert_loop_error(self, tpl, **kwargs):
        dt = xtpl.DefaultTemplate(tpl)
        with self.assertRaises(xtpl.TemplateLoopRenderingError):
            dt.render(**kwargs)

    def assert_sls_error(self, tpl, **kwargs):
        dt = xtpl.DefaultTemplate(tpl)
        with self.assertRaises(minie.SingleLineStatementError):
            dt.render(**kwargs)

    def test_engine(self):
        # A fake one
        dt = xtpl.DefaultTemplate([dict(__bronx_tpl_engine__='gruik')])
        with self.assertRaises(xtpl.TemplateRenderingError):
            dt.render()
        # Loop errors
        self.assert_loop_error(dict(__bronx_tpl_engine__='loop'))
        self.assert_loop_error(dict(__bronx_tpl_engine__='loop',
                                    __loopiterator__='[1, 2]'))
        self.assert_loop_error(dict(__bronx_tpl_engine__='loop',
                                    __loopiterator__='[1, 2]',
                                    __loopvariables__='i',))
        self.assert_loop_error(dict(__bronx_tpl_engine__='loop',
                                    __loopiterator__='[1, 2]',
                                    __loopvariables__='i',
                                    __body__='{{i + 100}}',
                                    __extra_vars__='gruik'))
        # SLS Errors
        self.assert_sls_error(dict(__bronx_tpl_engine__='loop',
                                   __loopiterator__='[1, 2]',
                                   __loopvariables__='i',
                                   __body__='{{i + 100}}',
                                   __extra_vars__=dict(autre='toto')))    # No
        self.assert_sls_error(dict(__bronx_tpl_engine__='loop',
                                   __loopiterator__='[1, 2]',
                                   __loopvariables__='i',
                                   __body__='{{coucou + 100}}',  # No
                                   __extra_vars__=dict(autre='i % 2')))
        self.assert_sls_error(dict(__bronx_tpl_engine__='loop',
                                   __loopiterator__='[1, 2] + "1"',  # Not Allowed
                                   __loopvariables__='i',
                                   __body__='{{i + 100}}',
                                   __extra_vars__=dict(autre='i % 2')))
        # Basic expansion
        self.assert_render(dict(__bronx_tpl_engine__='loop',
                                __loopiterator__='[1, 2]',
                                __loopvariables__='i',
                                __body__='{{i + 100}}', ),
                           [101, 102])
        # Various atributes
        self.assert_render(dict(__bronx_tpl_engine__='loop',
                                __loopiterator__='[1, 2, 3]',
                                __loopvariables__='i',
                                __body__='{{i + 100}}',
                                __body_first__='{{i}}',
                                __body_last__='{{i + 200}}',
                                ),
                           [1, 102, 203])
        self.assert_render(dict(__bronx_tpl_engine__='loop',
                                __loopiterator__='[1, 2, 3]',
                                __loopvariables__='i',
                                __body__='{{u"i1={:02d} and toto={:d}".format(i + 1, toto)}}',
                                __extra_vars__=dict(toto='i % 2')
                                ),
                           ["i1=02 and toto=1", "i1=03 and toto=0", "i1=04 and toto=1"])
        # External attributes + several loop variables
        self.assert_render([dict(__bronx_tpl_engine__='loop',
                                 __loopiterator__='zip(members, ["mb{:02d}".format(m) for m in members])',
                                 __loopvariables__='m, mstr',
                                 __body__=dict(member='{{m}}', mnext='{{m_next}}', block="{{mstr}}")
                                 ),
                            '{{"This is great -> {!s}".format(a)}}'],
                           [[dict(member=0, mnext=1, block='mb00'),
                             dict(member=1, mnext=2, block='mb01'),
                             dict(member=2, mnext=None, block='mb02')],
                            'This is great -> 1'],
                           members=[0, 1, 2], a=1)

    def test_jsonref(self):
        tpl = json.loads(JSON_TEST)
        dt = xtpl.DefaultTemplate(tpl)
        self.assertEqual(dt.render(now=Date(2019, 1, 1, 0),
                                   members=[0, 1],
                                   physics={0: [1, 2, 3], 1: [10, 11, 12]}),
                         JSON_TEST_REF)


if __name__ == '__main__':
    main(verbosity=2)
