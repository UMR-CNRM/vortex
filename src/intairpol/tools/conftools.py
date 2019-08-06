#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Conftools are small objects that can be instantiated from an application's
configuration file. This module defines conftools specific to IntAirPol applications.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import six
import collections

from bronx.fancies import loggers
from bronx.stdtypes.date import Date, Time, Period, timerangex
from footprints.stdtypes import FPDict, FPList

from common.tools.conftools import ConfTool

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


def _add_start_end_doc(func):
    func.__doc__ += """

        :param start: the series of coupling steps starts at...
        :param end: the series of coupling steps ends at...
                    (by default ``self.finalterm`` is used)
        """
    return func


_MocageDomainInfoBase_keys = ('source_app', 'source_conf', 'source_cutoff', 'source_model',
                              'atm_cpl_freq', 'surf_cpl_freq',
                              'atm_cpl_delta', 'surf_cpl_delta',
                              'post_steps')


class MocageDomainInfo(collections.namedtuple('MocageDomainInfoBase', _MocageDomainInfoBase_keys)):
    """Holds configuration data for a single domain."""

    def nice(self, indent=4):
        str_indent = ' ' * indent
        str_stack = list()
        for k in _MocageDomainInfoBase_keys:
            str_stack.append('{:s}{:16s}: {!s}'.format(str_indent, k, getattr(self, k)))
        return '\n'.join(str_stack)

    def __str__(self):
        return self.nice(indent=0)


class MocageDomainsConfError(Exception):
    """Abstract exception raise by :class:`MocageDomainsConfTool` objects."""
    pass


class MocageMixedDomainsInfo(object):
    """Returns configuration data that are common to several **subdomains**."""

    def __init__(self, subdomains, finalterm):
        """
        :param subdomains: A list of :class:`MocageDomainInfo` objects to be grouped
        :param finalterm: The final term
        """
        self._subdomains = subdomains
        self.finalterm = finalterm

    def __getattr__(self, name):
        stuff = set([getattr(subdomain, name) for subdomain in self._subdomains])
        if len(stuff) > 1:
            raise AttributeError('Inconsistent {:s} values among subdomains'.format(name))
        return stuff.pop()

    def atm_cpl_date(self, curdate):
        """The date of the atmospheric coupling data (given the current date **curdate**)."""
        return Date(curdate) - self.atm_cpl_delta

    def surf_cpl_date(self, curdate):
        """The date of the surface coupling data (given the current date **curdate**)."""
        return Date(curdate) - self.surf_cpl_delta

    def _domain_any_cpl_steps(self, entry, start, end, shift=False):
        start = Time(start)
        if end is None:
            end = self.finalterm
        else:
            end = Time(end)
        dentry = entry.replace('freq', 'delta')
        return timerangex(start=start, end=end, step=getattr(self, entry),
                          shift=getattr(self, dentry) if shift else 0)

    @_add_start_end_doc
    def atm_cpl_steps(self, start=0, end=None):
        """The atm_cpl_steps of coupling data."""
        return self._domain_any_cpl_steps('atm_cpl_freq', start, end)

    @_add_start_end_doc
    def surf_cpl_steps(self, start=0, end=None):
        """The surf_cpl_steps of coupling data."""
        return self._domain_any_cpl_steps('surf_cpl_freq', start, end)

    @_add_start_end_doc
    def atm_cpl_shiftedsteps(self, start=0, end=None):
        """The sifted surf_cpl_steps of coupling data."""
        return self._domain_any_cpl_steps('atm_cpl_freq', start, end, shift=True)

    @_add_start_end_doc
    def surf_cpl_shiftedsteps(self, start=0, end=None):
        """The geometry/shifted surf_cpl_steps :mod:`footprints`' substitution dictionary."""
        return self._domain_any_cpl_steps('surf_cpl_freq', start, end, shift=True)


class MocageDomainsConfTool(ConfTool):
    """
    Conf tool that handles the configuration of Mocage domains.

    This class can be instantiated using :mod:`footprints` (via the ``conftool``
    collector) or directly as demonstrated below.
    """

    _footprint = dict(
        info = 'Conf tool that handles the configuration of Mocage domains',
        attr = dict(
            kind = dict(
                values= ['mocagedomains', ],
            ),
            active = dict(
                info = 'The list of domains actually used in this Mocage run',
                type = FPList,
            ),
            domains = dict(
                info = ' The description of each indiviual Mocage domain',
                type = FPDict,
            ),
            finalterm = dict(
                info = 'The forecasts final term',
                type = Time,
            ),
        )
    )

    def __init__(self, *kargs, **kwargs):
        """
        Initialisation::

            >>> mct = MocageDomainsConfTool(kind='mocagedomains',
            ...                             active=('MACC01', 'GLOB22'),
            ...                             domains=dict(
            ...                                 GLOB01=dict(source_app='arpege',
            ...                                             source_conf='4dvarfr',
            ...                                             source_cutoff='assim',
            ...                                             source_model='arpege',
            ...                                             atm_cpl_freq='PT1H',
            ...                                             surf_cpl_freq='PT3H',
            ...                                             post_steps='0-12-3,18-finalterm-6'),
            ...                                 MACC01=dict(source_app='ifs',
            ...                                             source_conf='determ',
            ...                                             source_model='ifs',
            ...                                             atm_cpl_freq='PT3H',
            ...                                             atm_cpl_delta='PT12H',
            ...                                             surf_cpl_delta='PT24H',
            ...                                             post_steps=''),
            ...                                 GLOB22=dict(is_like='MACC01'), ),
            ...                             finalterm=48)
            >>> print(mct.domaindefs['GLOB01'])  # doctest: +NORMALIZE_WHITESPACE
            source_app      : arpege
            source_conf     : 4dvarfr
            source_cutoff   : assim
            source_model    : arpege
            atm_cpl_freq    : PT3600S
            surf_cpl_freq   : PT10800S
            atm_cpl_delta   : PT0S
            surf_cpl_delta  : PT0S
            post_steps      : [Time(0, 0), Time(3, 0), Time(6, 0), Time(9, 0), Time(12, 0),
                               Time(18, 0), Time(24, 0), Time(30, 0), Time(36, 0), Time(42, 0), Time(48, 0)]
            >>> print(mct.domaindefs['MACC01'])
            source_app      : ifs
            source_conf     : determ
            source_cutoff   : production
            source_model    : ifs
            atm_cpl_freq    : PT10800S
            surf_cpl_freq   : PT10800S
            atm_cpl_delta   : PT43200S
            surf_cpl_delta  : P1DT0S
            post_steps      : []
            >>> print(mct.domaindefs['GLOB22'])
            source_app      : ifs
            source_conf     : determ
            source_cutoff   : production
            source_model    : ifs
            atm_cpl_freq    : PT10800S
            surf_cpl_freq   : PT10800S
            atm_cpl_delta   : PT43200S
            surf_cpl_delta  : P1DT0S
            post_steps      : []

        In **domains** definitions:

            * the ``source_cutoff`` entry may be omitted; in such a case it will
              defaults to 'production';
            * the ``atm_cpl_delta`` entry may be omitted; in such a case it will
              defaults to 0;
            * the ``surf_cpl_freq`` and ``surf_cpl_delta`` entry (that describe
              the surface coupling), can be omitted; in such a case they will be
              equivalent to their ``atm_cpl_freq`` and ``atm_cpl_delta``
              atmospheric counterparts;
            * in the ``post_steps`` entry, the 'finalterm' string can appear in
              the time range definition. It will be substituted by the value
              specified in the **finalterm** attribute.
            * if two domains share identical settings, it is possible to specify
              only an ``is_like`` entry

        The present object can be used directly with :mod:`footprints` expansion
        and substitution mechanisms.

        The list of active domains/geometries::

            >>> print(', '.join(mct.all_active))
            MACC01, GLOB22

        Sometimes it is necessary to filter only active domains from a larger list::

            >>> print(', '.join(mct.grep_active('GLOB01', 'GLOB22')))
            GLOB22

        The dictionary that associates source_apps and geometries::

            >>> (mct.source_apps ==
            ...  {'geometry': {'GLOB01': 'arpege', 'MACC01': 'ifs', 'GLOB22': 'ifs'}})
            True

        The dictionary that associates source_confs and geometries::

            >>> (mct.source_confs ==
            ...  {'geometry': {'GLOB01': '4dvarfr', 'MACC01': 'determ', 'GLOB22': 'determ'}})
            True

        The dictionary that associates source_cutoffs and geometries::

            >>> (mct.source_cutoffs ==
            ...  {'geometry': {'GLOB01': 'assim', 'MACC01': 'production', 'GLOB22': 'production'}})
            True

        The dictionary that associates source_model and geometries::

            >>> (mct.source_models ==
            ...  {'geometry': {'GLOB01': 'arpege', 'MACC01': 'ifs', 'GLOB22': 'ifs'}})
            True

        The dictionaries that associates coupling data's date and geometries
        (this takes into account the ``(atm|surf)_cpl_delta`` entry)::

            >>> (mct.atm_cpl_dates('2019080700') ==
            ...  {'geometry': {'GLOB01': Date('2019080700'),
            ...                'MACC01': Date('2019080612'), 'GLOB22': Date('2019080612')}})
            True
            >>> (mct.surf_cpl_dates('2019080700') ==
            ...  {'geometry': {'GLOB01': Date('2019080700'),
            ...                'MACC01': Date('2019080600'), 'GLOB22': Date('2019080600')}})
            True

        The dictionaries that associates coupling data's terms and geometries::

            >>> (mct.atm_cpl_steps() ==
            ...  {'geometry': {'GLOB01': timerangex('0-48-1'),
            ...                'MACC01': timerangex('0-48-3'), 'GLOB22': timerangex('0-48-3')}})
            True
            >>> (mct.surf_cpl_steps() ==
            ...  {'geometry': {'GLOB01': timerangex('0-48-3'),
            ...                'MACC01': timerangex('0-48-3'), 'GLOB22': timerangex('0-48-3')}})
            True

        By default, the coupling data's term starts at 0 and ends at ``self.finalterm``
        but this can be overwritten::

            >>> (mct.atm_cpl_steps(12, 24) ==
            ...  {'geometry': {'GLOB01': timerangex('12-24-1'),
            ...                'MACC01': timerangex('12-24-3'), 'GLOB22': timerangex('12-24-3')}})
            True
            >>> (mct.atm_cpl_steps(12) ==
            ...  {'geometry': {'GLOB01': timerangex('12-48-1'),
            ...                'MACC01': timerangex('12-48-3'), 'GLOB22': timerangex('12-48-3')}})
            True

        There are equivalent methods that return values shifted by the ``(atm|surf)_cpl_delta`` entry::

            >>> (mct.atm_cpl_shiftedsteps() ==
            ...  {'geometry': {'GLOB01': timerangex('0-48-1'),
            ...                'MACC01': timerangex('12-60-3'), 'GLOB22': timerangex('12-60-3')}})
            True
            >>> (mct.surf_cpl_shiftedsteps() ==
            ...  {'geometry': {'GLOB01': timerangex('0-48-3'),
            ...                'MACC01': timerangex('24-72-3'), 'GLOB22': timerangex('24-72-3')}})
            True

        The dictionary that associates post-porcessing terms and geometries::

            >>> (mct.post_steps() ==
            ...  {'geometry': {'GLOB01': timerangex('0-12-3,18-48-6'), 'MACC01':[], 'GLOB22':[]}})
            True
            >>> (mct.post_steps(6, 24) ==
            ...  {'geometry': {'GLOB01': timerangex('6-12-3,18-24-6'), 'MACC01':[], 'GLOB22':[]}})
            True

        Domains can be grouped together and used jointly (if they share the same configuration)::

            >>> print(mct.group(['MACC01', 'GLOB22']).source_app)
            ifs
            >>> print(mct.group(['MACC01', 'GLOB22']).source_conf)
            determ
            >>> mct.group(['MACC01', 'GLOB22']).atm_cpl_date('2019080700')
            Date(2019, 8, 6, 12, 0)
            >>> (mct.group(['MACC01', 'GLOB22']).atm_cpl_steps() ==
            ...  timerangex('0-48-3'))
            True

        Using *group*, if domains are inconsistent, an exception is raised::

            >>> print(mct.group(['MACC01', 'GLOB01']).source_app)
            Traceback (most recent call last):
                ...
            AttributeError: Inconsistent source_app values among subdomains

        """
        super(MocageDomainsConfTool, self).__init__(*kargs, **kwargs)
        self._domaindefs = dict()
        for d, ddef in self.domains.items():
            if 'is_like' not in ddef:
                self._add_domain_def(d, ddef)
        for d, ddef in self.domains.items():
            if 'is_like' in ddef:
                try:
                    self._domaindefs[d] = self.domaindefs[ddef['is_like']]
                except KeyError:
                    raise MocageDomainsConfError('Incorrect is_like entry. {:s} does not exists.'
                                                 .format(ddef['is_like']))
        for d in self.active:
            if d not in self.domaindefs:
                raise MocageDomainsConfError('The active domain {:s} is not defined.'
                                             .format(d))

    def _add_domain_def(self, dname, ddef):
        """Adds a domain in _domainsdefs given its name and definition dictionary."""
        if not isinstance(ddef, dict):
            raise MocageDomainsConfError('A domain definition must be a dicitonary')
        # Set default values
        ddef.setdefault('source_cutoff', 'production')
        ddef.setdefault('atm_cpl_delta', 0)
        ddef.setdefault('surf_cpl_freq', ddef.get('atm_cpl_freq', 0))
        ddef.setdefault('surf_cpl_delta', ddef.get('atm_cpl_delta'))
        ddef.setdefault('post_steps', '')
        # Types conversion
        try:
            ddef['atm_cpl_freq'] = Period(ddef['atm_cpl_freq'])
            ddef['surf_cpl_freq'] = Period(ddef['surf_cpl_freq'])
            ddef['atm_cpl_delta'] = Period(ddef['atm_cpl_delta'])
            ddef['surf_cpl_delta'] = Period(ddef['surf_cpl_delta'])
        except (ValueError, TypeError):
            raise MocageDomainsConfError('(atm|surf)_cpl_(freq|delta) must be convertable to Period objects.')
        if ddef['post_steps'] and isinstance(ddef['post_steps'], six.string_types):
            if 'finalterm' in ddef['post_steps']:
                ddef['post_steps'] = ddef['post_steps'].replace('finalterm',
                                                                self.finalterm.fmthm)
            try:
                ddef['post_steps'] = timerangex(ddef['post_steps'])
            except (ValueError, TypeError):
                raise MocageDomainsConfError('post_steps should be parsable by timerangex: {!s}'
                                             .format(ddef['post_steps']))
        else:
            if not ddef['post_steps']:
                ddef['post_steps'] = []
            else:
                raise MocageDomainsConfError('post_steps should be a string')
        try:
            ddef_tuple = MocageDomainInfo(** ddef)
        except TypeError:
            raise MocageDomainsConfError("Unable to create the domain's configuration object " +
                                         "(some data are probably missing or misspelled).")
        self._domaindefs[dname] = ddef_tuple

    @property
    def domaindefs(self):
        """The dictionary of domains definitions (as :class:`MocageDomainInfo` objects)."""
        return self._domaindefs

    @property
    def all_active(self):
        """The list of all active domains."""
        return [d for d in self.active]

    def grep_active(self, *candidates):
        """Filter the **candidates** list in order to retain only active domains."""
        domains = list()
        for c in candidates:
            if isinstance(c, (list, tuple)):
                domains.extend([k for k in c if k in self.active])
            else:
                if c in self.active:
                    domains.append(c)
        return domains

    def group(self, domains):
        """
        Returns a :class:`MocageMixedDomainsInfo` object allowing to access jointly
        configuration data of all the domains listed in **domains**.
        """
        return MocageMixedDomainsInfo([self.domaindefs[d] for d in domains],
                                      self.finalterm)

    def _domain_dict_from_entry(self, entry):
        return dict(geometry={d: getattr(v, entry) for d, v in self.domaindefs.items()})

    def __getattr__(self, name):
        if name.endswith('s') and name[:-1] in _MocageDomainInfoBase_keys:
            return self._domain_dict_from_entry(name[:-1])
        else:
            raise AttributeError(name)

    def _domain_any_cpl_date(self, curdate, entry):
        curdate = Date(curdate)
        return dict(geometry={d: curdate - getattr(v, entry) for d, v in self.domaindefs.items()})

    def atm_cpl_dates(self, curdate):
        """The geometry/atm_cpl_date :mod:`footprints`' substitution dictionary."""
        return self._domain_any_cpl_date(curdate, 'atm_cpl_delta')

    def surf_cpl_dates(self, curdate):
        """The geometry/surf_cpl_date :mod:`footprints`' substitution dictionary."""
        return self._domain_any_cpl_date(curdate, 'surf_cpl_delta')

    def _domain_any_cpl_steps(self, entry, start, end, shift=False):
        start = Time(start)
        if end is None:
            end = self.finalterm
        else:
            end = Time(end)
        dentry = entry.replace('freq', 'delta')
        return dict(geometry={d: timerangex(start=start, end=end, step=getattr(v, entry),
                                            shift=getattr(v, dentry) if shift else 0)
                              for d, v in self.domaindefs.items()})

    @_add_start_end_doc
    def atm_cpl_steps(self, start=0, end=None):
        """The geometry/atm_cpl_steps :mod:`footprints`' substitution dictionary."""
        return self._domain_any_cpl_steps('atm_cpl_freq', start, end)

    @_add_start_end_doc
    def surf_cpl_steps(self, start=0, end=None):
        """The geometry/surf_cpl_steps :mod:`footprints`' substitution dictionary."""
        return self._domain_any_cpl_steps('surf_cpl_freq', start, end)

    @_add_start_end_doc
    def atm_cpl_shiftedsteps(self, start=0, end=None):
        """The geometry/shifted atm_cpl_steps :mod:`footprints`' substitution dictionary."""
        return self._domain_any_cpl_steps('atm_cpl_freq', start, end, shift=True)

    @_add_start_end_doc
    def surf_cpl_shiftedsteps(self, start=0, end=None):
        """The geometry/shifted surf_cpl_steps :mod:`footprints`' substitution dictionary."""
        return self._domain_any_cpl_steps('surf_cpl_freq', start, end, shift=True)

    def post_steps(self, start=None, end=None):
        """The geometry/post_steps :mod:`footprints`' substitution dictionary.

        :param start: the series of post-processing steps starts at...
        :param end: the series of post-processing steps ends at...
                    (by default ``self.finalterm`` is used)
        """
        if start is not None:
            start = Time(start)
        if end is not None:
            end = Time(end)
        return dict(geometry={d: [ps for ps in v.post_steps
                                  if (start is None or ps >= start) and (end is None or ps <= end)]
                              for d, v in self.domaindefs.items()})


if __name__ == '__main__':
    import doctest
    doctest.testmod()
