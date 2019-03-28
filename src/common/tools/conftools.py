#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Conftools are small objects that can be instantiated from an application's
configuration file.

They might be used when some complex calculations are needed to establish the
tasks configuration.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import six
import collections
import functools

from bronx.fancies import loggers
from bronx.stdtypes.date import Date, Time, Period, Month
from footprints.stdtypes import FPDict, FPList
from footprints.util import rangex
import footprints

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class ConfTool(footprints.FootprintBase):
    """Abstract class for conftools objects."""

    _abstract = True
    _collector = ('conftool',)
    _footprint = dict(
        info = 'Abstract Conf/Weird Tool',
        attr = dict(
            kind = dict(),
        )
    )


#: Holds coupling's data for a particular cutoff/hour
CouplingInfos = collections.namedtuple('CouplingInfos',
                                       ('base', 'dayoff', 'cutoff', 'vapp', 'vconf', 'xpid', 'model', 'steps')
                                       )


class CouplingOffsetConfError(Exception):
    """Abstract exception raise by :class:`CouplingOffsetConfTool` objects."""
    pass


class CouplingOffsetConfPrepareError(CouplingOffsetConfError):
    """Exception raised when an error occurs during coupling data calculations."""

    def __init__(self, fmtk):
        msg = 'It is useless to compute coupling for: {}.'.format(fmtk)
        super(CouplingOffsetConfPrepareError, self).__init__(msg)


class CouplingOffsetConfRefillError(CouplingOffsetConfError):
    """Exception raised when an orror occurs during refill."""

    def __init__(self, fmtk, hh=None):
        msg = 'It is useless to compute a refill for: {}'.format(fmtk)
        if hh is None:
            msg += '.'
        else:
            msg += ' at HH={!s}.'.format(hh)
        super(CouplingOffsetConfRefillError, self).__init__(msg)


class CouplingOffsetConfTool(ConfTool):
    """Conf tool that do all sorts of computations for coupling."""

    _footprint = dict(
        info = 'Conf tool that do all sorts of computations for coupling',
        attr = dict(
            kind = dict(
                values= ['couplingoffset', ],
            ),
            cplhhlist = dict(
                info = ('The list of cutoff and hours for this application. '
                        'If omitted, all entries of the **cplhhbase** attribute are used. ' +
                        "(e.g ``{'assim':[0, 6, 12, 18], 'production':[0, ]}``)"),
                type = FPDict,
                optional = True,
            ),
            cplhhbase = dict(
                info = ('For a given cutoff and hour, gives the base hour to couple to. ' +
                        "(e.g ``{'assim':{0:0, 6:6, 12:12, 18:18}, 'production':{0:18}}``)."),
                type = FPDict,
            ),
            cpldayoff = dict(
                info = ('For a given cutoff and hour, gives an offset in days. 0 by default. ' +
                        "(e.g ``{'assim':{'default':0}, 'production':{'default':1}}``)."),
                type = FPDict,
                optional = True,
            ),
            cplcutoff = dict(
                info = 'For a given cutoff and hour, gives the base cutoff to couple to.',
                type = FPDict,
            ),
            cplvapp = dict(
                info = 'For a given cutoff and hour, gives the base vapp to couple to.',
                type = FPDict,
            ),
            cplvconf = dict(
                info = 'For a given cutoff and hour, gives the base vconf to couple to.',
                type = FPDict,
            ),
            cplxpid = dict(
                info = 'For a given cutoff and hour, gives the experiment ID to couple to.',
                type = FPDict,
                optional = True,
            ),
            cplmodel = dict(
                info = 'For a given cutoff and hour, gives the base model to couple to.',
                type = FPDict,
                optional = True,
            ),
            cplsteps = dict(
                info = 'For a given cutoff and hour, gives then list of requested terms.',
                type = FPDict,
            ),
            refill_cutoff = dict(
                values = ['assim', 'production', 'all'],
                info = 'By default, what is the cutoff name of the refill task.',
                optional = True,
                default = 'assim',
            ),
            compute_on_refill = dict(
                info = 'Is it necessary to compute coupling files for the refilling cutoff ?',
                optional = True,
                default = True,
                type = bool,
            ),
            isolated_refill = dict(
                info = 'Are the refill tasks exclusive with prepare tasks ?',
                optional = True,
                default = True,
                type = bool,
            ),
            verbose = dict(
                info = 'When the object is created, print a summary.',
                type = bool,
                optional = True,
                default = True,
            ),
        )
    )

    _DFLT_KEY = 'default'

    def __init__(self, *kargs, **kwargs):
        super(CouplingOffsetConfTool, self).__init__(*kargs, **kwargs)

        # A dictionary summarising the base HH supported by this configuration tool
        # ex: dict(assim=set([0, 1 , 2, ...]), production=set([0, 6,...])
        self._target_hhs = collections.defaultdict(set)
        if self.cplhhlist is None:
            t_hhbase = collections.defaultdict(dict)
            for c, cv in self.cplhhbase.items():
                for h, v in [(Time(lh), Time(lv)) for lh, lv in cv.items()]:
                    t_hhbase[c][h] = v
                    self._target_hhs[c].add(h)
        else:
            for c, clist in self.cplhhlist.items():
                if not isinstance(clist, (tuple, list)):
                    clist = [clist, ]
                self._target_hhs[c].update([Time(h) for h in clist])
            t_hhbase = self._reshape_inputs(self.cplhhbase, value_reclass=Time)

        # Consistency checks and array reshaping
        t_dayoff = self._reshape_inputs(self.cpldayoff, class_default=0)
        t_cutoff = self._reshape_inputs(self.cplcutoff)
        t_vapp = self._reshape_inputs(self.cplvapp)
        t_vconf = self._reshape_inputs(self.cplvconf)
        t_steps = self._reshape_inputs(self.cplsteps)
        if self.cplmodel is None:
            t_model = t_vapp
        else:
            t_model = self._reshape_inputs(self.cplmodel)
        t_xpid = self._reshape_inputs(self.cplxpid, class_default='')

        # Build the dictionary of CouplingInfos objects
        self._cpl_data = collections.defaultdict(dict)
        for c, cv in t_hhbase.items():
            self._cpl_data[c] = {hh: CouplingInfos(cv[hh], int(t_dayoff[c][hh]),
                                                   t_cutoff[c][hh], t_vapp[c][hh],
                                                   t_vconf[c][hh], t_xpid[c][hh],
                                                   t_model[c][hh],
                                                   rangex(t_steps[c][hh]))
                                 for hh in cv.keys()}

        # Pre-compute the prepare terms
        self._prepare_terms_map = self._compute_prepare_terms()
        if self.verbose:
            print()
            print('#### Coupling configuration tool initialised ####')
            print('**** Coupling tasks terms map:')
            print('{:s}  :  {:s}'.format(self._cpl_fmtkey(('HH', 'VAPP', 'VCONF', 'XPID', 'MODEL', 'CUTOFF')),
                                         'Computed Terms'))
            for k in sorted(self._prepare_terms_map.keys()):
                print('{:s}  :  {:s}'.format(self._cpl_fmtkey(k),
                                             ' '.join([six.text_type(t.hour)
                                                       for t in self._prepare_terms_map[k]
                                                       ])
                                             )
                      )

        # Pre-compute the default refill_map
        self._refill_terms_map = dict()
        self._refill_terms_map[self.refill_cutoff] = self._compute_refill_terms(self.refill_cutoff,
                                                                                self.compute_on_refill,
                                                                                self.isolated_refill)
        if self.verbose:
            print('**** Refill tasks activation map (default refill_cutoff is: {:s}):'.format(self.refill_cutoff))
            print('{:s}  :  {:s}'.format(self._rtask_fmtkey(('VAPP', 'VCONF', 'XPID', 'MODEL', 'CUTOFF')),
                                         'Active hours'))
            for k in sorted(self._refill_terms_map[self.refill_cutoff].keys()):
                vdict = self._refill_terms_map[self.refill_cutoff][k]
                print('{:s}  :  {:s}'.format(self._rtask_fmtkey(k),
                                             ' '.join([six.text_type(t.hour) for t in sorted(vdict.keys())])))
            print()

    @property
    def target_hhs(self):
        return self. _target_hhs

    def _reshape_inputs(self, input_dict, class_default=None, value_reclass=lambda x: x):
        """Deal with default values, check dictionaries and convert keys to Time objects."""
        # Convert keys to time objects
        r_dict = dict()
        if input_dict is not None:
            for c, cv in input_dict.items():
                if isinstance(cv, dict):
                    r_dict[c] = dict()
                    for h, v in cv.items():
                        if h != self._DFLT_KEY:
                            r_dict[c][Time(h)] = value_reclass(v)
                        else:
                            r_dict[c][h] = value_reclass(v)
                else:
                    r_dict[c] = cv

        # Is there a generic default ?
        defined_topdefault = self._DFLT_KEY in r_dict
        top_default = r_dict.pop(self._DFLT_KEY, class_default)

        # Check consitency and replace missing values with defaults
        for c in self.target_hhs:
            myv = r_dict.setdefault(c, dict())
            # Is there a cutoff specific default ?
            defined_cutdefault = defined_topdefault or self._DFLT_KEY in myv
            last_default = myv.pop(self._DFLT_KEY, top_default)
            my_c_hhs = set(myv.keys())
            if defined_cutdefault or (class_default is not None):
                missinghh = self.target_hhs[c] - my_c_hhs
                for h in missinghh:
                    myv[h] = last_default
            else:
                if not my_c_hhs >= self.target_hhs[c]:
                    logger.error("Inconsistent input arrays while processing: \n%s",
                                 str(input_dict))
                    logger.error("Cutoff %s, expecting the following HH: \n%s",
                                 c, str(self.target_hhs[c]))
                    raise ValueError("Inconsistent input array.")

        # Filter values according to _target_hhs
        for c in list(r_dict.keys()):
            if c not in self.target_hhs:
                del r_dict[c]
        for c in self.target_hhs:
            my_c_hhs = set(r_dict[c].keys())
            extra = my_c_hhs - self.target_hhs[c]
            for hh in extra:
                del r_dict[c][hh]

        return r_dict

    @staticmethod
    def _cpl_key(hh, cutoff, vapp, vconf, xpid, model):
        return (six.text_type(hh), vapp, vconf, xpid, model, cutoff)

    @staticmethod
    def _cpl_fmtkey(k):
        cutoff_map = dict(production='prod')
        return '{:5s} {:6s}  {:24s} {:s} ({:s})'.format(
            k[0],
            cutoff_map.get(k[5], k[5]),
            k[1] + '/' + k[2],
            k[3],
            k[4]
        )

    @staticmethod
    def _rtask_key(cutoff, vapp, vconf, xpid, model):
        return (vapp, vconf, xpid, model, cutoff)

    @staticmethod
    def _rtask_fmtkey(k):
        cutoff_map = dict(production='prod')
        return '{:6s}  {:24s} {:s} ({:s})'.format(cutoff_map.get(k[4], k[4]), k[0] + '/' + k[1], k[2], k[3])

    @staticmethod
    def _process_date(date):
        mydate = Date(date)
        myhh = Time('{0.hour:d}:{0.minute:02d}'.format(mydate))
        return mydate, myhh

    @staticmethod
    def _hh_offset(hh, hhbase, dayoff):
        offset = hh - hhbase
        if offset < 0:
            offset += Time(24)
        return offset + Period(days=dayoff)

    def _compute_prepare_terms(self):
        terms_map = collections.defaultdict(set)
        for _, cv in self._cpl_data.items():
            for h, infos in cv.items():
                key = self._cpl_key(infos.base, infos.cutoff, infos.vapp, infos.vconf, infos.xpid, infos.model)
                targetoffset = self._hh_offset(h, infos.base, infos.dayoff)
                terms_map[key].update([s + targetoffset for s in infos.steps])
        terms_map = {k: sorted(terms) for k, terms in terms_map.items()}
        return terms_map

    def _compute_refill_terms(self, refill_cutoff, compute_on_refill, isolated_refill):
        finaldates = collections.defaultdict(functools.partial(collections.defaultdict,
                                                               functools.partial(collections.defaultdict, set)))
        if refill_cutoff == 'all':
            possiblehours = sorted(functools.reduce(lambda x, y: x | y,
                                                    [set(l) for l in self.target_hhs.values()]))
        else:
            possiblehours = self.target_hhs[refill_cutoff]

        # Look 24hr ahead
        for c, cv in self._cpl_data.items():
            for h, infos in cv.items():
                key = self._rtask_key(infos.cutoff, infos.vapp, infos.vconf, infos.xpid, infos.model)
                offset = self._hh_offset(h, infos.base, infos.dayoff)
                for possibleh in possiblehours:
                    roffset = self._hh_offset(h, possibleh, 0)
                    if ((roffset > 0 or
                            (compute_on_refill and roffset == 0 and (refill_cutoff == 'all' or refill_cutoff == c))) and
                            (roffset < offset or (isolated_refill and roffset == offset))):
                        finaldates[key][possibleh][offset - roffset].update([s + offset for s in infos.steps])

        for key, vdict in finaldates.items():
            for possibleh in vdict.keys():
                vdict[possibleh] = {off: sorted(terms) for off, terms in vdict[possibleh].items()}

        return finaldates

    def compatible_with(self, other):
        if isinstance(other, self.__class__):
            return (self.target_hhs == other.target_hhs and
                    self.refill_cutoff == other.refill_cutoff)
        else:
            return False

    def prepare_terms(self, date, cutoff, vapp, vconf, model=None, xpid=''):
        """
        For a task computing coupling files (at **date** and **cutoff**,
        for a specific **vapp** and **vconf**), lists the terms that should be
        computed.
        """
        _, myhh = self._process_date(date)
        if model is None:
            model = vapp
        key = self._cpl_key(myhh, cutoff, vapp, vconf, xpid, model)
        try:
            return self._prepare_terms_map[key]
        except KeyError:
            raise CouplingOffsetConfPrepareError(self._cpl_fmtkey(key))

    def coupling_offset(self, date, cutoff):
        """
        For a task needing coupling (at **date** and **cutoff**), return the
        time delta with the coupling model/file base date.
        """
        _, myhh = self._process_date(date)
        return self._hh_offset(myhh, self._cpl_data[cutoff][myhh].base,
                               self._cpl_data[cutoff][myhh].dayoff)

    def coupling_date(self, date, cutoff):
        """
        For a task needing coupling (at **date** and **cutoff**), return the
        base date of the coupling model/file.
        """
        mydate, myhh = self._process_date(date)
        return mydate - self._hh_offset(myhh, self._cpl_data[cutoff][myhh].base,
                                        self._cpl_data[cutoff][myhh].dayoff)

    def coupling_terms(self, date, cutoff):
        """
        For a task needing coupling (at **date** and **cutoff**), return the
        list of terms that should be fetched from the coupling model/file.
        """
        _, myhh = self._process_date(date)
        offset = self._hh_offset(myhh, self._cpl_data[cutoff][myhh].base,
                                 self._cpl_data[cutoff][myhh].dayoff)
        return [s + offset for s in self._cpl_data[cutoff][myhh].steps]

    def _coupling_stuff(self, date, cutoff, stuff):
        _, myhh = self._process_date(date)
        return getattr(self._cpl_data[cutoff][myhh], stuff)

    def coupling_steps(self, date, cutoff):
        """
        For a task needing coupling (at **date** and **cutoff**), return the
        prescribed steps.
        """
        return self._coupling_stuff(date, cutoff, 'steps')

    def coupling_cutoff(self, date, cutoff):
        """
        For a task needing coupling (at **date** and **cutoff**), return the
        cutoff of the coupling model/file.
        """
        return self._coupling_stuff(date, cutoff, 'cutoff')

    def coupling_vapp(self, date, cutoff):
        """
        For a task needing coupling (at **date** and **cutoff**), return the
        vapp of the coupling model/file.
        """
        return self._coupling_stuff(date, cutoff, 'vapp')

    def coupling_vconf(self, date, cutoff):
        """
        For a task needing coupling (at **date** and **cutoff**), return the
        vconf of the coupling model/file.
        """
        return self._coupling_stuff(date, cutoff, 'vconf')

    def coupling_xpid(self, date, cutoff):
        """
        For a task needing coupling (at **date** and **cutoff**), return the
        experiment ID of the coupling model/file.
        """
        return self._coupling_stuff(date, cutoff, 'xpid')

    def coupling_model(self, date, cutoff):
        """
        For a task needing coupling (at **date** and **cutoff**), return the
        vconf of the coupling model/file.
        """
        return self._coupling_stuff(date, cutoff, 'model')

    def refill_terms(self, date, cutoff, vapp, vconf, model=None, refill_cutoff=None, xpid=''):
        """The terms that should be computed for a given refill task."""
        refill_cutoff = self.refill_cutoff if refill_cutoff is None else refill_cutoff
        if refill_cutoff not in self._refill_terms_map:
            self._refill_terms_map[refill_cutoff] = self._compute_refill_terms(refill_cutoff,
                                                                               self.compute_on_refill,
                                                                               self.isolated_refill)
        if model is None:
            model = vapp
        mydate, myhh = self._process_date(date)
        key = self._rtask_key(cutoff, vapp, vconf, xpid, model)
        finaldates = dict()
        if (key not in self._refill_terms_map[refill_cutoff] or
                myhh not in self._refill_terms_map[refill_cutoff][key]):
            raise CouplingOffsetConfRefillError(self._rtask_fmtkey(key))
        for off, terms in self._refill_terms_map[refill_cutoff][key][myhh].items():
            finaldates[six.text_type(mydate - off)] = terms
        return {'date': finaldates}

    def refill_dates(self, date, cutoff, vapp, vconf, model=None, refill_cutoff=None, xpid=''):
        """The dates that should be processed in a given refill task."""
        return list(self.refill_terms(date, cutoff, vapp, vconf, model=model,
                                      refill_cutoff=refill_cutoff, xpid=xpid)['date'].keys())

    def refill_months(self, date, cutoff, vapp, vconf, model=None, refill_cutoff=None, xpid=''):
        """The months that should be processed in a given refill task."""
        mindate = min(self.refill_dates(date, cutoff, vapp, vconf, model=model,
                                        refill_cutoff=refill_cutoff, xpid=xpid))
        minmonth = Month(mindate)
        return [minmonth, minmonth + 1]


class AggregatedCouplingOffsetConfTool(ConfTool):

    _footprint = dict(
        info = 'Aggregate several CouplingOffsetConfTool objects into one',
        attr = dict(
            kind = dict(
                values= ['aggcouplingoffset', ],
            ),
            nominal = dict(
                info = "A list of couplingoffset objects used in nominal cases",
                type = FPList,
            ),
            alternate = dict(
                info = "A list of couplingoffset objects used in rescue modes",
                type = FPList,
                optional = True,
            ),
            use_alternates = dict(
                info = 'Actually use rescue mode ?',
                optional = True,
                default = True,
                type = bool,
            ),
            verbose = dict(
                info = 'When the object is created, print a summary.',
                type = bool,
                optional = True,
                default = True,
            ),
        )
    )

    def __init__(self, *kargs, **kwargs):
        super(AggregatedCouplingOffsetConfTool, self).__init__(*kargs, **kwargs)
        self._toolslist = list(self.nominal)
        if self.alternate and self.use_alternates:
            self._toolslist.extend(self.alternate)
        # At least one object is needed:
        if not len(self._toolslist):
            raise CouplingOffsetConfError("At least one sub-object is needed")
        # Check consistency
        for toolobj in self._toolslist[1:]:
            if not self._toolslist[0].compatible_with(toolobj):
                raise CouplingOffsetConfError("Inconsistent sub-objects")

        if self.verbose:
            print()
            print('#### Aggregated Coupling configuration tool initialised ####')
            print('It is made of {:d} nominal configuration tool(s)'.format(len(self.nominal)))
            if self.use_alternates:
                print('+ {:d} rescue-mode configuration tool(s)'.format(len(self.alternate)))
            else:
                print('No rescue-mode configuration tool is considered (deactivated)')
            print()

    def prepare_terms(self, date, cutoff, vapp, vconf, model=None, xpid=''):
        """
        For a task computing coupling files (at **date** and **cutoff**,
        for a specific **vapp** and **vconf**), lists the terms that should be
        computed.
        """
        terms = set()
        for toolobj in self._toolslist:
            try:
                terms.update(toolobj.prepare_terms(date, cutoff, vapp, vconf, model=model, xpid=xpid))
            except CouplingOffsetConfPrepareError as e:
                lateste = e
        if not terms:
            raise lateste
        else:
            return sorted(terms)

    def refill_terms(self, date, cutoff, vapp, vconf, model=None, refill_cutoff=None, xpid=''):
        """The terms that should be computed for a given refill task."""
        finaldates = collections.defaultdict(set)
        for toolobj in self._toolslist:
            try:
                rt = toolobj.refill_terms(date, cutoff, vapp, vconf, model=model,
                                          refill_cutoff=refill_cutoff, xpid=xpid)
                for k, v in rt['date'].items():
                    finaldates[k].update(v)
            except CouplingOffsetConfRefillError as e:
                lateste = e
        if not finaldates:
            raise lateste
        else:
            for k, v in finaldates.items():
                finaldates[k] = sorted(v)
            return {'date': finaldates}

    def refill_dates(self, date, cutoff, vapp, vconf, model=None, refill_cutoff=None, xpid=''):
        """The dates that should be processed in a given refill task."""
        return list(self.refill_terms(date, cutoff, vapp, vconf, model=model,
                                      refill_cutoff=refill_cutoff, xpid=xpid)['date'].keys())

    def refill_months(self, date, cutoff, vapp, vconf, model=None, refill_cutoff=None, xpid=''):
        """The months that should be processed in a given refill task."""
        mindate = min(self.refill_dates(date, cutoff, vapp, vconf, model=model,
                                        refill_cutoff=refill_cutoff, xpid=xpid))
        minmonth = Month(mindate)
        return [minmonth, minmonth + 1]
