#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

"""
utility classes to information on the availability of operational resources.

.. warning:: This module is under heavy development consequently significant
             will be made in future versions. DO NOT USE YET.

"""

from __future__ import absolute_import, print_function, unicode_literals

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex import toolbox
from bronx.stdtypes import date
from bronx.fancies.colors import termcolors as tmc


class Digger(footprints.FootprintBase):
    """
    Some kind of auxilary class for doing real hard work
    according to some contract.
    """

    _abstract  = True
    _collector = ('digger',)
    _footprint = dict(
        info = 'Default digger class.',
        attr = dict(
            mine = dict(),
        ),
    )

    def __init__(self, *args, **kw):
        logger.debug('Abstract digger init %s', self.__class__)
        super(Digger, self).__init__(*args, **kw)
        self.clear_stack()

    def clear_stack(self):
        self._stack = list()

    def delayed_print(self, *args):
        self._stack.append(args)

    @property
    def stack(self):
        return '\n'.join([' '.join(x) for x in self._stack])


class OpDigger(Digger):
    """
    On a basis of empirical configuration values, give pertinent information
    about availability of operational resources.
    """

    _footprint = dict(
        info = 'Digg in the op tables !',
        attr = dict(
            mine = dict(
                values = ['op'],
            ),
        ),
    )

    def get_storage_period(self, vapp, vconf, location, period):
        """Return actual storage period for the specified location."""
        if period is None:
            thisloc = self.cfg.info[vapp][vconf].get('locations', dict())
            if location in thisloc:
                period = thisloc[location]['storage_period']
            else:
                period = self.cfg.defaults['locations'][location]['storage_period']
        return period

    def get_extra_time(self, run, shelf, term):
        start, end = run['t' + shelf]
        length = end - start
        length = length.hour * 60 + length.minute
        lastterm = date.Time(run['terms'][-1])
        extra = length * (term.hour * 60 + term.minute) / (lastterm.hour * 60 + lastterm.minute)
        extra = date.Period(extra * 60)
        return (start, end, extra)

    def find_date(self, **kw):
        """Core function to find a proper reference for a given date."""
        rv = dict()
        for term in [date.Time(x) for x in footprints.util.rangex(0, end=kw['term'].fmthm, step=kw['step']) if x not in kw['notterm']]:
            isotime = term.fmthm
            xdate = kw['date'] - date.Period(term)
            self.cfg.select(date=xdate)
            for model in kw['model']:
                vapp, vconf = self.cfg.get_vapp_vconf(model)
                for cutoff in [x for x in kw['cutoff'] if x in self.cfg.info[vapp][vconf]]:
                    runs = [date.Time(x) for x in self.cfg.info[vapp][vconf][cutoff].keys()]
                    if xdate.time() not in runs:
                        continue
                    xdatehm = xdate.time().fmthm
                    thisrun = self.cfg.info[vapp][vconf][cutoff][xdatehm]
                    if term in [date.Time(x) for x in thisrun['terms']]:
                        if isotime not in rv:
                            rv[isotime] = list()
                        for shelf in kw['location']:
                            status = 'ok'
                            start, end, extra = self.get_extra_time(thisrun, shelf, term)
                            if self.get_storage_period(vapp, vconf, shelf, kw.get(shelf+'_period')) < kw['top'] - xdate:
                                status = 'out'
                            elif kw['top'] < xdate + start + extra:
                                status = 'notyet'
                            rv[isotime].append((vapp, vconf, cutoff, xdate.ymdhm, shelf, status))
        return rv

    def toolbox_setup(self, **kw):
        toolbox.defaults.update(
            rootdir = kw.get('rootdir', '/chaine/mxpt001'),
        )

    def prune_options(self, kw):
        """Remove None values from the given dictionnary of options."""
        for k, v in kw.items():
            if v is None:
                kw.pop(k)

    def candidates(self, **kw):
        # prune pseudo default values
        self.prune_options(kw)
        # Take a stamp just now !
        kw.update(top=date.utcnow())
        # Set some default for non-interactive usage
        kw.setdefault('step', date.Time('01:00'))
        kw.setdefault('location', self.cfg.locations())
        kw.setdefault('notterm', set())
        # Ensure some list-like values
        for opt in ('date', 'model', 'cutoff', 'location', 'notterm'):
            if not isinstance(kw[opt], (list, tuple, set, dict)):
                kw[opt] = (kw[opt],)
        # Result is a date-driven dictionnary
        myguess = dict()
        for thisdate in kw.pop('date'):
            # Switch to current configuration
            self.cfg.select(date=thisdate)
            # Get a fresh light copy because some values may be date-dependent
            thisargs = kw.copy()
            # Set max term for this date
            if thisargs.get('term') is None or thisargs['term'] < 0:
                thisargs['term'] = date.Time(self.cfg.maxterm)
            else:
                thisargs['term'] = date.Time(thisargs['term'])
            myguess[thisdate.ymdhm] = self.find_date(date=thisdate, **thisargs)
        return myguess

    def getrh(self, vapp, vconf, cutoff, basedate, term, location, kw):
        fp = self.cfg.info[vapp][vconf].get('resources', dict()).copy()
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
            namespace     = kw.get('namespace', fp.get('namespace', self.cfg.defaults['locations'][location].get('namespace'))),
            metadatacheck = kw.get('datacheck', fp.get('datacheck', self.cfg.defaults['locations'][location].get('datacheck'))),
        )
        return toolbox.rh(**fp)

    def getstnice(self, rst):
        try:
            rst = rst.st_size
        except AttributeError:
            pass
        return str(rst)

    def lookup(self, **kw):
        """Give a look to the expected candidates for the specified resource."""
        self.prune_options(kw)
        guess = self.candidates(**kw)
        self.toolbox_setup(**kw)
        self.clear_stack()
        for d in sorted(guess.keys()):
            self.delayed_print(' ', tmc.critical('* ' + d))
            for h in sorted(guess[d].keys()):
                self.delayed_print(' ' * 3, tmc.ok('+ ' + h))
                for r in guess[d][h]:
                    self.delayed_print(' ' * 5, '[{0:s}]'.format(', '.join(r)))
                    (vapp, vconf, cutoff, basedate, location, status) = r
                    if status in ('ok', 'notyet'):
                        rh = self.getrh(vapp, vconf, cutoff, basedate, h, location, kw)
                        if rh is not None:
                            rst = '[{0:s}]'.format(self.getstnice(rh.check())) if kw['check'] else ''
                            self.delayed_print(' ' * 5, '-', tmc.warning(rh.locate()), rst)
        return self.stack

    def best(self, **kw):
        """Find the best candidate for an expected resource."""
        self.prune_options(kw)
        guess = self.candidates(**kw)
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
        return rbest

    def ontime(self, **kw):
        """Give a look to the effective time match of the specified resources."""
        self.prune_options(kw)
        self.toolbox_setup(**kw)
        self.clear_stack()
        # Take a stamp just now !
        kw.update(top=date.utcnow())
        # Set some default for non-interactive usage
        kw.setdefault('location', self.cfg.locations())
        # Ensure some list-like values
        for opt in ('date', 'model', 'cutoff', 'location'):
            if not isinstance(kw[opt], (list, tuple, set, dict)):
                kw[opt] = (kw[opt],)
        # Result is a date-driven list
        for thisdate in kw['date']:
            # Switch to current configuration
            self.cfg.select(date=thisdate)
            for model in kw['model']:
                vapp, vconf = self.cfg.get_vapp_vconf(model)
                for cutoff in [x for x in kw['cutoff'] if x in self.cfg.info[vapp][vconf]]:
                    runs = [date.Time(x) for x in self.cfg.info[vapp][vconf][cutoff].keys()]
                    if thisdate.time() not in runs:
                        continue
                    self.delayed_print(' ', tmc.critical('* ' + thisdate.ymdhm))
                    xdatehm = thisdate.time().fmthm
                    thisrun = self.cfg.info[vapp][vconf][cutoff][xdatehm]
                    for term in kw['term']:
                        self.delayed_print(' ' * 3, tmc.ok('+ ' + term.fmthm))
                        for shelf in kw['location']:
                            start, end, extra = self.get_extra_time(thisrun, shelf, term)
                            expected = thisdate + start + extra
                            r = (vapp, vconf, cutoff, shelf, expected.isoformat())
                            self.delayed_print(' ' * 5, '[{0:s}]'.format(', '.join(r)))
                            rh = self.getrh(vapp, vconf, cutoff, thisdate, term, shelf, kw)
                            if rh is not None:
                                rst = ''
                                if kw['check']:
                                    rst = rh.check()
                                    try:
                                        rst = (date.Date(float(rst.st_ctime)) - expected).time().fmthm
                                    except AttributeError:
                                        pass
                                    rst = '[{0:s}]'.format(str(rst))
                                self.delayed_print(' ' * 5, '-', tmc.warning(rh.locate()), rst)
        return self.stack


class NamDigger(Digger):
    """
    Do its best to digg into operationnal namelists.
    """

    _footprint = dict(
        info = 'Digg in the op namelists !',
        attr = dict(
            mine = dict(
                values = ['namelist', 'naml'],
            ),
        ),
    )

    def __init__(self, *args, **kw):
        logger.debug('Abstract nam digger init %s', self.__class__)
        super(NamDigger, self).__init__(*args, **kw)
        self._rh = None
        self._domains = None

    @property
    def rh(self):
        return self._rh

    @property
    def domains(self):
        if not self._domains:
            self._domains = sorted(self.cfg.defaults.get('domains', list()))
        return self._domains

    def set_domains(self, only=None, grep=None, discard=None):
        self._domains = None
        if None in only:
            self._domains = [x for x in self.domains if x not in discard and grep.search(x)]
        else:
            self._domains = [x for x in self.domains if x in only]
        self.apply_domains()

    def load(self, **kw):
        try:
            self._rh = toolbox.rh(**kw)
        except toolbox.VortexToolboxDescError:
            self._rh = None
        if self.rh:
            self.rh.get()
            return '\n'.join((
                repr(self.rh),
                'Resource  : ' + str(self.rh.resource),
                'Provider  : ' + str(self.rh.provider),
                'Container : ' + str(self.rh.container),
            ))
        else:
            return None
        return self._rh.quickview() if self._rh else None

    def cat(self, **kw):
        return self.rh.contents.dumps()

    def blocks(self, **kw):
        return self.rh.contents.keys()

    def apply_domains(self):
        domains = ':'.join(self.domains)
        for block in self.rh.contents.data.values():
            for k in [x for x in block.keys() if x.startswith('CLD')]:
                block[k] = domains

    def save(self, **kw):
        self.rh.save()
        return self.rh.container.actualpath()
