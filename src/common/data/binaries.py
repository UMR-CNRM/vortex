#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []


from vortex.data.executables import Script, BlackBox, NWPModel
from gco.syntax.stdattrs import GenvKey, ArpIfsSimplifiedCycle


class IFSModel(NWPModel):
    """Yet an other IFS Model."""

    _footprint = dict(
        info = 'IFS Model',
        attr = dict(
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'master_[model]'
            ),
            kind = dict(
                values   = ['ifsmodel', 'mfmodel'],
            ),
            model = dict(
                outcast  = ['aladin', 'arome'],
            ),
            cycle = dict(
                type     = ArpIfsSimplifiedCycle,
                optional = True,
                default  = 'cy40',  # For "old" Olive configurations to keep working
            )
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

    def command_line(self, model='arpifs', vmodel='meteo',
                     name='XRUN', conf=1, timescheme='sli',
                     timestep=600, fcterm=0, fcunit='h'):
        """
        Build command line for execution as a single string.
        Depending on the cycle it may returns nothing.
        """
        if self.cycle < 'cy41':
            return '-v{0:s} -e{1:s} -c{2:d} -a{3:s} -t{4:g} -f{5:s}{6:d} -m{7:s}'.format(
                vmodel, name, conf, timescheme, timestep, fcunit, fcterm, model
            )
        else:
            return ''


class Arome(IFSModel):
    """Dedicated to local area model."""

    _footprint = dict(
        info = 'ALADIN / AROME Local Area Model',
        attr = dict(
            model = dict(
                values  = ['aladin', 'arome'],
                outcast = set(),
            ),
        )
    )

    def command_line(self, **kw):
        """Enforce aladin model option."""
        kw.setdefault('model', 'aladin')
        return super(Arome, self).command_line(**kw)


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


class Odbtools(BlackBox):
    """A tool for shuffle operations in ODB format."""

    _footprint = dict(
        info = 'Odbtools shuffle program',
        attr = dict(
            kind = dict(
                values   = ['odbtools'],
            ),
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'master_odbtools'
            ),
        )
    )

    @property
    def realkind(self):
        return 'odbtools'

    def command_line(self, dbin='ECMA', dbout='CCMA', npool=1, nslot=1, fcma=None, masksize=None, date=None):
        """Build command line for execution as a single string."""
        cmdline = '-i{0:s} -o{1:s} -b1 -a{2:d} -T{3:d}'.format(dbin.upper(), dbout.upper(), npool, nslot)
        if fcma is not None:
            cmdline = cmdline + ' -F{0:s}'.format(fcma.upper())
        if masksize is not None:
            cmdline = cmdline + ' -n{0:d}'.format(int(masksize))
        if date is not None:
            cmdline = cmdline + ' -B' + date.ymdh
        return cmdline


class VarBCTool(BlackBox):
    """Well... a single minded binary for a quite explicite purpose."""

    _footprint = dict(
        info = 'VarBC merger program',
        attr = dict(
            kind = dict(
                values   = ['varbctool'],
            ),
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'master_merge_varbc'
            ),
        )
    )

    @property
    def realkind(self):
        return 'varbctool'


class LopezMix(BlackBox):
    """Some mixture for surface fields during the 3DVar assimilation process."""

    _footprint = dict(
        info = 'Surface mix',
        attr = dict(
            kind = dict(
                values   = ['lopezmix', 'lopez', 'mastsurf', 'surfmix'],
                remap    = dict(autoremap = 'first'),
            ),
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'master_surfmix'
            ),
        )
    )

    @property
    def realkind(self):
        return 'lopezmix'


class MasterDiagPI(BlackBox):
    """A binary to compute some diagnostics with aromepi's gribs."""

    _footprint = dict(
        info = 'MasterDiag utility for diagnostics computation',
        attr = dict(
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'master_diag_aromepi'
            ),
            kind = dict(
                values   = [ 'masterdiagpi' ],
            ),
        )
    )

    @property
    def realkind(self):
        return 'masterdiagpi'


class IOPoll(Script):
    """
    The IOPoll script. A Genvkey can be given.
    """
    _footprint = dict(
        info='IOPoll script',
        attr=dict(
            kind=dict(
                values=['iopoll', 'io_poll'],
                remap=dict(autoremap='first'),
            ),
            gvar=dict(
                type=GenvKey,
                optional=True,
                default='tools_io_poll',
            ),
        )
    )

    @property
    def realkind(self):
        return 'iopoll'


class LFITools(BlackBox):
    """Multipurpose tool to handle LFI/FA files."""

    _footprint = dict(
        info = 'Tool to handle LFI/FA files',
        attr = dict(
            kind = dict(
                values   = ['lfitools', ],
            ),
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'master_lfitools'
            ),
        )
    )

    @property
    def realkind(self):
        return 'lfitools'


class Combi(BlackBox):
    """Multipurpose tool to build the initial states of the ensemble prediction system."""

    _footprint = dict(
        info = 'Tool to build EPS initial conditions',
        attr = dict(
            kind = dict(
                values   = ['combi'],
            ),
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'master_combi'
            ),
        )
    )

    @property
    def realkind(self):
        return 'combi'


class Gobptout(BlackBox):
    """A tool for grib conversion on a gaussian grid."""

    _footprint = dict(
        info = 'Gobptout utility for grib conversion',
        attr = dict(
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'master_gobtout'
            ),
            kind = dict(
                values   = ['gobptout'],
            ),
        )
    )

    @property
    def realkind(self):
        return 'gobptout'


class Clust(BlackBox):
    """Tool that selects a subset of EPS members using the Clustering method."""

    _footprint = dict(
        info = 'Tool that selects a subset of EPS members using the Clustering method',
        attr = dict(
            kind = dict(
                values   = ['clust'],
            ),
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'master_clust'
            ),
        )
    )

    @property
    def realkind(self):
        return 'clust'


class PertSurf(BlackBox):
    """Tool that adds perturbations to surface fields."""

    _footprint = dict(
        info = 'Tool that adds perturbations to surface fields',
        attr = dict(
            kind = dict(
                values   = ['pertsurf'],
            ),
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'master_pertsurf'
            ),
        )
    )

    @property
    def realkind(self):
        return 'pertsurf'


class AddPearp(BlackBox):
    """Tool that adds perturbations taken from a given PEARP member to the deterministic initial conditions."""

    _footprint = dict(
        info = 'Tool that adds perturbations taken from a given PEARP member',
        attr = dict(
            kind = dict(
                values   = ['addpearp'],
            ),
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'master_addpearp'
            ),
        )
    )

    @property
    def realkind(self):
        return 'addpearp'
