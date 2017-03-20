#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: Automatic export off
__all__ = []


import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.tools.date      import Time

from vortex.data.flow       import FlowResource, GeoFlowResource
from vortex.data.contents   import JsonDictContent
from vortex.syntax.stdattrs import FmtInt, term
from gco.syntax.stdattrs    import gvar


class _BackgroundErrorInfo(GeoFlowResource):
    """
    A generic class for data in grib format related to the background error.
    """

    _abstract = True
    _footprint = [
        term,
        gvar,
        dict(
            info='Background standard deviation',
            attr=dict(
                term=dict(
                    optional=True,
                    values=[3, 6, 9, 12],
                    default=3
                ),
                nativefmt=dict(
                    default='grib',
                ),
                gvar = dict(
                    default = 'errgrib_t[geometry:truncation]'
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return 'bgstdinfo'

    def basename_info(self):
        """Generic information for names fabric, with radical = ``bcor``."""
        return dict(
            radical = self.realkind,
            geo     = [{'truncation': self.geometry.truncation}],
            fmt     = self.nativefmt,
            src     = [self.model, ],
            term    = self.term.fmthm,
        )


class BackgroundStdError(_BackgroundErrorInfo):
    """Background error standard deviation.

    stage: 
        * unbal/vor: unbalanced variables fields
        * scr: obs. related fields
        * profile: full variables global and latitude bands horizontal averages
        * full: full variables fields

    origin: 
        * ens: diagnosed from an ensemble
        * diag: diagnosed from randomized (a priori climatological) covariances

    """

    _footprint = [
        dict(
            info='Background error standard deviation',
            attr=dict(
                kind=dict(
                    values=['bgstderr', 'bg_stderr', 'bgerrstd'],
                    remap=dict(autoremap='first'),
                ),
                stage=dict(
                    optional=True,
                    default='unbal',
                    values=['scr', 'vor', 'full', 'unbal', 'profile'],
                    remap=dict(vor='unbal'),
                ),
                origin=dict(
                    optional=True,
                    values=['ens', 'diag'],
                    default = 'ens',
                ),
                gvar = dict(
                    default = 'errgrib_vor_monthly'
                ),
                nativefmt=dict(
                    values=['grib', 'ascii'],
                    default='grib',
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return 'bgstderr'

    def basename_info(self):
        """Generic information for names fabric, with radical = ``bcor``."""
        infos = super(BackgroundStdError, self).basename_info()
        infos['src'].append(self.stage)
        if self.stage != 'scr':
            infos['src'].append(self.origin)
        return infos

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        if self.stage in ('unbal',):
            return '(errgribfix:igakey)'
        else:
            return 'errgrib_' + self.stage

    def olive_basename(self):
        """OLIVE specific naming convention."""
        if self.stage in ('unbal',):
            return 'errgribvor'
        else:
            return 'sigma_b'

    def gget_basename(self):
        """GGET specific naming convention."""
        return '.m{:02d}'.format(self.date.month)


class BackgroundErrorNorm(_BackgroundErrorInfo):
    """
    Background error normalisation data for wavelet covariances.
    """

    _footprint = [
        dict(
            info='Background error normalisation data for wavelet covariances',
            attr=dict(
                kind=dict(
                    values=['bgstdrenorm', 'bgerrnorm'],
                    remap=dict(autoremap='first'),
                ),
                gvar = dict(
                    default = 'srenorm_t[geometry:truncation]'
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return 'bgstdrenorm'

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return 'srenorm.' + str(self.geometry.truncation)

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'srenorm.t' + str(self.geometry.truncation)

    def archive_pathinfo(self):
        """OpArchive specific pathname needs."""
        return dict(
            nativefmt = self.nativefmt,
            model     = self.model,
            date      = self.date,
            cutoff    = self.cutoff,
            directory = 'wavelet',
        )


class Wavelet(GeoFlowResource):
    """
    Background error wavelet covariances.
    """

    _footprint = [
        term,
        gvar,
        dict(
            info = 'Background error wavelet covariances',
            attr = dict(
                kind = dict(
                    values   = ['wavelet', 'waveletcv'],
                    remap    = dict(autoremap = 'first'),
                ),
                gvar = dict(
                    default = 'wavelet_cv_t[geometry:truncation]'
                ),
                term=dict(
                    optional=True,
                    default=3
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'wavelet'

    def basename_info(self):
        """Generic information for names fabric, with radical = ``bcor``."""
        return dict(
            radical = self.realkind,
            geo     = [{'truncation': self.geometry.truncation}],
            fmt     = self.nativefmt,
            src     = [self.model],
            term    = self.term.fmthm,
        )

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return 'wavelet.cv.' + str(self.geometry.truncation)

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'wavelet.cv.t' + str(self.geometry.truncation)

    def archive_pathinfo(self):
        """OpArchive specific pathname needs."""
        return dict(
            nativefmt = self.nativefmt,
            model     = self.model,
            date      = self.date,
            cutoff    = self.cutoff,
            directory = self.realkind,
        )


class RawControlVector(GeoFlowResource):
    """
    Raw Control Vector as issued by minimisation, playing the role of an Increment.
    """

    _footprint = dict(
        info = 'Raw Control Vector',
        attr = dict(
            kind = dict(
                values   = ['rawcv', 'rcv', 'increment', 'minimcv'],
                remap    = dict(autoremap = 'first'),
            ),
        )
    )

    @property
    def realkind(self):
        return 'rawcv'

    def basename_info(self):
        """Generic information for names fabric, with radical = ``bcor``."""
        return dict(
            radical = self.realkind,
            geo     = [{'truncation': self.geometry.truncation}],
            fmt     = self.nativefmt,
            src     = [self.model],
        )

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'MININCR'


class InternalMinim(GeoFlowResource):
    """
    Generic class for resources internal to minimisation.
    """

    _abstract = True
    _footprint = dict(
        attr = dict(
            nativefmt = dict(
                values  = ['fa', 'lfi', 'grib'],
                default = 'fa',
            ),
            term = dict(
                type     = Time,
                optional = True,
                default  = Time(-3),
            ),
        )
    )

    def basename_info(self):
        """Generic information for names fabric, with radical = ``bcor``."""
        return dict(
            radical = self.realkind,
            geo     = [{'truncation': self.geometry.truncation}],
            fmt     = self.nativefmt,
            src     = [self.model],
        )

    def olive_suffixtr(self):
        """Return BR or HR specific OLIVE suffix according to geo streching."""
        return 'HR' if self.geometry.stretching > 1 else 'BR'


class StartingPointMinim(InternalMinim):
    """
    Guess as reprocessed by the minimisation.
    """

    _footprint = dict(
        info = 'Starting Point Output Minim',
        attr = dict(
            kind = dict(
                values  = ['stpmin'],
            ),
        )
    )

    @property
    def realkind(self):
        return 'stpmin'

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'STPMIN'  + self.olive_suffixtr()


class AnalysedStateMinim(InternalMinim):
    """
    Analysed state as produced by the minimisation.
    """

    _footprint = dict(
        info = 'Analysed Output Minim',
        attr = dict(
            kind = dict(
                values  = ['anamin'],
            ),
        )
    )

    @property
    def realkind(self):
        return 'anamin'

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'ANAMIN'  + self.olive_suffixtr()


class PrecevMap(FlowResource):
    """
    Map of the precondionning eigenvectors as produced by minimisation.
    """

    _footprint = dict(
        info = 'Prec EV Map',
        attr = dict(
            kind = dict(
                values   = ['precevmap'],
            ),
            clscontents = dict(
                default = JsonDictContent,
            ),
            nativefmt   = dict(
                values  = ['json'],
                default = 'json',
            ),
        )
    )

    @property
    def realkind(self):
        return 'precevmap'

    def basename_info(self):
        """Generic information for names fabric, with radical = ``bcor``."""
        return dict(
            radical = self.realkind,
            fmt     = self.nativefmt,
            src     = [self.model],
        )


class Precev(FlowResource):
    """
    Precondionning eigenvectors as produced by minimisation.
    """

    _footprint = dict(
        info = 'Starting Point Output Minim',
        attr = dict(
            kind = dict(
                values   = ['precev'],
            ),
            evnum = dict(
                type    = FmtInt,
                args    = dict(fmt = '03'),
            ),
        )
    )

    @property
    def realkind(self):
        return 'precev'

    def basename_info(self):
        """Generic information for names fabric, with radical = ``bcor``."""
        return dict(
            radical = self.realkind,
            fmt     = self.nativefmt,
            src     = [self.model, str(self.evnum)],
        )
