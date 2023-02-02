from collections import defaultdict
import gc
from unittest import TestCase, main

from bronx.patterns import observer


class SlurpObserver(observer.Observer):

    def __init__(self):
        self.once_observed = set()
        self.currently_observed = set()
        self.messages = defaultdict(list)

    def newobsitem(self, item, info):
        self.once_observed.add(item.tag)
        self.currently_observed.add(item.tag)
        self.messages[item.tag].append(info)

    def delobsitem(self, item, info):
        if item.tag in self.currently_observed:
            self.messages[item.tag].append(info)
        self.currently_observed.discard(item.tag)

    def updobsitem(self, item, info):
        if item.tag in self.currently_observed:
            self.messages[item.tag].append(info)


class Foo:

    def __init__(self, obsboard, tag):
        self.tag = tag
        self.oboard = obsboard
        self.oboard.notify_new(self, 'Hey guys!')

    def quit(self):
        self.oboard.notify_del(self, 'Bye Bye')

    def talk(self, msg):
        self.oboard.notify_upd(self, msg)


# Tests for footprints observers

class utObservers(TestCase):

    def test_observers_bases(self):
        sec_obs = observer.SecludedObserverBoard()
        self.assertEqual(len(sec_obs.observers()), 0)
        slurper = SlurpObserver()
        slurper2 = SlurpObserver()
        slurper3 = SlurpObserver()
        sec_obs.register(slurper)
        sec_obs.register(slurper2)
        self.assertEqual(len(sec_obs.observed()), 0)
        self.assertEqual(len(sec_obs.observers()), 2)
        a = Foo(sec_obs, tag='a')
        sec_obs.register(slurper3)
        self.assertEqual(len(sec_obs.observers()), 3)
        a.talk("I feel like I'm observed")
        b = Foo(sec_obs, tag='b')
        a.quit()
        del a
        gc.collect()
        # Send something unregistered (it should do no harm)
        c = 2
        sec_obs.notify_upd(c, 'impostor')
        sec_obs.notify_del(c, 'impostor')
        for obs in (slurper, slurper2):
            self.assertSetEqual(obs.once_observed, {'a', 'b'})
            self.assertSetEqual(obs.currently_observed, {'b'})
            self.assertDictEqual(obs.messages,
                                 dict(a=['Hey guys!', "I feel like I'm observed", 'Bye Bye'],
                                      b=['Hey guys!', ]))
        self.assertDictEqual(slurper3.messages,
                             dict(b=['Hey guys!', ]))
        sec_obs.unregister(slurper)
        self.assertEqual(len(sec_obs.observers()), 2)
        b.quit()
        self.assertSetEqual(slurper.currently_observed, {'b'})
        self.assertSetEqual(slurper2.currently_observed, set())
        self.assertDictEqual(slurper.messages,
                             dict(a=['Hey guys!', "I feel like I'm observed", 'Bye Bye'],
                                  b=['Hey guys!', ]))
        self.assertDictEqual(slurper2.messages,
                             dict(a=['Hey guys!', "I feel like I'm observed", 'Bye Bye'],
                                  b=['Hey guys!', 'Bye Bye']))
        self.assertDictEqual(slurper3.messages,
                             dict(b=['Hey guys!', 'Bye Bye']))


if __name__ == '__main__':
    main(verbosity=2)
