from unittest import TestCase, main

import footprints
from footprints import doc


def autofmt(t):
    tname = (t.__module__ + '.' if not t.__module__.startswith('__') else '')
    return tname + t.__name__


expected_doc_v1 = """

    .. note:: This class is managed by footprint.

         * info: Some nice stuff
         * priority: PriorityLevel::DEFAULT (rank=1)

       Automatic parameters from the footprint:

         * **stuff1** (:class:`{:s}`) - rxx - This is stuff1

           * Values: set(['titi'])
           * Remap: dict(toto = 'titi',)

         * **stuff2** (:class:`{:s}`) - rxx - Not documented, sorry.

           * Optional. Default is 'foo'.


       Aliases of some parameters:

         * **arg1** is an alias of stuff1.
""".format(autofmt(str), autofmt(float))


class utDoc(TestCase):

    def setUp(self):
        self.fp = footprints.Footprint(
            attr=dict(
                stuff1=dict(
                    values=['titi', ],
                    info='This is stuff1',
                    alias=('arg1',),
                    remap=dict(toto='titi')
                ),
                stuff2=dict(
                    type=float,
                    optional=True,
                    default='foo',
                    doc_zorder=-50
                ),
            ),
            info='Some nice stuff'
        )

    def test_doc_slurp(self):
        self.assertEqual("\n".join([line.rstrip(" ")
                                    for line in doc.format_docstring(self.fp, 2).split("\n")]),
                         expected_doc_v1)


if __name__ == '__main__':
    main(verbosity=2)
