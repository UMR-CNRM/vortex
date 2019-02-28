#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, division, unicode_literals

from vortex.data.executables import Script, BlackBox, NWPModel, SurfaceModel
from gco.syntax.stdattrs import gvar, arpifs_cycle

#: No automatic export
__all__ = []


class IFSModel(NWPModel):
    """Yet an other IFS Model."""

    _footprint = [
        arpifs_cycle,
        gvar,
        dict(
            info = 'IFS Model',
            attr = dict(
                gvar = dict(
                    default  = 'master_[model]'
                ),
                kind = dict(
                    values   = ['ifsmodel', 'mfmodel'],
                ),
                model = dict(
                    outcast  = ['aladin', 'arome'],
                ),
            )
        )
    ]

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


class Prep(BlackBox):
    """A tool to interpolate Surfex files."""

    _footprint = [
        gvar,
        dict(
            info = 'Prep utility to interpolate Surfex files',
            attr = dict(
                gvar = dict(
                    default  = 'master_prep'
                ),
                kind = dict(
                    values   = ['prep', ],
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'prep'


class PGD(BlackBox):
    """A tool to create Surfex clim files."""

    _footprint = [
        gvar,
        dict(
            info = 'PGD utility to create Surfex clim files',
            attr = dict(
                gvar = dict(
                    default  = 'master_pgd'
                ),
                kind = dict(
                    values   = ['buildpgd', ],
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'buildpgd'


class OfflineSurfex(SurfaceModel):
    """Surfex executable."""

    _footprint = [
        gvar,
        dict(
            info = 'Surfex executable',
            attr = dict(
                gvar = dict(
                    default  = 'master_offline'
                ),
                kind = dict(
                    values   = ['offline', ],
                ),
                model = dict(
                    values   = ['surfex', ],
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'offline'


class ProGrid(BlackBox):
    """A tool for grib conversion."""

    _footprint = [
        gvar,
        dict(
            info = 'ProGrid utility for grib conversion',
            attr = dict(
                gvar = dict(
                    default  = 'master_progrid'
                ),
                kind = dict(
                    values   = ['progrid', 'gribtool'],
                    remap    = dict(gribtool = 'progrid'),
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'progrid'


class ProTool(BlackBox):
    """A tool for adding fields on FA objects."""

    _footprint = [
        gvar,
        dict(
            info = 'ProTool utility for field manipulation',
            attr = dict(
                gvar = dict(
                    default  = 'master_addsurf'
                ),
                kind = dict(
                    values   = [ 'protool', 'addsurf' ],
                    remap    = dict(addsurf = 'protool'),
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'protool'


class SstNetcdf2Ascii(BlackBox):
    """Change format of NetCDF sst files."""

    _footprint = [
        gvar,
        dict(
            info = 'Tool to change the format of NetCDF sst files',
            attr = dict(
                gvar = dict(
                    default = "master_sst_netcdf"
                ),
                kind = dict(
                    values = ['sst_netcdf'],
                )
            )
        )
    ]


class SstGrb2Ascii(BlackBox):
    """Transform sst grib files from the BDAP into ascii files."""

    _footprint = [
        gvar,
        dict(
            info = 'Tool to change the format of grib sst files',
            attr = dict(
                gvar = dict(
                    default = "master_lectbdap"
                ),
                kind = dict(
                    values = ['lectbdap'],
                )
            )
        )
    ]

    def command_line(self, year, month, day, hour, lon, lat):
        """Build the command line to launch the executable."""
        return '-y{year} -m{month} -d{day} -r{hour} -o{lon} -a{lat}'.format(
            year=year, month=month, day=day, hour=hour, lon=lon, lat=lat
        )


class IceGrb2Ascii(BlackBox):
    """Transform sea ice grib files into ascii files using the SeaIceLonLat file for coordinates."""

    _footprint = [
        gvar,
        dict(
            info = 'Ice_grib executable to convert sea ice grib files into ascii files',
            attr = dict(
                gvar = dict(
                    default = 'master_ice_grb'
                ),
                kind = dict(
                    values = ['ice_grb']
                )
            )
        )
    ]


class IceNCDF2Ascii(BlackBox):
    """Transform sea ice NetCDF files into obsoul files."""

    _footprint = [
        gvar,
        dict(
            info = 'Ice_netcdf executable to convert sea ice NetCDF files into obsoul files',
            attr = dict(
                gvar = dict(
                    default = 'master_ice_netcdf'
                ),
                kind = dict(
                    values = ['ice_netcdf']
                )
            )
        )
    ]

    def command_line(self, file_in_hn, file_in_hs, param, file_out):
        """Build the command line to launch the executable."""
        return '{file_in_hn} {file_in_hs} {param} {file_out}'.format(
            file_in_hn = file_in_hn,
            file_in_hs = file_in_hs,
            param = param,
            file_out = file_out
        )


class IOAssign(BlackBox):
    """A tool for ODB pools mapping."""

    _footprint = [
        gvar,
        dict(
            info = 'ProTool utility for field manipulation',
            attr = dict(
                kind = dict(
                    values   = ['ioassign', 'odbioassign'],
                    remap    = dict(odbioassign = 'ioassign'),
                ),
                gvar = dict(
                    default  = 'master_ioassign'
                ),
                iotool = dict(
                    optional = True,
                    default  = 'create_ioassign',
                    access   = 'rwx',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'ioassign'


class Batodb(BlackBox):
    """A tool for conversion to ODB format."""

    _footprint = [
        arpifs_cycle,
        gvar,
        dict(
            info = 'Batodb conversion program',
            attr = dict(
                kind = dict(
                    values   = ['bator', 'batodb'],
                    remap    = dict(bator = 'batodb'),
                ),
                gvar = dict(
                    default  = 'master_batodb'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'batodb'


class Odbtools(BlackBox):
    """A tool for shuffle operations in ODB format."""

    _footprint = [
        gvar,
        dict(
            info = 'Odbtools shuffle program',
            attr = dict(
                kind = dict(
                    values   = ['odbtools'],
                ),
                gvar = dict(
                    default  = 'master_odbtools'
                ),
            )
        )
    ]

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


class FcqODB(BlackBox):
    """A tool to calculate flags on observations."""

    _footprint = [
        gvar,
        dict(
            info = 'Flags calculation program',
            attr = dict(
                kind = dict(
                    values = ['fcqodb'],
                ),
                gvar = dict(
                    default = 'master_fcqodb'
                )
            ),
        )
    ]


class VarBCTool(BlackBox):
    """Well... a single minded binary for a quite explicite purpose."""

    _footprint = [
        gvar,
        dict(
            info = 'VarBC merger program',
            attr = dict(
                kind = dict(
                    values   = ['varbctool'],
                ),
                gvar = dict(
                    default  = 'master_merge_varbc'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'varbctool'


class LopezMix(BlackBox):
    """Some mixture for surface fields during the 3DVar assimilation process."""

    _footprint = [
        gvar,
        dict(
            info = 'Surface mix',
            attr = dict(
                kind = dict(
                    values   = ['lopezmix', 'lopez', 'mastsurf', 'surfmix'],
                    remap    = dict(autoremap = 'first'),
                ),
                gvar = dict(
                    default  = 'master_surfmix'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'lopezmix'


class MasterDiag(BlackBox):
    """A binary to compute a diagnostic with some gribs."""

    _footprint = [
        gvar,
        dict(
            info = 'MasterDiag utility for diagnostics computation',
            attr = dict(
                gvar = dict(
                    default  = 'master_diag_[diagnostic]'
                ),
                kind = dict(
                    values   = ['masterdiag', 'masterdiagpi'],
                    remap    = dict(masterdiagpi='masterdiag'),
                ),
                diagnostic = dict(
                    info     = "The type of diagnostic to be performed.",
                    optional = True,
                    default  = 'aromepi',
                    values   = ['voisin', 'neighbour', 'aromepi'],
                    remap    = dict(neighbour='voisin'),
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'masterdiag'


class IOPoll(Script):
    """
    The IOPoll script. A Genvkey can be given.
    """
    _footprint = [
        gvar,
        dict(
            info='IOPoll script',
            attr=dict(
                kind=dict(
                    optional = False,
                    values=['iopoll', 'io_poll'],
                    remap=dict(autoremap='first'),
                ),
                gvar=dict(
                    default='tools_io_poll',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'iopoll'


class LFITools(BlackBox):
    """Multipurpose tool to handle LFI/FA files."""

    _footprint = [
        gvar,
        dict(
            info = 'Tool to handle LFI/FA files',
            attr = dict(
                kind = dict(
                    values   = ['lfitools', ],
                ),
                gvar = dict(
                    default  = 'master_lfitools'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'lfitools'


class SFXTools(BlackBox):
    """Multipurpose tool to handle Surfex files."""

    _footprint = [
        gvar,
        dict(
            info = 'Tool that handles Surfex files',
            attr = dict(
                kind = dict(
                    values   = ['sfxtools', ],
                ),
                gvar = dict(
                    default  = 'master_sfxtools'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'sfxtools'


class Combi(BlackBox):
    """Multipurpose tool to build the initial states of the ensemble prediction system."""

    _footprint = [
        gvar,
        dict(
            info = 'Tool to build EPS initial conditions',
            attr = dict(
                kind = dict(
                    values   = ['combi'],
                ),
                gvar = dict(
                    default  = 'master_combi'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'combi'


class Gobptout(BlackBox):
    """A tool for grib conversion on a gaussian grid."""

    _footprint = [
        gvar,
        dict(
            info = 'Gobptout utility for grib conversion',
            attr = dict(
                gvar = dict(
                    default  = 'master_gobtout'
                ),
                kind = dict(
                    values   = ['gobptout'],
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'gobptout'


class Clust(BlackBox):
    """Tool that selects a subset of EPS members using the Clustering method."""

    _footprint = [
        gvar,
        dict(
            info = 'Tool that selects a subset of EPS members using the Clustering method',
            attr = dict(
                kind = dict(
                    values   = ['clust'],
                ),
                gvar = dict(
                    default  = 'master_clust'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'clust'


class PertSurf(BlackBox):
    """Tool that adds perturbations to surface fields."""

    _footprint = [
        gvar,
        dict(
            info = 'Tool that adds perturbations to surface fields',
            attr = dict(
                kind = dict(
                    values   = ['pertsurf'],
                ),
                gvar = dict(
                    default  = 'master_pertsurf'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'pertsurf'


class AddPearp(BlackBox):
    """Tool that adds perturbations taken from a given PEARP member
    to the deterministic initial conditions."""

    _footprint = [
        gvar,
        dict(
            info = 'Tool that adds perturbations taken from a given PEARP member',
            attr = dict(
                kind = dict(
                    values   = ['addpearp'],
                ),
                gvar = dict(
                    default  = 'master_addpearp'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'addpearp'


class BDMExecutableBUFR(Script):
    """An executable to extract BDM BUFR files."""

    _footprint = [
        gvar,
        dict(
            info = 'Executable to extract BDM files using Oulan',
            attr = dict(
                source = dict(
                    values  = ['alim.awk', 'alim_olive.awk'],
                ),
                kind = dict(
                    optional = False,
                    values   = ['bdm_bufr_extract', ],
                ),
                gvar=dict(
                    values=['extract_stuff'],
                    default='extract_stuff',
                ),
                language = dict(
                    default = 'awk',
                    values = ['awk'],
                    optional = True,
                )
            )
        )
    ]

    @property
    def realkind(self):
        return 'bdm_bufr_extract'

    def gget_urlquery(self):
        """GGET specific query : ``extract``."""
        return 'extract=' + self.source

    def command_line(self, **opts):
        """Returns optional attribute :attr:`rawopts`."""
        args = []
        if 'query' in opts:
            args.append(opts['query'])  # The query name
        superraw = super(BDMExecutableBUFR, self).command_line(**opts)
        if superraw:
            args.append(superraw)  # Other arguments provided by the user
        return ' '.join(args)


class BDMExecutableOulan(BlackBox):
    """An executable to extract BDM files using Oulan."""

    _footprint = [
        gvar,
        dict(
            info = 'Executable to extract BDM BUFR files',
            attr = dict(
                kind = dict(
                    values   = ['bdm_oulan_extract', ],
                ),
                gvar=dict(
                    values=['master_oulan'],
                    default='master_oulan',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'bdm_obsoul_extract'


class ExecMonitoring(BlackBox):
    """Compute monitoring statistics."""

    _footprint = [
        gvar,
        dict(
            info = 'Executable to compute monitoring statistics',
            attr = dict(
                gvar = dict(
                    default = "master_monitoring"
                ),
                kind = dict(
                    values = ['exec_monitoring'],
                )
            )
        )
    ]


class ExecReverser(BlackBox):
    """Compute the initial state for Ctpini."""

    _footprint = [
        gvar,
        dict(
            info='Executable to compute initial state for Ctpini',
            attr=dict(
                gvar=dict(
                    default="master_involive_km"
                ),
                kind=dict(
                    values=['exec_reverser'],
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'exec_reverser'


class Rgrid(BlackBox):
    """An executable to make a gaussian reduced grid from several parameters."""

    _footprint = [
        gvar,
        dict(
            info = 'Executable to make a gaussian reduced grid',
            attr = dict(
                kind = dict(
                    values   = ['rgrid', ],
                ),
                gvar=dict(
                    values=['master_rgrid'],
                    default='master_rgrid',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'rgrid'

    def command_line(self, **opts):
        args = []
        for k, v in opts.items():
            args.extend(['-' + k, v])
        return ' '.join(args)


class Festat(BlackBox):
    """Executable to compute the B matrix and statistics upon it."""

    _footprint = [
        gvar,
        dict(
            info = 'Executable to compute the B matrix',
            attr = dict(
                kind = dict(
                    values = ["festat", ],
                ),
                gvar = dict(
                    optional = True,
                ),
            )
        )
    ]
