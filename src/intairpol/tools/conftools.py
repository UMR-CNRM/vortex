#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Conftools are small objects that can be instantiated from an application's
configuration file. This module defines conftools specific to IntAirPol applications.
"""

from __future__ import print_function, absolute_import, unicode_literals, division
from six.moves import filter

import collections
import functools

from bronx.fancies import language, loggers
from bronx.stdtypes.date import Date, Time, Period, timerangex
from footprints.stdtypes import FPDict

from vortex.syntax import stdattrs as v_stdattrs

from common.tools.conftools import ConfTool

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


# ------------------------------------------------------------------------------
# Some decorators to auto-generate documentation

def _add_cutoff_hh_doc(func):
    """Document cutoff and hh arguments."""
    func.__doc__ += """

        :param str cutoff: 'assim' or 'production'
        :param int hh: The current simulation basetime
        """
    return func


def _add_start_end_doc(func):
    """Document start and end arguments."""
    func.__doc__ += """

        :param bronx.stdtypes.date.Time start: the series of steps starts at...
        :param bronx.stdtypes.date.Time end: the series of steps ends at...
                                             (by default ``self.finalterm`` is used)
        :param bool first: Return the first element of the steps list
        :param bool final: Return the last element of the steps list
        """
    return func


# ------------------------------------------------------------------------------
# Code related to the Mocage domains configuration tools


_MocageDomainInfoBase_keys = ('source_app', 'source_conf', 'source_cutoff',
                              'source_model', 'source_geometry',
                              'atm_cpl_delta', 'chem_cpl_delta', 'surf_cpl_delta',
                              'atm_cpl_steps', 'chem_cpl_steps', 'surf_cpl_steps',
                              'post_steps', 'restart_steps', 'stats_steps')

_PluralisedMocageDomainInfoBase_keys = [language.Pluralise('en_GB')(k)
                                        for k in _MocageDomainInfoBase_keys]


class MocageDomainInfo(collections.namedtuple('MocageDomainInfoBase', _MocageDomainInfoBase_keys)):
    """Holds configuration data for a single domain.

    Depending on the context, the object may contain information for every
    possible cutoff and basetime (hh).
    """

    def nice(self, indent=4):
        str_indent = ' ' * indent
        str_stack = list()
        for k in _MocageDomainInfoBase_keys:
            what = getattr(self, k)
            if isinstance(what, (list, tuple)):
                what = ','.join(['{!s}'.format(w) for w in what])
            str_stack.append('{:s}{:16s}: {!s}'.format(str_indent, k, what))
        return '\n'.join(str_stack)

    def __str__(self):
        return self.nice(indent=0)


class MocageDomainsConfError(Exception):
    """Abstract exception raise by :class:`MocageDomainsConfTool` objects."""
    pass


class HHDict(dict):
    """A special dict that automatically deals with the 'default' entry."""

    def __getitem__(self, name):
        if name != 'default' and not isinstance(name, Time):
            name = Time(name)
        if name not in self and 'default' in self:
            return self['default']
        else:
            return super(HHDict, self).__getitem__(name)


class MocageDomainsConfTool(ConfTool):
    """
    Conf tool that handles the configuration of Mocage domains.

    This class can be instantiated using :mod:`footprints` (via the ``conftool``
    collector) or directly as demonstrated below.

    The object's configuration is provided using the **config** attribute that
    is a dictionary. It must strictly contain ``actives``, ``domains`` and
    ``finalterms`` entries:

        * The ``actives`` entry contains the list of active domains (i.e. the
          one that will actually be used for the Mocage forecast. Each of the
          active domain must be described in the ``domains`` entry (see below);
        * The ``domains`` entry gives the description of each domain (that can
          be active or not). Consequently, it is itself a dictionary. More detail
          is given in the following example;
        * The ``finalterms``, entry contains the final term of the forecast. It
          must be convertible to a :class:`Time` object.

    For each and every **config** entry, the configuration data may vary depending
    on the cutoff and the current basetime (HH). For example, the ``finalterms``
    can be described as follow:

        * ``finalterms='72'``: The finalterm is always 72h
        * ``finalterms=dict(production=72, assim=24)``: The finalterm is 24h
          for 'assim' cutoffs and 72h for 'production' cutoffs
        * ``finalterms={'00':72, '12':48, 'default':24}``: The finalterm is 24h except
          at the 00UTC and 12UTC basetimes (that will respectively use a
          72h and 48h finalterm)
        * ``finalterms=dict(production={'00':72, 'default':48}, assim=24)``:
          The finalterm is 24h for all 'assim' cutoffs, 72 for the 00UTC 'production'
          cutoff and 48h for all other 'production' cutoffs

    A direct consequence of this *cutoff*/basetime dependency is that most of the
    object's methods must be called with *cutoff* and basetime (*hh*) as first
    arguments.

    Here is an example with a real, live, object:

    """

    _footprint = dict(
        info = 'Conf tool that handles the configuration of Mocage domains',
        attr = dict(
            kind = dict(
                values= ['mocagedomains', ],
            ),
            config = dict(
                info = ' The general configuration and configuration of each individual Mocage domain',
                type = FPDict,
            ),
        )
    )

    def __init__(self, *kargs, **kwargs):
        """
        Initialisation::

            >>> mct = MocageDomainsConfTool(kind='mocagedomains',
            ...                             config=dict(
            ...                                 actives=('MACC01', 'GLOB22'),
            ...                                 domains=dict(
            ...                                     GLOB11=dict(source_app='arpege',
            ...                                                 source_conf='4dvarfr',
            ...                                                 source_cutoff='assim',
            ...                                                 source_model='arpege',
            ...                                                 source_geometry='global1798',
            ...                                                 atm_cpl_steps='0-finalterm-1',
            ...                                                 chem_cpl_steps='0-finalterm-3',
            ...                                                 surf_cpl_steps='0-finalterm-3',
            ...                                                 post_steps='0-12-3,18-finalterm-6',
            ...                                                 restart_steps='0-finalterm-24',
            ...                                                 stats_steps='0-finalterm-24', ),
            ...                                     MACC01=dict(source_app='ifs',
            ...                                                 source_conf='determ',
            ...                                                 source_model='ifs',
            ...                                                 atm_cpl_delta=dict(production='PT24H',
            ...                                                                    assim='PT12H'),
            ...                                                 surf_cpl_delta='PT24H',
            ...                                                 atm_cpl_steps=['0-6-1', '9-finalterm-3'],
            ...                                                 surf_cpl_steps='0-finalterm-3',
            ...                                                 chem_cpl_steps='0-finalterm-3',
            ...                                                 post_steps='',
            ...                                                 restart_steps='0-finalterm-24',
            ...                                                 stats_steps='0-finalterm-24', ),
            ...                                     GLOB22=dict(is_like='MACC01'), ),
            ...                                 finalterms=dict(production={'00':72, 'default':48},
            ...                                                 assim=24), )
            ...                             )
            >>> print(mct.ontime_domains('assim', 0)['GLOB11'])  # doctest: +NORMALIZE_WHITESPACE
            source_app      : arpege
            source_conf     : 4dvarfr
            source_cutoff   : assim
            source_model    : arpege
            source_geometry : global1798
            atm_cpl_delta   : PT0S
            chem_cpl_delta  : PT0S
            surf_cpl_delta  : PT0S
            atm_cpl_steps   : 0-finalterm-1
            chem_cpl_steps  : 0-finalterm-3
            surf_cpl_steps  : 0-finalterm-3
            post_steps      : 0-12-3,18-finalterm-6
            restart_steps   : 0-finalterm-24
            stats_steps     : 0-finalterm-24
            >>> print(mct.ontime_domains('assim', 0)['MACC01'])  # doctest: +NORMALIZE_WHITESPACE
            source_app      : ifs
            source_conf     : determ
            source_cutoff   : production
            source_model    : ifs
            source_geometry : None
            atm_cpl_delta   : PT43200S
            chem_cpl_delta  : PT43200S
            surf_cpl_delta  : P1DT0S
            atm_cpl_steps   : 0-6-1,9-finalterm-3
            chem_cpl_steps  : 0-finalterm-3
            surf_cpl_steps  : 0-finalterm-3
            post_steps      :
            restart_steps   : 0-finalterm-24
            stats_steps     : 0-finalterm-24
            >>> print(mct.ontime_domains('assim', 0)['GLOB22'])  # doctest: +NORMALIZE_WHITESPACE
            source_app      : ifs
            source_conf     : determ
            source_cutoff   : production
            source_model    : ifs
            source_geometry : None
            atm_cpl_delta   : PT43200S
            chem_cpl_delta  : PT43200S
            surf_cpl_delta  : P1DT0S
            atm_cpl_steps   : 0-6-1,9-finalterm-3
            chem_cpl_steps  : 0-finalterm-3
            surf_cpl_steps  : 0-finalterm-3
            post_steps      :
            restart_steps   : 0-finalterm-24
            stats_steps     : 0-finalterm-24

        In **domains** definitions:

            * the ``source_cutoff`` entry may be omitted; in such a case it will
              defaults to 'production';
            * the ``source_geometry`` entry may be omitted; in such a case it will
              defaults to ``None``
            * the ``atm_cpl_delta`` entry may be omitted; in such a case it will
              defaults to 0;
            * the ``chem_cpl_delta`` entry may be omitted; in such a case it will
              defaults to `atm_cpl_delta``;
            * the ``surf_cpl_delta`` entry may be omitted; in such a case it will
              defaults to `atm_cpl_delta``;
            * in the ``atm_cpl_steps``, ``chem_cpl_steps``, ``surf_cpl_steps``,
              ``post_steps``, ``restart_steps`` and ``stats_cpl_steps`` entry,
              the 'finalterm' string can appear in the time range definition. It
              will be substituted by the value specified in the **finalterms**
              attribute.
            * if two domains share identical settings, it is possible to specify
              only an ``is_like`` entry

        The present object can be used directly with :mod:`footprints` expansion
        and substitution mechanisms.

        The list of active domains/geometries::

            >>> print(', '.join(mct.all_active('assim', '00')))
            MACC01, GLOB22

        Sometimes it is necessary to filter only active domains from a larger list::

            >>> print(', '.join(mct.grep_active('assim', '00', 'GLOB11', 'GLOB22')))
            GLOB22

        Or to retrieve the name of the first active domain::

            >>> print(mct.first_active('assim', '00'))
            MACC01

        The dictionary that associates source_apps and geometries::

            >>> (mct.source_apps('assim', '00') ==
            ...  {'geometry': {'GLOB11': 'arpege', 'MACC01': 'ifs', 'GLOB22': 'ifs'}})
            True

        The dictionary that associates source_confs and geometries::

            >>> (mct.source_confs('assim', '00') ==
            ...  {'geometry': {'GLOB11': '4dvarfr', 'MACC01': 'determ', 'GLOB22': 'determ'}})
            True

        The dictionary that associates source_cutoffs and geometries::

            >>> (mct.source_cutoffs('assim', '00') ==
            ...  {'geometry': {'GLOB11': 'assim', 'MACC01': 'production', 'GLOB22': 'production'}})
            True

        The dictionary that associates source_model and geometries::

            >>> (mct.source_models('assim', '00') ==
            ...  {'geometry': {'GLOB11': 'arpege', 'MACC01': 'ifs', 'GLOB22': 'ifs'}})
            True

        The dictionary that associates source_geometry and geometries::

            >>> (mct.source_geometries('assim', '00') ==
            ...  {'geometry': {'GLOB11': 'global1798', 'MACC01': None, 'GLOB22': None}})
            True

        The dictionaries that associates coupling data's date and geometries
        (this takes into account the ``(atm|chem|surf)_cpl_delta`` entry)::

            >>> (mct.atm_cpl_dates('assim', '00', '2019080700') ==
            ...  {'geometry': {'GLOB11': Date('2019080700'),
            ...                'MACC01': Date('2019080612'), 'GLOB22': Date('2019080612')}})
            True
            >>> (mct.chem_cpl_dates('assim', '00', '2019080700') ==
            ...  {'geometry': {'GLOB11': Date('2019080700'),
            ...                'MACC01': Date('2019080612'), 'GLOB22': Date('2019080612')}})
            True
            >>> (mct.surf_cpl_dates('assim', '00', '2019080700') ==
            ...  {'geometry': {'GLOB11': Date('2019080700'),
            ...                'MACC01': Date('2019080600'), 'GLOB22': Date('2019080600')}})
            True

        Because of our configuration, the result is different depending on the
        *cutoff* and basetime (because ``atm_cpl_delta`` varies)::

            >>> (mct.atm_cpl_dates('production', '00', '2019080700') ==
            ...  {'geometry': {'GLOB11': Date('2019080700'),
            ...                'MACC01': Date('2019080600'), 'GLOB22': Date('2019080600')}})
            True
            >>> (mct.chem_cpl_dates('production', '00', '2019080700') ==
            ...  {'geometry': {'GLOB11': Date('2019080700'),
            ...                'MACC01': Date('2019080600'), 'GLOB22': Date('2019080600')}})
            True
            >>> (mct.surf_cpl_dates('production', '00', '2019080700') ==
            ...  {'geometry': {'GLOB11': Date('2019080700'),
            ...                'MACC01': Date('2019080600'), 'GLOB22': Date('2019080600')}})
            True

        The dictionaries that associates coupling data's terms and geometries::

            >>> (mct.atm_cpl_steps('assim', '00') ==
            ...  {'geometry': {'GLOB11': timerangex('0-24-1'),
            ...                'MACC01': timerangex('0-6-1,9-24-3'),
            ...                'GLOB22': timerangex('0-6-1,9-24-3')}})
            True
            >>> (mct.chem_cpl_steps('assim', '00') ==
            ...  {'geometry': {'GLOB11': timerangex('0-24-3'),
            ...                'MACC01': timerangex('0-24-3'), 'GLOB22': timerangex('0-24-3')}})
            True
            >>> (mct.surf_cpl_steps('assim', '00') ==
            ...  {'geometry': {'GLOB11': timerangex('0-24-3'),
            ...                'MACC01': timerangex('0-24-3'), 'GLOB22': timerangex('0-24-3')}})
            True

        A simple way to exclude the first/and last values of the steps list is provided::

            >>> (mct.atm_cpl_steps('assim', '00', first=False) ==
            ...  {'geometry': {'GLOB11': timerangex('1-24-1'),
            ...                'MACC01': timerangex('1-6-1,9-24-3'),
            ...                'GLOB22': timerangex('1-6-1,9-24-3')}})
            True
            >>> (mct.atm_cpl_steps('assim', '00', final=False) ==
            ...  {'geometry': {'GLOB11': timerangex('0-23-1'),
            ...                'MACC01': timerangex('0-6-1,9-21-3'),
            ...                'GLOB22': timerangex('0-6-1,9-21-3')}})
            True
            >>> (mct.atm_cpl_steps('assim', '00', first=False, final=False) ==
            ...  {'geometry': {'GLOB11': timerangex('1-23-1'),
            ...                'MACC01': timerangex('1-6-1,9-21-3'),
            ...                'GLOB22': timerangex('1-6-1,9-21-3')}})
            True

        By default, the coupling data's term starts at the first term listed in the settings
        and ends at ``self.finalterm`` but this can be overwritten::

            >>> (mct.atm_cpl_steps('assim', 0, 12, 18) ==
            ...  {'geometry': {'GLOB11': timerangex('12-18-1'),
            ...                'MACC01': timerangex('12-18-3'), 'GLOB22': timerangex('12-18-3')}})
            True
            >>> (mct.chem_cpl_steps('assim', 0, 12, 18) ==
            ...  {'geometry': {'GLOB11': timerangex('12-18-3'),
            ...                'MACC01': timerangex('12-18-3'), 'GLOB22': timerangex('12-18-3')}})
            True
            >>> (mct.surf_cpl_steps('assim', 0, 12) ==
            ...  {'geometry': {'GLOB11': timerangex('12-24-3'),
            ...                'MACC01': timerangex('12-24-3'), 'GLOB22': timerangex('12-24-3')}})
            True

        For the first active domain, the coupling frequency at the begining of
        the steps list can be obtained as follows::

            >>> mct.atm_cpl_firstfreq('assim', 0)
            Period(seconds=3600)
            >>> mct.atm_cpl_firstfreq('assim', 0, start=6)
            Period(seconds=10800)
            >>> mct.chem_cpl_firstfreq('assim', 0)
            Period(seconds=10800)
            >>> mct.surf_cpl_firstfreq('assim', 0)
            Period(seconds=10800)

        There are equivalent methods that return values shifted by the ``(atm|chem|surf)_cpl_delta`` entry::

            >>> (mct.atm_cpl_shiftedsteps('assim', '00') ==
            ...  {'geometry': {'GLOB11': timerangex('0-24-1'),
            ...                'MACC01': timerangex('12-18-1,21-36-3'),
            ...                'GLOB22': timerangex('12-18-1,21-36-3')}})
            True
            >>> (mct.chem_cpl_shiftedsteps('assim', '00') ==
            ...  {'geometry': {'GLOB11': timerangex('0-24-3'),
            ...                'MACC01': timerangex('12-36-3'), 'GLOB22': timerangex('12-36-3')}})
            True
            >>> (mct.surf_cpl_shiftedsteps('assim', '00') ==
            ...  {'geometry': {'GLOB11': timerangex('0-24-3'),
            ...                'MACC01': timerangex('24-48-3'), 'GLOB22': timerangex('24-48-3')}})
            True

        Because of our configuration, the result is different depending on the
        *cutoff* and basetime (because of ``finalterms`` and ``atm_cpl_delta``):

            >>> (mct.atm_cpl_steps('production', '00') ==
            ...  {'geometry': {'GLOB11': timerangex('0-72-1'),
            ...                'MACC01': timerangex('0-6-1,9-72-3'),
            ...                'GLOB22': timerangex('0-6-1,9-72-3')}})
            True
            >>> (mct.atm_cpl_shiftedsteps('production', '00') ==
            ...  {'geometry': {'GLOB11': timerangex('0-72-1'),
            ...                'MACC01': timerangex('24-30-1,33-96-3'),
            ...                'GLOB22': timerangex('24-30-1,33-96-3')}})
            True
            >>> (mct.atm_cpl_steps('production', '12') ==
            ...  {'geometry': {'GLOB11': timerangex('0-48-1'),
            ...                'MACC01': timerangex('0-6-1,9-48-3'),
            ...                'GLOB22': timerangex('0-6-1,9-48-3')}})
            True
            >>> (mct.atm_cpl_shiftedsteps('production', '12') ==
            ...  {'geometry': {'GLOB11': timerangex('0-48-1'),
            ...                'MACC01': timerangex('24-30-1,33-72-3'),
            ...                'GLOB22': timerangex('24-30-1,33-72-3')}})
            True

        The dictionary that associates post-processing terms and geometries work the same way::

            >>> (mct.post_steps('production', '12') ==
            ...  {'geometry': {'GLOB11': timerangex('0-12-3,18-48-6'), 'MACC01':[], 'GLOB22':[]}})
            True
            >>> (mct.post_steps('production', '00') ==
            ...  {'geometry': {'GLOB11': timerangex('0-12-3,18-72-6'), 'MACC01':[], 'GLOB22':[]}})
            True
            >>> (mct.post_steps('production', '00', 6, 24) ==
            ...  {'geometry': {'GLOB11': timerangex('6-12-3,18-24-6'), 'MACC01':[], 'GLOB22':[]}})
            True

        Conversely, the dictionary that associates restart/stats terms and geometries::

            >>> (mct.restart_steps('production', '12') ==
            ...  {'geometry': {'GLOB11': timerangex('0-48-24'), 'MACC01':timerangex('0-48-24'),
            ...                'GLOB22':timerangex('0-48-24')}})
            True
            >>> (mct.stats_steps('production', '12') ==
            ...  {'geometry': {'GLOB11': timerangex('0-48-24'), 'MACC01':timerangex('0-48-24'),
            ...                'GLOB22':timerangex('0-48-24')}})
            True

        Domains can be grouped together and used jointly (if they share the same configuration)::

            >>> print(mct.group('assim', '00', ['MACC01', 'GLOB22']).source_app)
            ifs
            >>> print(mct.group('assim', '00', ['MACC01', 'GLOB22']).source_conf)
            determ
            >>> mct.group('assim', '00', ['MACC01', 'GLOB22']).atm_cpl_date('2019080700')
            Date(2019, 8, 6, 12, 0)
            >>> (mct.group('assim', '00', ['MACC01', 'GLOB22']).atm_cpl_steps() ==
            ...  timerangex('0-6-1,9-24-3'))
            True

        Groups with only one domain also work (also it is kind of useless...)::

            >>> (mct.group('assim', '00', ['GLOB11', ], active=False).atm_cpl_steps() ==
            ...  timerangex('0-24-1'))
            True

        Using *group*, if domains are inconsistent, an exception is raised::

            >>> print(mct.group('assim', '00', ['MACC01', 'GLOB11'], active=False).source_app)
            Traceback (most recent call last):
                ...
            AttributeError: Inconsistent source_app values among subdomains

        Having to specified *cutoff* and *hh* at each and every method call is
        tedious. The :class:`CutoffHhMocageDomainsConfTool` provide a way to create
        a 'temporary' object that will be dedicated to a given *cutoff* and
        basetime (*hh*). Such objects can be created using :mod:`footprints`
        (via the ``conftool`` collector) or directly as demonstrated below::

            >>> mct00A = CutoffHhMocageDomainsConfTool(kind='mocagedomains',
            ...                                        parentconf=mct,
            ...                                        cutoff='assim', hh='00')
            >>> print(mct00A.domains['GLOB11'])  # doctest: +NORMALIZE_WHITESPACE
            source_app      : arpege
            source_conf     : 4dvarfr
            source_cutoff   : assim
            source_model    : arpege
            source_geometry : global1798
            atm_cpl_delta   : PT0S
            chem_cpl_delta  : PT0S
            surf_cpl_delta  : PT0S
            atm_cpl_steps   : 0-finalterm-1
            chem_cpl_steps  : 0-finalterm-3
            surf_cpl_steps  : 0-finalterm-3
            post_steps      : 0-12-3,18-finalterm-6
            restart_steps   : 0-finalterm-24
            stats_steps     : 0-finalterm-24

        For example, to get the source_app mapping:

            >>> (mct00A.source_apps() ==
            ...  {'geometry': {'GLOB11': 'arpege', 'MACC01': 'ifs', 'GLOB22': 'ifs'}})
            True

        Likewise, to get the finalterm:

            >>> mct00A.finalterm
            Time(24, 0)

        """
        super(MocageDomainsConfTool, self).__init__(*kargs, **kwargs)
        if set(self.config.keys()) != set(('actives', 'domains', 'finalterms')):
            raise MocageDomainsConfError('The config dictionary must contain "active", "domains" and "finalterm" entries')
        self._actual_config = dict(domains=dict())
        for d, ddef in self.config['domains'].items():
            if 'is_like' not in ddef:
                self._add_domain_def(d, ddef)
        for d, ddef in self.config['domains'].items():
            if 'is_like' in ddef:
                try:
                    self.domains[d] = self.domains[ddef['is_like']]
                except KeyError:
                    raise MocageDomainsConfError('Incorrect is_like entry. {:s} does not exists.'
                                                 .format(ddef['is_like']))
        self._actual_config['actives'] = self._item_transform(self.config['actives'],
                                                              validcb=lambda ds: ((isinstance(ds, (list, tuple)) and
                                                                                   all([d in self.domains for d in ds])) or
                                                                                  ds in self.domains),
                                                              validmsg='Validation error: Active domain not defined',
                                                              cast=list)
        self._actual_config['finalterms'] = self._item_transform(self.config['finalterms'],
                                                                 cast=Time)

    @property
    def actives(self):
        return self._actual_config['actives']

    @property
    def domains(self):
        return self._actual_config['domains']

    @property
    def finalterms(self):
        return self._actual_config['finalterms']

    @_add_cutoff_hh_doc
    def ontime_domains(self, cutoff, hh):
        """
        Return a dictionary with domains definitions for a given *cutoff* and
        basetime (*hh*).
        """
        return {k: MocageDomainInfo(** {ek: getattr(ddef, ek)[cutoff][hh]
                                        for ek in _MocageDomainInfoBase_keys})
                for k, ddef in self.domains.items()}

    @staticmethod
    def _item_value_tweak(value, validcb, validmsg, cast):
        if validcb and not validcb(value):
            raise MocageDomainsConfError('{:s} (got:  {!s})'.format(validmsg, value))
        if cast is not None:
            try:
                value = cast(value)
            except (TypeError, ValueError):
                raise MocageDomainsConfError('Unable to cast "{!s}" using the "{!r}" object'.format(value, cast))
        return value

    @classmethod
    def _item_time_transform(cls, item, validcb, validmsg, cast):
        transformed = HHDict()
        for k, v in item.items():
            if k != 'default':
                try:
                    k = Time(k)
                except (TypeError, ValueError):
                    # Malformed key...
                    raise MocageDomainsConfError('Malformed dictionary: {!s}'.format(item))
            transformed[k] = cls._item_value_tweak(v, validcb, validmsg, cast)
        return transformed

    @classmethod
    def _item_transform(cls, item, validcb=None, validmsg='Validation Error',
                        cast=None):
        d = dict()
        if isinstance(item, dict):
            if set(item.keys()) == set(['assim', 'production']):
                # an assim/prod mapping
                for c, v in item.items():
                    if isinstance(v, dict):
                        # hh based dictionary
                        v = cls._item_time_transform(v, validcb, validmsg, cast)
                    else:
                        v = HHDict(default=cls._item_value_tweak(v, validcb, validmsg, cast))
                    d[c] = v
            else:
                # hh based dictionary
                v = cls._item_time_transform(item, validcb, validmsg, cast)
                for c in ('assim', 'production'):
                    d[c] = v
        else:
            # Single global values
            for c in ('assim', 'production'):
                d[c] = HHDict(default=cls._item_value_tweak(item, validcb, validmsg, cast))
        return d

    @staticmethod
    def _any_steps_validation(value):
        if value:
            # Use a fake finalterm just to test that the expression is valid...
            # The actual expansion will be done latter
            if not isinstance(value, list):
                value = [value, ]
            for a_value in value:
                newvalue = a_value.replace('finalterm', '480:00')
                try:
                    value = timerangex(newvalue)
                except (ValueError, TypeError):
                    return False
        return True

    def _add_domain_def(self, dname, ddef):
        """Adds a domain in _domainsdefs given its name and definition dictionary."""
        if not isinstance(ddef, dict):
            raise MocageDomainsConfError('A domain definition must be a dictionary')
        # Set default values
        ddef.setdefault('source_cutoff', 'production')
        ddef.setdefault('source_geometry', None)
        ddef.setdefault('atm_cpl_delta', 0)
        ddef.setdefault('chem_cpl_delta', ddef.get('atm_cpl_delta'))
        ddef.setdefault('surf_cpl_delta', ddef.get('atm_cpl_delta'))
        ddef.setdefault('atm_cpl_steps', '')
        ddef.setdefault('chem_cpl_steps', '')
        ddef.setdefault('surf_cpl_steps', '')
        ddef.setdefault('post_steps', '')
        ddef.setdefault('restart_steps', '')
        ddef.setdefault('stats_steps', '')
        # Generic transform
        for k in ('source_app', 'source_conf', 'source_cutoff', 'source_model', 'source_geometry'):
            if k not in ddef:
                raise MocageDomainsConfError('The {:s} key is missing in the {!s} domain definition'.format(k, dname))
            ddef[k] = self._item_transform(ddef[k])
        # Generic transform + Period cast
        for k in ('atm_cpl_delta', 'chem_cpl_delta', 'surf_cpl_delta'):
            ddef[k] = self._item_transform(ddef[k], cast=Period)
        # Deal with any steps
        for k in ('post_steps', 'restart_steps', 'stats_steps', 'atm_cpl_steps',
                  'surf_cpl_steps', 'chem_cpl_steps' ):
            ddef[k] = self._item_transform(ddef[k],
                                           validcb=self._any_steps_validation,
                                           validmsg='any_steps should be parsable by timerangex')
        try:
            ddef_tuple = MocageDomainInfo(** ddef)
        except TypeError:
            raise MocageDomainsConfError("Unable to create the domain's configuration object " +
                                         "(some data are probably missing or misspelled).")
        self.domains[dname] = ddef_tuple

    @_add_cutoff_hh_doc
    def all_active(self, cutoff, hh):
        """The list of all active domains."""
        return [d for d in self.actives[cutoff][hh]]

    @_add_cutoff_hh_doc
    def first_active(self, cutoff, hh):
        """The first active domain."""
        return self.actives[cutoff][hh][0]

    @_add_cutoff_hh_doc
    def grep_active(self, cutoff, hh, *candidates):
        """Filter the **candidates** list in order to retain only active domains."""
        domains = list()
        all_active = self.all_active(cutoff, hh)
        for c in candidates:
            if isinstance(c, (list, tuple)):
                domains.extend([k for k in c if k in all_active])
            else:
                if c in all_active:
                    domains.append(c)
        return domains

    @_add_cutoff_hh_doc
    def group(self, cutoff, hh, domains, active=True):
        """
        Returns a :class:`MocageMixedDomainsInfo` object allowing to access jointly
        configuration data of all the domains listed in **domains**.
        """
        flat_domains = self.ontime_domains(cutoff, hh)
        domains = self.grep_active(cutoff, hh, domains) if active else domains
        return MocageMixedDomainsInfo([flat_domains[d] for d in domains],
                                      self.finalterms[cutoff][hh])

    def _domain_dict_from_entry(self, cutoff, hh, entry):
        return dict(geometry={d: getattr(v, entry)[cutoff][hh] for d, v in self.domains.items()})

    def __getattr__(self, name):
        if name in _PluralisedMocageDomainInfoBase_keys:
            iname = _PluralisedMocageDomainInfoBase_keys.index(name)
            sname = _MocageDomainInfoBase_keys[iname]

            def _attr_access(cutoff, hh):
                return self._domain_dict_from_entry(cutoff, hh, sname)
            return _attr_access
        else:
            raise AttributeError(name)

    def _domain_any_cpl_date(self, cutoff, hh, curdate, entry):
        curdate = Date(curdate)
        return dict(geometry={d: curdate - getattr(v, entry)[cutoff][hh]
                              for d, v in self.domains.items()})

    @_add_cutoff_hh_doc
    def atm_cpl_dates(self, cutoff, hh, curdate):
        """The geometry/atm_cpl_date :mod:`footprints`' substitution dictionary."""
        return self._domain_any_cpl_date(cutoff, hh, curdate, 'atm_cpl_delta')

    @_add_cutoff_hh_doc
    def chem_cpl_dates(self, cutoff, hh, curdate):
        """The geometry/chem_cpl_date :mod:`footprints`' substitution dictionary."""
        return self._domain_any_cpl_date(cutoff, hh, curdate, 'chem_cpl_delta')

    @_add_cutoff_hh_doc
    def surf_cpl_dates(self, cutoff, hh, curdate):
        """The geometry/surf_cpl_date :mod:`footprints`' substitution dictionary."""
        return self._domain_any_cpl_date(cutoff, hh, curdate, 'surf_cpl_delta')

    def _expand_any_steps(self, ddef, entry, cutoff, hh, shift):
        rangestr = getattr(ddef, entry)[cutoff][hh]
        if rangestr:
            if not isinstance(rangestr, (list, tuple)):
                rangestr = (rangestr, )
            actual_finalterm_str = str(self.finalterms[cutoff][hh])
            return timerangex(",".join([rs.replace('finalterm',
                                                   actual_finalterm_str) for rs in rangestr]),
                              shift=shift)
        else:
            return []

    def _domain_any_steps(self, cutoff, hh, entry, start, end,
                          shift=False, final=True, first=True):
        start = Time(0) if start is None else Time(start)
        if end is None:
            end = self.finalterms[cutoff][hh]
        else:
            end = Time(end)
        dentry = entry.replace('steps', 'delta')
        subdict = dict()
        for d, v in self.domains.items():
            dshift = getattr(v, dentry, Time(0))[cutoff][hh] if shift else Time(0)
            subdict[d] = list(filter(lambda t: ((t - dshift > start) and (t - dshift < end)) or
                                               (final and t - dshift == end) or
                                               (first and t - dshift == start),
                                     self._expand_any_steps(v, entry, cutoff, hh, dshift)))
        return dict(geometry=subdict)

    @_add_start_end_doc
    @_add_cutoff_hh_doc
    def atm_cpl_steps(self, cutoff, hh, start=0, end=None, final=True, first=True):
        """The geometry/atm_cpl_steps :mod:`footprints`' substitution dictionary."""
        return self._domain_any_steps(cutoff, hh, 'atm_cpl_steps', start, end,
                                      final=final, first=first)

    @_add_start_end_doc
    @_add_cutoff_hh_doc
    def surf_cpl_steps(self, cutoff, hh, start=0, end=None, final=True, first=True):
        """The geometry/surf_cpl_steps :mod:`footprints`' substitution dictionary."""
        return self._domain_any_steps(cutoff, hh, 'surf_cpl_steps', start, end,
                                      final=final, first=first)

    @_add_start_end_doc
    @_add_cutoff_hh_doc
    def chem_cpl_steps(self, cutoff, hh, start=0, end=None, final=True, first=True):
        """The list of time for chem_cpl_steps :mod:`footprints`' substitution dictionary."""
        return self._domain_any_steps(cutoff, hh, 'chem_cpl_steps', start, end,
                                      final=final, first=first)

    @_add_start_end_doc
    @_add_cutoff_hh_doc
    def atm_cpl_shiftedsteps(self, cutoff, hh, start=0, end=None, final=True, first=True):
        """The geometry/shifted atm_cpl_steps :mod:`footprints`' substitution dictionary."""
        return self._domain_any_steps(cutoff, hh, 'atm_cpl_steps', start, end,
                                      shift=True, final=final, first=first)

    @_add_start_end_doc
    @_add_cutoff_hh_doc
    def surf_cpl_shiftedsteps(self, cutoff, hh, start=0, end=None, final=True, first=True):
        """The geometry/shifted surf_cpl_steps :mod:`footprints`' substitution dictionary."""
        return self._domain_any_steps(cutoff, hh, 'surf_cpl_steps', start, end,
                                      shift=True, final=final, first=first)

    @_add_start_end_doc
    @_add_cutoff_hh_doc
    def chem_cpl_shiftedsteps(self, cutoff, hh, start=0, end=None, final=True, first=True):
        """The geometry/shifted chem_cpl_steps :mod:`footprints`' substitution dictionary."""
        return self._domain_any_steps(cutoff, hh, 'chem_cpl_steps', start, end,
                                      shift=True, final=final, first=first)

    def _domain_any_freq(self, cutoff, hh, entry, start):
        start = Time(0) if start is None else Time(start)
        cpl_steps = getattr(self, entry)(cutoff, hh, start, end=None, final=True, first=True)
        cpl_steps = cpl_steps['geometry'][self.first_active(cutoff, hh)]
        return Period(cpl_steps[1] - cpl_steps[0])

    @_add_cutoff_hh_doc
    def atm_cpl_firstfreq(self, cutoff, hh, start=0):
        """
        The atm coupling frequency at the begining of the coupling period for the
        first active domain.

        :param bronx.stdtypes.date.Time start: the series of steps starts at...
        """
        return self._domain_any_freq(cutoff, hh, 'atm_cpl_steps', start)

    @_add_cutoff_hh_doc
    def surf_cpl_firstfreq(self, cutoff, hh, start=0):
        """
        The surf coupling frequency at the begining of the coupling period for the
        first active domain.

        :param bronx.stdtypes.date.Time start: the series of steps starts at...
        """
        return self._domain_any_freq(cutoff, hh, 'surf_cpl_steps', start)

    @_add_cutoff_hh_doc
    def chem_cpl_firstfreq(self, cutoff, hh, start=0):
        """
        The chem coupling frequency at the begining of the coupling period for the
        first active domain.

        :param bronx.stdtypes.date.Time start: the series of steps starts at...
        """
        return self._domain_any_freq(cutoff, hh, 'chem_cpl_steps', start)

    @_add_start_end_doc
    @_add_cutoff_hh_doc
    def post_steps(self, cutoff, hh, start=0, end=None, final=True, first=True):
        """The list of time for post_steps :mod:`footprints`' substitution dictionary."""
        return self._domain_any_steps(cutoff, hh, 'post_steps', start, end,
                                      final=final, first=first)

    @_add_start_end_doc
    @_add_cutoff_hh_doc
    def restart_steps(self, cutoff, hh, start=0, end=None, final=True, first=True):
        """The list of time for restart_steps :mod:`footprints`' substitution dictionary."""
        return self._domain_any_steps(cutoff, hh, 'restart_steps', start, end,
                                      final=final, first=first)

    @_add_start_end_doc
    @_add_cutoff_hh_doc
    def stats_steps(self, cutoff, hh, start=0, end=None, final=True, first=True):
        """The list of time for stats_steps :mod:`footprints`' substitution dictionary."""
        return self._domain_any_steps(cutoff, hh, 'stats_steps', start, end,
                                      final=final, first=first)


class CutoffHhMocageDomainsConfTool(ConfTool):
    """
    This class acts as a wrapper around a :class:`MocageDomainsConfTool` object.

    Its footprint need a **parentconf** :class:`MocageDomainsConfTool` object
    and wait for **cutoff** and **hh** attributes. Therefore, one can call upon
    this class every method defined in the :class:`MocageDomainsConfTool` class but
    without having to specify the *cutoff* and *hh* arguments that will be
    automatically added.

    The **actives**, **finalterms** and **domains** properties can also be
    accessed but the returned values will only contain information for the
    *cutoff* and basetime (*hh*) prescribed at the object's creation time
    (through the footprint).
    """

    _footprint = [
        v_stdattrs.cutoff,
        dict(
            info = 'Conf tool that handles the configuration of Mocage domains',
            attr = dict(
                kind = dict(
                    values= ['mocagedomains', ],
                ),
                parentconf = dict(
                    info = ' The general configuration and configuration of each individual Mocage domain',
                    type = MocageDomainsConfTool,
                ),
                hh = dict(
                    info = 'The current basetime',
                    type = Time,
                ),
            )
        )
    ]

    def __init__(self, *kargs, **kwargs):
        """
        :example: see the :class:`MocageDomainsConfTool` class documentation.
        """
        super(CutoffHhMocageDomainsConfTool, self).__init__(*kargs, **kwargs)
        self._cache = dict()

    def __getattr__(self, name):
        """Provides the wrapper service..."""
        if name.startswith('_'):
            raise AttributeError()
        if name in self._cache:
            return self._cache[name]
        elif name in ('actives', 'active'):
            a = self.parentconf.actives[self.cutoff][self.hh]
            self._cache.update({k: a for k in ('actives', 'active')})
            return a
        elif name in ('finalterms', 'finalterm'):
            f = self.parentconf.finalterms[self.cutoff][self.hh]
            self._cache.update({k: f for k in ('finalterms', 'finalterm')})
            return f
        elif name == 'domains':
            self._cache['domains'] = self.parentconf.ontime_domains(self.cutoff, self.hh)
            return self._cache['domains']
        elif callable(getattr(self.parentconf, name, None)):
            self._cache[name] = functools.partial(getattr(self.parentconf, name),
                                                  self.cutoff, self.hh)
            return self._cache[name]
        else:
            raise AttributeError()


class MocageMixedDomainsInfo(object):
    """
    Returns configuration data that are common to several **subdomains** for a
    given cutoff and basetime (hh).

    Do not create, these object manually. Use the ``group`` methods of the
    :class:`MocageDomainConfTool` or :class:`CutoffHhMocageDomainConfTool`
    objects.
    """

    def __init__(self, subdomains, finalterm):
        """
        :param subdomains: A list of :class:`MocageDomainInfo` objects to be grouped
        :param finalterm: The final term
        """
        self._subdomains = subdomains
        self.finalterm = finalterm

    def __getattr__(self, name):
        return self._get_mixeddomains_attr(name)

    def _get_mixeddomains_attr(self, name):
        stuff = set()
        for s_attr in [getattr(s, name) for s in self._subdomains]:
            stuff.add(tuple(s_attr) if isinstance(s_attr, list) else s_attr)
        if len(stuff) > 1:
            raise AttributeError('Inconsistent {:s} values among subdomains'.format(name))
        return stuff.pop()

    def atm_cpl_date(self, curdate):
        """The date of the atmospheric coupling data (given the current date **curdate**)."""
        return Date(curdate) - self.atm_cpl_delta

    def surf_cpl_date(self, curdate):
        """The date of the surface coupling data (given the current date **curdate**)."""
        return Date(curdate) - self.surf_cpl_delta

    def chem_cpl_date(self, curdate):
        """The date of the surface coupling data (given the current date **curdate**)."""
        return Date(curdate) - self.chem_cpl_delta

    def _expand_any_steps(self, entry, shift):
        rangestr = self._get_mixeddomains_attr(entry)
        if rangestr:
            if not isinstance(rangestr, (list, tuple)):
                rangestr = (rangestr, )
            return timerangex(",".join([rs.replace('finalterm',
                                                   str(self.finalterm)) for rs in rangestr]),
                              shift=shift)
        else:
            return []

    def _domain_any_steps(self, entry, start, end, shift=False, final=True, first=True):
        start = Time(0) if start is None else Time(start)
        end = Time(self.finalterm) if end is None else Time(end)
        dentry = entry.replace('steps', 'delta')
        dshift = getattr(self, dentry, Time(0)) if shift else Time(0)
        return list(filter(lambda t: (((t - dshift > start) and (t - dshift < end)) or
                                      (final and t - dshift == end) or
                                      (first and t - dshift == start)),
                           self._expand_any_steps(entry, dshift)))

    @_add_start_end_doc
    def atm_cpl_steps(self, start=0, end=None, final=True, first=True):
        """The atm_cpl_steps of coupling data."""
        return self._domain_any_steps('atm_cpl_steps', start, end,
                                      final=final, first=first)

    @_add_start_end_doc
    def surf_cpl_steps(self, start=0, end=None, final=True, first=True):
        """The surf_cpl_steps of coupling data."""
        return self._domain_any_steps('surf_cpl_steps', start, end,
                                      final=final, first=first)

    @_add_start_end_doc
    def chem_cpl_steps(self, start=0, end=None, final=True, first=True):
        """The surf_cpl_steps of coupling data."""
        return self._domain_any_steps('chem_cpl_steps', start, end,
                                      final=final, first=first)

    @_add_start_end_doc
    def atm_cpl_shiftedsteps(self, start=0, end=None, final=True, first=True):
        """The sifted surf_cpl_steps of coupling data."""
        return self._domain_any_steps('atm_cpl_steps', start, end,
                                      shift=True, final=final, first=first)

    @_add_start_end_doc
    def surf_cpl_shiftedsteps(self, start=0, end=None, final=True, first=True):
        """The geometry/shifted surf_cpl_steps :mod:`footprints`' substitution dictionary."""
        return self._domain_any_steps('surf_cpl_steps', start, end,
                                      shift=True, final=final, first=first)

    @_add_start_end_doc
    def chem_cpl_shiftedsteps(self, start=0, end=None, final=True, first=True):
        """The geometry/shifted chem_cpl_steps :mod:`footprints`' substitution dictionary."""
        return self._domain_any_steps('chem_cpl_steps', start, end,
                                      shift=True, final=final, first=first)

    @_add_start_end_doc
    def post_steps(self, start=0, end=None, final=True, first=True):
        """The list of time for post_steps :mod:`footprints`' substitution dictionary."""
        return self._domain_any_steps('post_steps', start, end,
                                      final=final, first=first)

    @_add_start_end_doc
    def restart_steps(self, start=0, end=None, final=True, first=True):
        """The list of time for restart_steps :mod:`footprints`' substitution dictionary."""
        return self._domain_any_steps('restart_steps', start, end,
                                      final=final, first=first)

    @_add_start_end_doc
    def stats_steps(self, start=0, end=None, final=True, first=True):
        """The list of time for stats_steps :mod:`footprints`' substitution dictionary."""
        return self._domain_any_steps('stats_steps', start, end,
                                      final=final, first=first)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
