#!/usr/bin/env python
# -*- coding: utf-8 -*-
from vortex.data.geometries import HorizontalGeometry
from vortex.data.resources import Resource

#: No automatic export
__all__ = []

import copy

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.tools.date        import Date, Time
from vortex.data.flow         import FlowResource, GeoFlowResource
from vortex.data.contents     import JsonDictContent, TextContent
from vortex.syntax.stdattrs   import FmtInt, a_date, a_term
from common.data.modelstates  import Historic


class PerturbedState(Historic):
    """
    Class for numbered historic resources, for example perturbations or perturbed states of the EPS.
    """

    _footprint = dict(
        info = 'Perturbation or perturbed state',
        attr = dict(
            kind = dict(
                values  = ['perturbation', 'perturbed_historic', 'perturbed_state', 'pert'],
                remap = dict(autoremap = 'first')
            ),
            number = dict(
                type    = FmtInt,
                args    = dict(fmt = '03'),
            ),
            term = dict(
                type = Time,
                optional = True,
                default = Time(0)
            ),
            processing = dict(
                values = ['unit', 'normed'],
                optional = True,
            ),
        )
    )

    @property
    def realkind(self):
        return 'pert'

    def basename_info(self):
        """Generic information for names fabric."""
        pr_transform = {'unit': 'u', 'normed': 'n'}
        d = super(PerturbedState, self).basename_info()
        d['number'] = self.number
        d['radical'] = pr_transform.get(self.processing, '') + self.realkind
        return d

    def olive_basename(self):
        """OLIVE specific naming convention."""
        raise NotImplementedError("Perturbations were previously tar files, not supported yet.")

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        raise NotImplementedError("Perturbations were previously tar files, not supported yet.")


class SingularVector(Historic):
    """
    Generic class for resources internal to singular vectors.
    """
    _footprint = dict(
        info = 'Singular vector',
        attr = dict(
            kind = dict(
                values  = ['svector'],
            ),
            number = dict(
                type    = FmtInt,
                args    = dict(fmt = '03'),
            ),
            zone = dict(
                values  = ['ateur', 'hnc', 'hs', 'pno', 'oise', 'an', 'pne',
                           'oiso', 'ps', 'oin', 'trop1', 'trop2', 'trop3', 'trop4'],
            ),
            term = dict(
                type = Time,
                optional = True,
                default = Time(0)
            ),
            optime = dict(
                type = Time,
                optional = True,
            )
        )
    )

    @property
    def realkind(self):
        return 'svector'

    def basename_info(self):
        """Generic information for names fabric."""
        d = super(SingularVector, self).basename_info()
        d['number'] = self.number
        d['radical'] = self.realkind + '-' + self.zone
        return d

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'SVARPE'  + '{0:03d}'.format(self.number) + '+0000'

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return 'SVARPE'  + '{0:03d}'.format(self.number) + '+0000'


class NormCoeff(FlowResource):
    """
    Coefficient used to normalize the singular vectors or the bred modes.
    """

    _footprint = dict(
        info = 'Perturbations coefficient',
        attr = dict(
            kind = dict(
                values   = ['coeffnorm', 'coeffpert'],
                remap = dict(autoremap = 'first'),
            ),
            clscontents = dict(
                default = JsonDictContent,
            ),
            nativefmt   = dict(
                values  = ['json'],
                default = 'json',
            ),
            pertkind     = dict(
                values   = ['sv', 'bd'],
                optional = True,
                default  = 'sv',
            ),
        )
    )

    @property
    def realkind(self):
        return 'coeff' + self.pertkind

    def basename_info(self):
        """Generic information for names fabric."""
        return dict(
            radical = self.realkind,
            fmt     = self.nativefmt,
            src     = [self.model],
        )


class SampleContent(JsonDictContent):
    """Specialisation of the JSONDictContent to deal with drawing lots."""

    def drawing(self, g, x):
        """Return the number of a sampled element according to the local number."""
        n = g.get('number', x.get('number', None))
        virgin = g.get('untouched', x.get('untouched', [0, ]))
        if n is None:
            return None
        else:
            try:
                if not isinstance(virgin, list):
                    virgin = [int(virgin)]
                else:
                    virgin = map(int, virgin)
                n = int(n)
            except TypeError:
                return None
            if n in virgin:
                return n
            else:
                try:
                    return self.data['drawing'][n - 1]
                except KeyError:
                    return None

    def __getattr__(self, attr):
        # Return an access function that corresponds to the key
        drawing_keys = set([item
                            for d in self.data.get('drawing', []) if isinstance(d, dict)
                            for item in d.keys()])
        if attr in drawing_keys:
            def _attr_access(g, x):
                elt = self.drawing(g, x)
                # drawing may returns
                # * None (if the 'number' attribute is incorrect or missing)
                # * An integer if 'number' is in the 'untouched' list
                # * A dictionary
                if elt is None:
                    choices = set([d[attr] for d in self.data['drawing']])
                    return None if len(choices) > 1 else choices.pop()
                else:
                    return elt[attr] if isinstance(elt, dict) else None
            return _attr_access
        # Returns the list of drawn keys
        listing_keys = set([item + 's'
                            for d in self.data.get('drawing', []) if isinstance(d, dict)
                            for item in d.keys()])
        if attr in listing_keys:
            return [d[attr[:-1]] for d in self.data['drawing']]
        # Return the list of available keys
        listing_keys = set([item + 's'
                            for d in self.data['population'] if isinstance(d, dict)
                            for item in d.keys()])
        if attr in listing_keys:
            return [d[attr[:-1]] for d in self.data['population']]
        raise AttributeError()

    def timedelta(self, g, x):
        """Find the time difference between the resource's date and the targetdate."""
        targetdate = g.get('targetdate', x.get('targetdate', None))
        if targetdate is None:
            raise ValueError("A targetdate attribute must be present if timedelta is used")
        targetdate = Date(targetdate)
        targetterm = Time(g.get('targetterm', x.get('targetterm', 0)))
        thedate = Date(self.date(g, x))
        period = (targetdate + targetterm) - thedate
        return str(period.time())

    def _actual_diff(self, ref):
        me = copy.copy(self.data)
        other = copy.copy(ref.data)
        me.pop('experiment', None)  # Do not compare the experiment ID (if present)
        other.pop('experiment', None)
        return me == other


class PopulationList(FlowResource):
    """
    Description of available data
    """

    _abstract = True
    _footprint = dict(
        info = 'A Population List',
        attr = dict(
            clscontents = dict(
                default = SampleContent,
            ),
            nativefmt   = dict(
                values  = ['json'],
                default = 'json',
            ),
            nbsample = dict(
                optional = True,
                type = int,
            ),
            checkrole = dict(
                optional = True
            )
        )
    )

    def basename_info(self):
        """Generic information for names fabric."""
        return dict(
            radical = self.realkind,
            fmt     = self.nativefmt,
        )


class MembersPopulation(PopulationList):

    _footprint = dict(
        info = 'Members population',
        attr = dict(
            kind = dict(
                values   = ['mbpopulation', ],
            ),
        )
    )

    @property
    def realkind(self):
        return 'mbpopulation'


class Sample(PopulationList):
    """
    Lot drawn out of a set.
    """

    _abstract = True,
    _footprint = dict(
        info = 'Sample',
        attr = dict(
            nbsample = dict(
                optional = False,
            ),
            population = dict(
                type = footprints.stdtypes.FPList,
                optional = True
            ),
        )
    )

    def basename_info(self):
        """Generic information for names fabric."""
        return dict(
            radical = self.realkind + 'of{:d}'.format(self.nbsample),
            fmt     = self.nativefmt,
        )


class MembersSample(Sample):
    """
    List of members selected among a set.
    """

    _footprint = dict(
        info = 'Members sample',
        attr = dict(
            kind = dict(
                values   = ['mbsample', 'mbselect', 'mbdrawing', 'members_select'],
                remap = dict(autoremap = 'first'),
            ),
        )
    )

    @property
    def realkind(self):
        return 'mbsample'


class MultiphysicsSample(Sample):
    """
    List of physical packages selected among a set.
    """

    _footprint = dict(
        info = 'Physical packages sample',
        attr = dict(
            kind = dict(
                values   = ['physample', 'physelect', 'phydrawing'],
                remap = dict(autoremap = 'first'),
            ),
        )
    )

    @property
    def realkind(self):
        return 'physample'


class ClustContent(TextContent):
    """Specialisation of the TextContent to deal with clustering outputs."""

    def getNumber(self, idx):
        return self.data[idx - 1]


class GeneralCluster(FlowResource):
    """
    Files produced by the clustering step of the LAM PE.
    """

    _footprint = dict(
        abstract = True,
        info = 'Clustering stuff',
        attr = dict(
            kind = dict(
                values   = ['clustering', 'clust', 'members_select'],
                remap = dict(autoremap = 'first'),
            ),
            clscontents = dict(
                default = ClustContent,
            ),
            nativefmt = dict(
                values   = ['ascii', 'txt'],
                default  = 'txt',
                remap    = dict(ascii = 'txt'),
            ),
            filling = dict(
                values   = ['population', 'pop', 'members'],
                remap    = dict(population = 'pop'),
                default  = '',
            ),
        )
    )

    @property
    def realkind(self):
        return 'clustering' + '_' + self.filling

    def basename_info(self):
        """Generic information for names fabric."""
        return dict(
            radical = self.realkind,
            fmt     = self.nativefmt,
        )


class Score(GeoFlowResource):
    """
    Files produced to contain the scores.
    """

    _footprint = dict(
        info = 'Ensemble scores',
        attr = dict(
            kind = dict(
                values   = ['score'],
            ),
            clscontents = dict(
                default = JsonDictContent,
            ),
            nativefmt = dict(
                values   = ['json'],
                optional = True,
                default  = 'json',
            ),
            term = a_term,
            score = dict(
                type   = str,
            ),
            parameter = dict(
                type   = str,
            ),
            level = dict(
                type   = str,
            ),
            event = dict(
                optional = True,
                type   = str,
            ),
        )
    )

    @property
    def realkind(self):
        return self.score

    def basename_info(self):
        """Generic information for names fabric."""
        radsocle = self.realkind + '_' + self.parameter + self.level
        if self.event is not None: radsocle += ('_' + self.event)
        return dict(
            radical = radsocle,
            fmt     = self.nativefmt,
            geo     = self.geometry.area,
            term    = self.term,
            src     = self.model,
        )


class GraphicScore(Resource):
    """
    Files produced to contain the scores.
    """

    _footprint = dict(
        info = 'Ensemble scores',
        attr = dict(
            date = a_date,
            kind = dict(
                values   = ['score'],
            ),
            geometry = dict(
                type = HorizontalGeometry,
            ),
            nativefmt = dict(
                values   = ['pdf'],
                optional = True,
                default  = 'pdf',
            ),
            score = dict(
                type   = str,
            ),
            calcul = dict(
                type   = str,
            ),
            parameter = dict(
                type   = str,
            ),
            level = dict(
                type   = str,
            ),
            term = dict(
                type     = Time,
                optional = True,
            )
        )
    )

    @property
    def realkind(self):
        return self.calcul + '_' + self.score

    def basename_info(self):
        """Generic information for names fabric."""
        dico = dict(
            radical = self.realkind + '_' + self.parameter + self.level,
            fmt     = self.nativefmt,
            geo     = self.geometry.area,
        )
        if hasattr(self, 'term'):
            dico['term'] = self.term
        return dico

    def vortex_pathinfo(self):
        """Default path informations (used by :class:`vortex.data.providers.Vortex`)."""
        return dict(
            nativefmt = self.nativefmt,
            date      = self.date,
            cutoff    = '',
            geometry  = self.geometry
        )

    def footprint_export_geometry(self):
        """Return the ``geometry`` attribute as its id tag."""
        return self.geometry.tag


class Obset(Resource):
    """
    Files produced to contain the extracted obs sets.
    """

    _footprint = dict(
        info = 'Observation sets',
        attr = dict(
            kind = dict(
                values   = ['obset'],
            ),
            date = a_date,
            geometry = dict(
                type = HorizontalGeometry,
            ),
            nativefmt = dict(
                values   = ['ascii'],
                optional = True,
                default  = 'ascii',
            ),
            parameter = dict(
                type   = str,
            ),
            window = dict(
                type   = int,
            ),
        )
    )

    @property
    def realkind(self):
        return 'obset'

    def basename_info(self):
        """Generic information for names fabric."""
        return dict(
            radical = self.realkind + '_' + self.parameter + '_' + str(self.window),
            fmt     = self.nativefmt,
            geo     = self.geometry.area,
        )

    def vortex_pathinfo(self):
        """Default path informations (used by :class:`vortex.data.providers.Vortex`)."""
        return dict(
            nativefmt = self.nativefmt,
            date      = self.date,
            cutoff    = '',
            geometry  = self.geometry
        )

    def footprint_export_geometry(self):
        """Return the ``geometry`` attribute as its id tag."""
        return self.geometry.tag
