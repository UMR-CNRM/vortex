from __future__ import print_function, absolute_import, unicode_literals, division

import unittest

from bronx.fancies.loggers import unittestGlobalLevel
from bronx.stdtypes.date import Date, Time, Period

from vortex.algo.components import AlgoComponentError
from common.algo.oopsroot import OOPSMemberDetectDecoMixin

tloglevel = 'ERROR'


# Fake objects for test purposes only
class FakeResource(object):
    pass


class FakeDResource(object):

    def __init__(self, d):
        self.date = Date(d)


class FakeTResource(object):

    def __init__(self, t, d):
        self.term = Time(t)
        self.date = Date(d)


class FakeProvider(object):
    pass


class FakeMProvider(object):

    def __init__(self, m):
        self.member = m


class FakeContainer(object):

    def exists(self):
        return True


class FakeRh(object):

    def __init__(self, r, p):
        self.resource = r
        self.provider = p
        self.container = FakeContainer()


class FakeSec(object):

    def __init__(self, r, p, stage='get'):
        self.rh = FakeRh(r, p)
        self.stage = stage


@unittestGlobalLevel(tloglevel)
class TestOopsParallel(unittest.TestCase):

    def assert_mdectect(self, members, terms, lagged=False,
                        d_members=None, o_members=None, r_members=None,
                        r_effterms=None,
                        **kwargs):
        md = OOPSMemberDetectDecoMixin._stateless_members_detect
        ms, mds, mos, ts, lms, rms, rts = md(kwargs, Date('2019010106'))
        self.assertEqual(ms, members)
        self.assertEqual(ts, [Time(t) for t in terms])
        self.assertEqual(lms, lagged)
        if d_members is not None:
            self.assertEqual(mds, d_members)
        if o_members is not None:
            self.assertEqual(mos, [None if o is None else Period(o * 3600)
                                   for o in o_members])
        if r_members is not None:
            self.assertEqual(rms, r_members)
        if r_effterms is not None:
            self.assertEqual(rts, r_effterms)

    def assert_mdectect_ko(self, **kwargs):
        md = OOPSMemberDetectDecoMixin._stateless_members_detect
        with self.assertRaises(AlgoComponentError):
            md(kwargs, Date('2019010106'))

    def assert_mdectect_p(self, members, terms, minsize, lagged=False,
                          r_members=None, r_effterms=None,
                          **kwargs):
        md = OOPSMemberDetectDecoMixin._stateless_members_detect
        ms, _, _, ts, lms, rms, rts = md(kwargs, Date('2019010106'),
                                         ensminsize=minsize, utest=True)
        self.assertEqual(ms, members)
        self.assertEqual(ts, [Time(t) for t in terms])
        self.assertEqual(lms, lagged)
        if r_members is not None:
            self.assertEqual(rms, r_members)
        if r_effterms is not None:
            self.assertEqual(rts, r_effterms)

    def test_members_detect_ok(self):
        self.assert_mdectect(
            [], [],
            SurfaceGuess=[FakeSec(FakeResource(), FakeProvider())],
            Guess=[FakeSec(FakeResource(), FakeProvider())],
        )
        self.assert_mdectect(
            [], [],
            SurfaceGuess=[FakeSec(FakeTResource('6:00', '2019010100'),
                                  FakeProvider())],
            Guess=[FakeSec(FakeTResource('6:00', '2019010100'),
                           FakeMProvider(0))],
        )
        self.assert_mdectect(
            [0, 1], [],
            d_members=[None, None],
            o_members=[None, None],
            r_members=['Guess', 'ModelState'],
            SurfaceGuess=[FakeSec(FakeResource(), FakeProvider())],
            Guess=[FakeSec(FakeResource(),
                           FakeMProvider(0)),
                   FakeSec(FakeResource(),
                           FakeMProvider(1))],
            ModelState=[FakeSec(FakeResource(),
                                FakeMProvider(0)),
                        FakeSec(FakeResource(),
                                FakeMProvider(1))],
        )
        self.assert_mdectect(
            [0, 1], [0, ],
            r_members=['Guess', 'ModelState'],
            r_effterms=['Guess', 'ModelState'],
            SurfaceGuess=[FakeSec(FakeResource(), FakeProvider())],
            Guess=[FakeSec(FakeTResource('6:00', '2019010100'),
                           FakeMProvider(0)),
                   FakeSec(FakeTResource('6:00', '2019010100'),
                           FakeMProvider(1))],
            ModelState=[FakeSec(FakeTResource('6:00', '2019010100'),
                                FakeMProvider(0)),
                        FakeSec(FakeTResource('6:00', '2019010100'),
                                FakeMProvider(1))],
        )
        self.assert_mdectect(
            [0, 1], [],
            r_members=['Guess', 'ModelState'],
            d_members=['2019010100', '2019010100'],
            SurfaceGuess=[FakeSec(FakeResource(), FakeProvider())],
            Guess=[FakeSec(FakeTResource('6:00', '2019010100'),
                           FakeMProvider(0)),
                   FakeSec(FakeTResource('6:00', '2019010100'),
                           FakeMProvider(1))],
            ModelState=[FakeSec(FakeTResource('9:00', '2019010100'),
                                FakeMProvider(0)),
                        FakeSec(FakeTResource('9:00', '2019010100'),
                                FakeMProvider(1))],
        )
        self.assert_mdectect(
            [0, 0], [],
            lagged=True,
            r_members=['Guess', 'ModelState'],
            d_members=['2019010100', '2019010106'],
            o_members=[6, 0],
            SurfaceGuess=[FakeSec(FakeResource(), FakeProvider())],
            Guess=[FakeSec(FakeTResource('6:00', '2019010106'),
                           FakeMProvider(0)),
                   FakeSec(FakeTResource('12:00', '2019010100'),
                           FakeMProvider(0))],
            ModelState=[FakeSec(FakeTResource('9:00', '2019010106'),
                                FakeMProvider(0)),
                        FakeSec(FakeTResource('15:00', '2019010100'),
                                FakeMProvider(0))],
        )
        self.assert_mdectect(
            [0, 1], [0, ],
            r_members=['Guess', 'ModelState'],
            r_effterms=['ModelState'],
            SurfaceGuess=[FakeSec(FakeResource(), FakeProvider())],
            Guess=[FakeSec(FakeDResource('2019010100'),
                           FakeMProvider(0)),
                   FakeSec(FakeDResource('2019010100'),
                           FakeMProvider(1))],
            ModelState=[FakeSec(FakeTResource('6:00', '2019010100'),
                                FakeMProvider(0)),
                        FakeSec(FakeTResource('6:00', '2019010100'),
                                FakeMProvider(1))],
        )
        self.assert_mdectect(
            [0, 0], [6, ],
            lagged=True,
            r_members=['Guess', 'ModelState'],
            r_effterms=['ModelState'],
            SurfaceGuess=[FakeSec(FakeResource(), FakeProvider())],
            Guess=[FakeSec(FakeDResource('2019010106'),
                           FakeMProvider(0)),
                   FakeSec(FakeDResource('2019010100'),
                           FakeMProvider(0))],
            ModelState=[FakeSec(FakeTResource('6:00', '2019010106'),
                                FakeMProvider(0)),
                        FakeSec(FakeTResource('12:00', '2019010100'),
                                FakeMProvider(0))],
        )
        self.assert_mdectect(
            [0, 1], [0, ],
            r_members=['EnsembleModelState'],
            r_effterms=['EnsembleModelState'],
            SurfaceGuess=[FakeSec(FakeResource(), FakeProvider())],
            Guess=[FakeSec(FakeTResource('6:00', '2019010100'),
                           FakeProvider()),
                   FakeSec(FakeTResource('9:00', '2019010100'),
                           FakeProvider())],
            EnsembleModelState=[FakeSec(FakeTResource('6:00', '2019010100'),
                                        FakeMProvider(0)),
                                FakeSec(FakeTResource('6:00', '2019010100'),
                                        FakeMProvider(1))],
        )

        what = dict(
            Guess=[FakeSec(FakeTResource('6:00', '2019010100'),
                           FakeMProvider(1)),
                   FakeSec(FakeTResource('9:00', '2019010100'),
                           FakeMProvider(1)),
                   FakeSec(FakeTResource('6:00', '2019010100'),
                           FakeMProvider(3)),
                   FakeSec(FakeTResource('9:00', '2019010100'),
                           FakeMProvider(3))],
            ModelState=[FakeSec(FakeTResource('6:00', '2019010100'),
                                FakeMProvider(1)),
                        FakeSec(FakeTResource('9:00', '2019010100'),
                                FakeMProvider(1)),
                        FakeSec(FakeTResource('6:00', '2019010100'),
                                FakeMProvider(3)),
                        FakeSec(FakeTResource('9:00', '2019010100'),
                                FakeMProvider(3))], )
        self.assert_mdectect(
            [1, 3], [0, 3],
            r_members=['Guess', 'ModelState'],
            r_effterms=['Guess', 'ModelState'],
            SurfaceGuess=[FakeSec(FakeResource(), FakeProvider())],
            ** what
        )
        self.assert_mdectect(
            [1, 3], [0, 3],
            r_members=['Guess', 'ModelState'],
            r_effterms=['Guess', 'ModelState'],
            SurfaceGuess=[FakeSec(FakeTResource('24:00', '2019010100'), FakeMProvider(1))],
            ** what
        )
        self.assert_mdectect(
            [1, 3], [0, 3],
            r_members=['Guess', 'ModelState'],
            r_effterms=['Guess', 'ModelState'],
            SurfaceGuess=[FakeSec(FakeTResource('6:00', '2019010100'), FakeProvider()),
                          FakeSec(FakeTResource('9:00', '2019010100'), FakeProvider()), ],
            ** what
        )
        self.assert_mdectect(
            [1, 3], [0, 3],
            r_members=['Guess', 'ModelState', 'SurfaceGuess'],
            r_effterms=['Guess', 'ModelState'],
            SurfaceGuess=[FakeSec(FakeTResource('6:00', '2019010100'),
                                  FakeMProvider(1)),
                          FakeSec(FakeTResource('6:00', '2019010100'),
                                  FakeMProvider(3))],
            ** what
        )

    def test_members_detect_ko(self):
        # For a given role, inconsistent list of terms across members
        self.assert_mdectect_ko(
            SurfaceGuess=[FakeSec(FakeResource(), FakeProvider())],
            Guess=[FakeSec(FakeTResource('6:00', '2019010100'),
                           FakeMProvider(1)),
                   FakeSec(FakeTResource('9:00', '2019010100'),
                           FakeMProvider(2))],
            ModelState=[FakeSec(FakeTResource('9:00', '2019010100'),
                                FakeMProvider(1)),
                        FakeSec(FakeTResource('9:00', '2019010100'),
                                FakeMProvider(2))],
        )
        mwhat = dict(
            ModelState=[FakeSec(FakeTResource('6:00', '2019010100'),
                                FakeMProvider(1)),
                        FakeSec(FakeTResource('9:00', '2019010100'),
                                FakeMProvider(1)),
                        FakeSec(FakeTResource('6:00', '2019010100'),
                                FakeMProvider(3)),
                        FakeSec(FakeTResource('9:00', '2019010100'),
                                FakeMProvider(3))], )
        # Inconsistent multiple terms across roles
        self.assert_mdectect_ko(
            SurfaceGuess=[FakeSec(FakeResource(), FakeProvider())],
            Guess=[FakeSec(FakeTResource('6:00', '2019010100'),
                           FakeMProvider(1)),
                   FakeSec(FakeTResource('12:00', '2019010100'),
                           FakeMProvider(1)),
                   FakeSec(FakeTResource('6:00', '2019010100'),
                           FakeMProvider(3)),
                   FakeSec(FakeTResource('12:00', '2019010100'),
                           FakeMProvider(3))],
            ** mwhat
        )
        # Inconsistent list of members for Guess
        self.assert_mdectect_ko(
            SurfaceGuess=[FakeSec(FakeResource(), FakeProvider())],
            Guess=[FakeSec(FakeTResource('6:00', '2019010100'),
                           FakeMProvider(1)),
                   FakeSec(FakeTResource('6:00', '2019010100'),
                           FakeMProvider(3)),
                   FakeSec(FakeTResource('9:00', '2019010100'),
                           FakeMProvider(3))],
            ** mwhat
        )
        # Inconsistent list of members across roles
        self.assert_mdectect_ko(
            SurfaceGuess=[FakeSec(FakeResource(), FakeProvider())],
            Guess=[FakeSec(FakeTResource('6:00', '2019010100'),
                           FakeMProvider(1)),
                   FakeSec(FakeTResource('9:00', '2019010100'),
                           FakeMProvider(1)),
                   FakeSec(FakeTResource('6:00', '2019010100'),
                           FakeMProvider(2)),
                   FakeSec(FakeTResource('9:00', '2019010100'),
                           FakeMProvider(2))],
            ** mwhat
        )
        self.assert_mdectect_ko(
            SurfaceGuess=[FakeSec(FakeResource(), FakeProvider())],
            Guess=[FakeSec(FakeTResource('6:00', '2019010106'),
                           FakeMProvider(1)),
                   FakeSec(FakeTResource('9:00', '2019010106'),
                           FakeMProvider(1)),
                   FakeSec(FakeTResource('6:00', '2019010100'),
                           FakeMProvider(2)),
                   FakeSec(FakeTResource('9:00', '2019010100'),
                           FakeMProvider(2))],
            ** mwhat
        )

    def test_members_detect_failing(self):
        what = dict(
            Guess=[FakeSec(FakeTResource('6:00', '2019010100'),
                           FakeMProvider(1)),
                   FakeSec(FakeTResource('9:00', '2019010100'),
                           FakeMProvider(1)),
                   FakeSec(FakeTResource('6:00', '2019010100'),
                           FakeMProvider(3)),
                   FakeSec(FakeTResource('9:00', '2019010100'),
                           FakeMProvider(3), stage='void')],
            ModelState=[FakeSec(FakeTResource('6:00', '2019010100'),
                                FakeMProvider(1)),
                        FakeSec(FakeTResource('9:00', '2019010100'),
                                FakeMProvider(1)),
                        FakeSec(FakeTResource('6:00', '2019010100'),
                                FakeMProvider(3)),
                        FakeSec(FakeTResource('9:00', '2019010100'),
                                FakeMProvider(3))], )
        self.assert_mdectect_p([1, ], [0, 3], 1,
                               r_members=['Guess', 'ModelState'],
                               r_effterms=['Guess', 'ModelState'],
                               SurfaceGuess=[FakeSec(FakeResource(), FakeProvider())],
                               **what)
        self.assert_mdectect_p([], [0, 3], 0,
                               r_members=['Guess', 'ModelState', 'SurfaceGuess'],
                               r_effterms=['Guess', 'ModelState'],
                               SurfaceGuess=[FakeSec(FakeDResource('2019010100'), FakeMProvider(1),
                                                     stage='void'),
                                             FakeSec(FakeDResource('2019010100'), FakeMProvider(3)), ],
                               **what)
        for minsize in (2, None):
            with self.assertRaises(AlgoComponentError):
                self.assert_mdectect_p([1, ], [0, 3], minsize,
                                       SurfaceGuess=[FakeSec(FakeResource(), FakeProvider())],
                                       **what)


if __name__ == "__main__":
    unittest.main(verbosity=2)
