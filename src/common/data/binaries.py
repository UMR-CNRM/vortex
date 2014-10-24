#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []


from vortex.data.executables import BlackBox, NWPModel
from gco.syntax.stdattrs import GenvKey


class IFSModel(NWPModel):
    """Yet an other IFS Model."""

    _footprint = dict(
        info = 'IFS Model',
        attr = dict(
            gvar = dict(
                type = GenvKey,
                optional = True,
                default = 'master_[model]'
            ),
            kind = dict(
                values = ['ifsmodel', 'mfmodel'],
            ),
            model = dict(
                outcast = ['aladin', 'arome'],
            ),
        )
    )

    @property
    def realkind(self):
        return 'ifsmodel'

    def iga_pathinfo(self):
        """Standard path information for IGA inline cache."""
        return dict(
            model = self.model
        )

    def iga_basename(self):
        """Standard expected basename for IGA inline cache."""
        return 'ARPEGE'

    def command_line(self, model=None, vmodel='meteo',
                     name='XRUN', conf=1, timescheme='sli',
                     timestep=600, fcterm=0, fcunit='h'):
        """Build command line for execution as a single string."""
        if model:
            return '-v{0:s} -e{1:s} -c{2:d} -a{3:s} -t{4:g} -f{5:s}{6:d} -m{7:s}'.format(
                vmodel, name, conf, timescheme, timestep, fcunit, fcterm, model
            )
        else:
            return '-v{0:s} -e{1:s} -c{2:d} -a{3:s} -t{4:g} -f{5:s}{6:d}'.format(
                vmodel, name, conf, timescheme, timestep, fcunit, fcterm
            )


class Aladin(IFSModel):
    """Dedicated to local area model."""

    _footprint = dict(
        info = 'ALADIN / AROME Local Area Model',
        attr = dict(
            model = dict(
                values = ['aladin', 'arome'],
            ),
        )
    )

    def command_line(self, **kw):
        """Enforce aladin model option."""
        kw['model'] = 'aladin'
        return super(Aladin, self).command_line(**kw)


class ProGrid(BlackBox):
    """A tool for grib conversion."""

    _footprint = dict(
         info = 'ProGrid utility for grib conversion',
        attr = dict(
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'master_progrid'
            ),
            kind = dict(
                values   = ['progrid', 'gribtool'],
                remap    = dict(gribtool = 'progrid'),
            ),
        )
    )

    @property
    def realkind(self):
        return 'progrid'


class ProTool(BlackBox):
    """A tool for adding fields on FA objects."""

    _footprint = dict(
         info = 'ProTool utility for field manipulation',
        attr = dict(
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'master_addsurf'
            ),
            kind = dict(
                values   = [ 'protool', 'addsurf' ],
                remap    = dict(addsurf = 'protool'),
            ),
        )
    )

    @property
    def realkind(self):
        return 'protool'


class IOAssign(BlackBox):
    """A tool for ODB pools mapping."""

    _footprint = dict(
         info = 'ProTool utility for field manipulation',
        attr = dict(
            kind = dict(
                values   = ['ioassign', 'odbioassign'],
                remap    = dict(odbioassign = 'ioassign'),
            ),
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'master_ioassign'
            ),
            iotool = dict(
                optional = True,
                default  = 'create_ioassign',
                access   = 'rwx',
            ),
        )
    )

    @property
    def realkind(self):
        return 'ioassign'


class Batodb(BlackBox):
    """A tool for conversion to ODB format."""

    _footprint = dict(
         info = 'Batodb conversion program',
        attr = dict(
            kind = dict(
                values   = ['bator', 'batodb'],
                remap    = dict(bator = 'batodb'),
            ),
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'master_batodb'
            ),
        )
    )

    @property
    def realkind(self):
        return 'batodb'
