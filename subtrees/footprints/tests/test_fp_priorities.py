from unittest import TestCase, main

from footprints import priorities


class utPriorities(TestCase):

    def test_priorities_basics(self):
        rv = priorities.PrioritySet()
        self.assertIsInstance(rv, priorities.PrioritySet)
        self.assertEqual(len(rv), 0)
        self.assertIsInstance(rv(), tuple)
        self.assertNotIn('debug', rv)

        rv.extend('default', 'toolbox', 'debug')
        self.assertEqual(len(rv), 3)
        self.assertIn('default', rv)
        self.assertIn('toolbox', rv)
        self.assertIn('debug', rv)
        self.assertIsInstance(rv.DEBUG, priorities.PriorityLevel)
        self.assertIs(rv.DEFAULT, rv.level('default'))
        self.assertIs(rv.TOOLBOX, rv.level('toolbox'))
        self.assertIs(rv.DEBUG, rv.level('debug'))

        rv = priorities.PrioritySet(levels=['default', 'toolbox'])
        self.assertIsInstance(rv, priorities.PrioritySet)
        self.assertEqual(len(rv), 2)
        self.assertIn('Default', rv)
        self.assertIsInstance(rv.levels, tuple)
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX'))
        self.assertListEqual([x for x in rv], ['DEFAULT', 'TOOLBOX'])

        rv.extend('debug')
        self.assertEqual(len(rv), 3)
        self.assertIn('DEBUG', rv)
        self.assertIsInstance(rv.DEBUG, priorities.PriorityLevel)
        self.assertGreater(rv.DEBUG, rv.TOOLBOX)
        self.assertEqual(rv.DEFAULT(), 0)
        self.assertEqual(rv.TOOLBOX(), 1)
        self.assertEqual(rv.DEBUG(), 2)
        with self.assertRaises(AttributeError):
            self.assertTrue(rv.DEBUG < 'bof')
        self.assertEqual(rv.DEBUG.as_dump(), "DEBUG (rank=2)")

        rv.reset()
        self.assertEqual(len(rv), 2)
        self.assertNotIn('debug', rv)

        rv.extend('default')
        self.assertEqual(len(rv), 2)
        self.assertTupleEqual(rv.levels, ('TOOLBOX', 'DEFAULT'))

        rv.remove('toolbox')
        self.assertEqual(len(rv), 1)
        self.assertNotIn('toolbox', rv)

        rv.reset()
        rv.remove(rv.TOOLBOX)
        self.assertEqual(len(rv), 1)
        self.assertNotIn('toolbox', rv)

        rv.reset()
        self.assertEqual(len(rv), 2)
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX'))

        rv.TOOLBOX.delete()
        self.assertEqual(len(rv), 1)
        self.assertTupleEqual(rv.levels, ('DEFAULT',))

    def test_priorities_compare(self):
        rv = priorities.PrioritySet(levels=['default', 'toolbox', 'debug'])
        self.assertGreater(rv.DEBUG, rv.TOOLBOX)
        self.assertGreater(rv.DEBUG, 'toolbox')
        self.assertLess(rv.TOOLBOX, rv.DEBUG)
        self.assertLess(rv.DEFAULT, 'debug')
        self.assertGreater(rv.TOOLBOX, rv.DEFAULT)
        self.assertGreater(rv.TOOLBOX, 'default')
        self.assertLess(rv.DEFAULT, rv.TOOLBOX)
        self.assertLess(rv.DEFAULT, 'toolbox')
        self.assertEqual(rv.DEFAULT, 'default')
        self.assertEqual(rv.DEFAULT.rank, 0)
        self.assertEqual(rv.TOOLBOX.rank, 1)
        self.assertEqual(rv.DEBUG.rank, 2)
        self.assertEqual(rv.levelindex('default'), 0)
        self.assertEqual(rv.levelindex('toolbox'), 1)
        self.assertEqual(rv.levelindex('debug'), 2)
        self.assertEqual(rv.levelbyindex(0), rv.DEFAULT)
        self.assertEqual(rv.levelbyindex(1), rv.TOOLBOX)
        self.assertEqual(rv.levelbyindex(2), rv.DEBUG)

        with self.assertRaises(ValueError):
            rv.levelindex('foo')

        rv = priorities.top
        self.assertTrue(rv.NONE < rv.DEFAULT < rv.TOOLBOX < rv.DEBUG)
        self.assertTrue(rv.DEBUG > 'toolbox')
        self.assertTrue(rv.DEFAULT < 'toolbox')
        self.assertIsNone(rv.DEBUG.nextlevel())
        self.assertIsNone(rv.NONE.prevlevel())

    def test_priorities_reorder(self):
        rv = priorities.PrioritySet(levels=['default', 'toolbox', 'debug'])
        self.assertTrue(rv.DEBUG > 'toolbox')

        rv.rerank('toolbox', 1)
        self.assertFalse(rv.DEBUG > 'toolbox')

        rv.rerank('default', 999)
        self.assertFalse(rv.DEBUG > 'default')
        self.assertTupleEqual(rv.levels, ('DEBUG', 'TOOLBOX', 'DEFAULT'))

        rv.DEBUG.top()
        self.assertTrue(rv.DEBUG > 'default')
        self.assertTupleEqual(rv.levels, ('TOOLBOX', 'DEFAULT', 'DEBUG'))

        rv.DEFAULT.bottom()
        self.assertTrue(rv.TOOLBOX > 'default')
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'DEBUG'))

        rv.DEBUG.up()
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'DEBUG'))

        rv.DEFAULT.down()
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'DEBUG'))

        rv.TOOLBOX.up()
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'DEBUG', 'TOOLBOX'))

        rv.reset()
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'DEBUG'))

        rv.TOOLBOX.down()
        self.assertTupleEqual(rv.levels, ('TOOLBOX', 'DEFAULT', 'DEBUG'))

        rv.reset()
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'DEBUG'))

        rv.TOOLBOX.addafter('foo')
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'FOO', 'DEBUG'))

        rv.DEBUG.addafter('top')
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'FOO', 'DEBUG', 'TOP'))

        rv.reset()
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'DEBUG'))

        rv.TOOLBOX.addbefore('foo')
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'FOO', 'TOOLBOX', 'DEBUG'))

        rv.DEFAULT.addbefore('scratch')
        self.assertTupleEqual(rv.levels, ('SCRATCH', 'DEFAULT', 'FOO', 'TOOLBOX', 'DEBUG'))

    def test_priorities_freeze(self):
        rv = priorities.PrioritySet(levels=['default', 'toolbox', 'debug'])
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'DEBUG'))
        self.assertListEqual(rv.freezed(), ['default'])

        rtag = rv.insert(None, after='toolbox')
        self.assertIsNone(rtag)

        rv.insert('hip', after='toolbox')
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'HIP', 'DEBUG'))

        rv.insert('hip', after=rv.TOOLBOX)
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'HIP', 'DEBUG'))

        rv.freeze('hip-added')
        self.assertListEqual(rv.freezed(), ['default', 'hip-added'])

        rv.insert('hop', before='debug')
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'HIP', 'HOP', 'DEBUG'))

        rv.insert('hop', before=rv.DEBUG)
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'HIP', 'HOP', 'DEBUG'))

        rv.freeze('hop-added')
        self.assertListEqual(rv.freezed(), ['default', 'hip-added', 'hop-added'])

        rv.reset()
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'DEBUG'))

        rv.restore('hop-added')
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'HIP', 'HOP', 'DEBUG'))

        rv.remove('hip')
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'HOP', 'DEBUG'))

        rv.restore('hip-added')
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'HIP', 'DEBUG'))
        self.assertTrue(rv.TOOLBOX < rv.HIP < rv.DEBUG)

        with self.assertRaises(ValueError):
            rv.freeze('default')

    def test_priorities_methods(self):
        rv = priorities.top
        self.assertIsInstance(rv, priorities.PrioritySet)

        rv.freeze('original_priorities')

        rv.reset()
        self.assertTupleEqual(rv.levels, ('NONE', 'DEFAULT', 'TOOLBOX', 'DEBUG'))

        priorities.set_after('default', 'hip', 'hop')
        self.assertTupleEqual(rv.levels, ('NONE', 'DEFAULT', 'HIP', 'HOP', 'TOOLBOX', 'DEBUG'))

        rv.reset()
        self.assertTupleEqual(rv.levels, ('NONE', 'DEFAULT', 'TOOLBOX', 'DEBUG'))

        priorities.set_before('toolbox', 'hip', 'hop')
        self.assertTupleEqual(rv.levels, ('NONE', 'DEFAULT', 'HIP', 'HOP', 'TOOLBOX', 'DEBUG'))

        rv.reset()
        self.assertTupleEqual(rv.levels, ('NONE', 'DEFAULT', 'TOOLBOX', 'DEBUG'))

        rv.restore('original_priorities')


if __name__ == '__main__':
    main(verbosity=2)
