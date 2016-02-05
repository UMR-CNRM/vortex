#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.tools.date        import Time
from vortex.data.flow         import FlowResource
from vortex.data.contents     import JsonDictContent, TextContent
from vortex.syntax.stdattrs   import FmtInt
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
        virgin = g.get('untouched', x.get('untouched', []))
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
                return self.data['drawing'][n - 1]


class Sample(FlowResource):
    """
    Lot drawn out of a set.
    """

    _abstract = True,
    _footprint = dict(
        info = 'Sample',
        attr = dict(
            clscontents = dict(
                default = SampleContent,
            ),
            nativefmt   = dict(
                values  = ['json'],
                default = 'json',
            ),
            nblot = dict(
                type = int,
            ),
            nbset = dict(
                type = int,
            ),
        )
    )

    def basename_info(self):
        """Generic information for names fabric."""
        return dict(
            radical = self.realkind + '.{:d}outof{:d}'.format(self.nblot, self.nbset),
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
