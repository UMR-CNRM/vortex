#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import footprints

from vortex import toolbox
from bronx.stdtypes import date
from bronx.fancies.dispatch import InteractiveDispatcher

import common.util.usepygram


class OpDigger(InteractiveDispatcher):
    """
    On a basis of empirical configuration values, give pertinent information
    about availability of operational resources.
    """

    def cfgsetup(self):
        self._maxterm = 0
        self.expandall(self.cfginfo)

    def expandall(self, data):
        for k, v in data.items():
            if k.endswith('_period'):
                data[k] = date.Period(v)
            elif k.endswith('_term') or k == 'terms':
                data[k] = footprints.util.rangex(v)
                self._maxterm = max(self._maxterm, data[k][-1])
            elif k.startswith('t') and type(v) is list:
                data[k] = [date.Time(x) for x in v]
            elif type(v) is dict:
                self.expandall(v)

    @property
    def maxterm(self):
        return self._maxterm

    def op_maxterm(self, **kw):
        """Exploration depth in hours."""
        return self.maxterm

    def op_vapps(self, **kw):
        """Current vapp/vconf defined in configuration file."""
        return [ vapp + '-' + vconf
                for vapp in self.op_models(**kw)
                for vconf in self.notexcluded(self.cfginfo[vapp])]

    def op_models(self, **kw):
        """Entry points of the configuration file."""
        return self.notexcluded(self.cfginfo.keys())

    def op_cutoffs(self, **kw):
        """Set of defined cutoff for all models."""
        c = set()
        for vapp in self.op_models():
            for vconf in self.notexcluded(self.cfginfo[vapp]):
                c.update(self.notexcluded(self.cfginfo[vapp][vconf].keys()))
        return list(c)

    def op_locations(self, **kw):
        """List of storage location (probably: disk and arch)."""
        return [x.replace('_period', '') for x in self.cfginfo['meta'].keys()]

    def rdelta(self, vapp, vconf, cutoff, hour):
        runs = sorted(self.cfginfo[vapp][vconf][cutoff].keys())
        ipos = runs.index(hour)
        dt = int(runs[ipos-1]) - int(runs[ipos])
        if dt >= 0:
            dt = dt - 24
        return date.Period(abs(dt)*3600)

    def find_date(self, **kw):
        rv = dict()
        for m in kw['model']:
            if '-' in m:
                vapp, vconf = m.split('-')
            else:
                vapp = m
                vconf = self.cfginfo[m]['default']
            if 'remap' in self.cfginfo[vapp]:
                vconf = self.cfginfo[vapp]['remap'].get(vconf, vconf)
            for c in [x for x in kw['cutoff'] if x in self.cfginfo[vapp][vconf]]:
                runs = sorted(self.cfginfo[vapp][vconf][c].keys())
                closest = -1
                for i, v in enumerate(runs):
                    if kw['date'].hour < int(v):
                        closest = i-1
                        break
                xdate = date.Date(kw['date'].ymd + runs[closest])
                delta = kw['date'] - xdate
                while delta.time().hour <= kw['term']:
                    if delta.time().hour in self.cfginfo[vapp][vconf][c][xdate.hh]['terms']:
                        isotime = delta.time().fmthm
                        if isotime not in rv:
                            rv[isotime] = list()
                        for shelf in kw['location']:
                            status = 'ok'
                            start, end = self.cfginfo[vapp][vconf][c][xdate.hh]['t'+shelf]
                            length = start - end
                            length = length.hour * 60 + length.minute
                            extra = length * delta.time().hour / self.cfginfo[vapp][vconf][c][xdate.hh]['terms'][-1]
                            extra = date.Period(extra*60)
                            if kw[shelf] < kw['top'] - xdate:
                                status = 'out'
                            elif kw['top'] < xdate + start + extra:
                                status = 'notyet'
                            rv[isotime].append((vapp, vconf, c, xdate.ymdhm, shelf, status))
                    xdate = xdate - self.rdelta(vapp, vconf, c, xdate.hh)
                    delta = kw['date'] - xdate
        return rv

    def toolbox_setup(self, **kw):
        toolbox.defaults.update(
            rootdir = kw.get('rootdir', '/chaine/mxpt001'),
        )

    def op_guess(self, **kw):
        kw.update(
            top  = date.utcnow(),
            disk = self.cfginfo['meta']['disk_period'],
            arch = self.cfginfo['meta']['arch_period'],
        )
        # Set some default for non-interactive usage
        kw.setdefault('location', self.op_locations())
        kw.setdefault('check', False)
        # Ensure some list-like values
        for opt in ('date', 'model', 'cutoff', 'location'):
            if not isinstance(kw[opt], (list, tuple, set, dict)):
                kw[opt] = (kw[opt],)
        if kw.get('term') is None or kw['term'] < 0:
            kw['term'] = self.maxterm
        return {d.ymdhm: self.find_date(date=d, **kw) for d in kw.pop('date')}

    def op_view(self, **kw):
        return footprints.dump.fulldump(self.op_guess(**kw))

    def getrh(self, vapp, vconf, cutoff, basedate, term, location, kw):
        location = 'inline' if location == 'disk' else 'archive'
        fp = self.cfginfo[vapp][vconf].get('footprint', dict())
        fp.update(
            incore        = True,
            vapp          = vapp,
            vconf         = vconf,
            cutoff        = cutoff,
            date          = basedate,
            term          = term,
            model         = vapp,
            suite         = kw.get('suite', fp.get('suite', 'oper')),
            kind          = kw.get('kind', fp.get('kind', 'historic')),
            namespace     = '[suite].' + location + '.fr',
            metadatacheck = True if location == 'inline' else False,
        )
        return toolbox.rh(**fp)

    def getstnice(self, rst):
        try:
            rst = rst.st_size
        except AttributeError:
            pass
        return str(rst)

    def op_look(self, **kw):
        guess = self.op_guess(**kw)
        self.toolbox_setup(**kw)
        for d in sorted(guess.keys()):
            print(' ' * 3, '*', d)
            for h in sorted(guess[d].keys()):
                print(' ' * 7, '+', h)
                for r in guess[d][h]:
                    print(' ' * 11, '[{0:s}]'.format(', '.join(r)))
                    (vapp, vconf, cutoff, basedate, location, status) = r
                    if status in ('ok', 'notyet'):
                        rh = self.getrh(vapp, vconf, cutoff, basedate, h, location, kw)
                        if rh is not None:
                            rst = '[{0:s}]'.format(self.getstnice(rh.check())) if kw['check'] else ''
                            print(' ' * 11, '-', rh.locate(), rst)

    def op_best(self, **kw):
        guess = self.op_guess(**kw)
        self.toolbox_setup(**kw)
        rbest = dict()
        for d in sorted(guess.keys()):
            for h in sorted(guess[d].keys()):
                if d in rbest:
                    continue
                for r in guess[d][h]:
                    (vapp, vconf, cutoff, basedate, location, status) = r
                    if status in ('ok', 'notyet'):
                        rh = self.getrh(vapp, vconf, cutoff, basedate, h, location, kw)
                        if rh is not None:
                            if rh.check():
                                rbest[d] = dict(description=r, handler=rh, term=h)
                                break
        return [rbest[x] for x in sorted(rbest.keys())]
