import copy
from unittest import TestCase, main

from bronx.patterns import getbytag


class utGetByTag(TestCase):

    def test_getbytag_basics(self):

        class Tag0(getbytag.GetByTag):
            pass

        class Tag1(Tag0):
            pass

        class Tag2(Tag0):
            _tag_topcls = False

        # topcls or not...
        a = Tag0()
        b = Tag0()
        self.assertIs(a, b)
        self.assertEqual(a.tag, 'default')
        b = Tag1()
        self.assertIsNot(a, b)
        b = Tag2()
        self.assertIs(a, b)
        # With a customized tag
        b = Tag0(tag='truc')
        self.assertIsNot(a, b)
        c = Tag0('truc')
        self.assertIs(b, c)
        # Force creation
        c = Tag0(tag='truc', new=True)
        self.assertIsNot(a, b)
        # Some of the class methods
        self.assertSequenceEqual(Tag0.tag_keys(), ['default', 'truc'])
        self.assertSetEqual(set(Tag0.tag_values()), {a, c})
        self.assertSetEqual(set(Tag0.tag_items()), {('default', a), ('truc', c)})
        self.assertSetEqual(set(Tag0.tag_classes()), {Tag0, Tag2})
        # Ugly copies
        self.assertIs(copy.copy(a), a)
        self.assertIs(copy.deepcopy(a), a)
        # The end
        Tag0.tag_clear()
        self.assertListEqual(Tag0.tag_values(), [])

    def test_getbytag_focus(self):

        class Tag0(getbytag.GetByTag):

            def __init__(self):
                self.flag = 'bare'

            def focus_loose_hook(self):
                super().focus_loose_hook()
                self.flag = 'sleeping'

            def focus_gain_hook(self):
                super().focus_gain_hook()
                self.flag = 'focused'

            def focus_gain_allow(self):
                super().focus_gain_allow()
                if self.tag == 'third':
                    raise RuntimeError('No way I will get focus')

        a = Tag0('first')
        b = Tag0('second')
        c = Tag0('third')

        for o in (a, b, c):
            self.assertEqual(o.flag, 'bare')
        # a
        a.catch_focus()
        self.assertEqual(a.flag, 'focused')
        self.assertTrue(a.has_focus())
        self.assertEqual(Tag0.tag_focus(), 'first')
        for o in (b, c):
            self.assertEqual(o.flag, 'bare')
            self.assertFalse(o.has_focus())
        # b
        Tag0.set_focus(b)
        self.assertEqual(a.flag, 'sleeping')
        self.assertFalse(a.has_focus())
        self.assertEqual(b.flag, 'focused')
        self.assertTrue(b.has_focus())
        # c
        with self.assertRaises(RuntimeError):
            # c should never be allowed to get the focus
            c.catch_focus()
        # As result nothing has changed...
        self.assertEqual(b.flag, 'focused')
        self.assertTrue(b.has_focus())
        self.assertEqual(c.flag, 'bare')


if __name__ == '__main__':
    main(verbosity=2)
