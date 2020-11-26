#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Abstract base class for any AlgoComponnent leveraging the Arpege/IFS code.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers
import footprints

from vortex.algo.components import Parallel, ParallelIoServerMixin, AlgoComponentError
from vortex.syntax.stdattrs import model
from vortex.tools import grib

from common.algo import ifsnaming  # @UnusedImport
from common.tools import satrad, drhook

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class IFSParallel(Parallel, ParallelIoServerMixin,
                  satrad.SatRadDecoMixin, drhook.DrHookDecoMixin, grib.EcGribDecoMixin):
    """Abstract IFSModel parallel algo components."""

    _abstract = True
    _footprint = [
        model,
        dict(
            info = 'Abstract AlgoComponent for anything based on Arpege/IFS.',
            attr = dict(
                kind = dict(
                    info            = 'The kind of processing we want the Arpege/IFS binary to perform.',
                    default         = 'ifsrun',
                    doc_zorder      = 90,
                ),
                model = dict(
                    values  = ['arpege', 'arp', 'arp_court', 'aladin', 'ald',
                               'arome', 'aro', 'aearp', 'pearp', 'ifs']
                ),
                ioname = dict(
                    default = 'nwpioserv',
                ),
                binarysingle = dict(
                    default = 'basicnwp',
                ),
                conf = dict(
                    info = 'The configuration number given to Arpege/IFS.',
                    type            = int,
                    optional        = True,
                    default         = 1,
                    doc_visibility  = footprints.doc.visibility.ADVANCED,
                ),
                timescheme = dict(
                    info = 'The timescheme that will be used by Arpege/IFS model.',
                    optional        = True,
                    default         = 'sli',
                    values          = ['eul', 'eulerian', 'sli', 'semilag'],
                    remap           = dict(
                        eulerian = 'eul',
                        semilag  = 'sli'
                    ),
                    doc_visibility  = footprints.doc.visibility.ADVANCED,
                ),
                timestep = dict(
                    info     = 'The timestep of the Arpege/IFS model.',
                    type     = float,
                    optional = True,
                    default  = 600.,
                ),
                fcterm = dict(
                    info     = 'The forecast term of the Arpege/IFS model.',
                    type = int,
                    optional = True,
                    default = 0,
                ),
                fcunit = dict(
                    info     = 'The unit used in the *fcterm* attribute.',
                    optional = True,
                    default  = 'h',
                    values   = ['h', 'hour', 't', 'step'],
                    remap = dict(
                        hour = 'h',
                        step = 't'
                    )
                ),
                xpname = dict(
                    info = 'The default labelling of files used in Arpege/IFS model.',
                    optional        = True,
                    default         = 'XPVT',
                    doc_visibility  = footprints.doc.visibility.ADVANCED,
                ),
                member = dict(
                    info            = ("The current member's number " +
                                       "(may be omitted in deterministic configurations)."),
                    optional        = True,
                    type            = int,
                ),
                mpiconflabel = dict(
                    default  = 'mplbased'
                )
            )
        )
    ]

    def fstag(self):
        """Extend default tag with ``kind`` value."""
        return super(IFSParallel, self).fstag() + '.' + self.kind

    def valid_executable(self, rh):
        """Be sure that the specifed executable is ifsmodel compatible."""
        valid = super(IFSParallel, self).valid_executable(rh)
        try:
            return valid and bool(rh.resource.realkind == 'ifsmodel')
        except (ValueError, TypeError):
            return False

    def spawn_hook(self):
        """Usually a good habit to dump the fort.4 namelist."""
        super(IFSParallel, self).spawn_hook()
        if self.system.path.exists('fort.4'):
            self.system.subtitle('{0:s} : dump namelist <fort.4>'.format(self.realkind))
            self.system.cat('fort.4', output=False)

    def spawn_command_options(self):
        """Dictionary provided for command line factory."""
        return dict(
            name=(self.xpname + 'xxxx')[:4].upper(),
            conf=self.conf,
            timescheme=self.timescheme,
            timestep=self.timestep,
            fcterm=self.fcterm,
            fcunit=self.fcunit,
        )

    def naming_convention(self, kind, rh, actualfmt=None, **kwargs):
        """Create an appropriate :class:`IFSNamingConvention`.

        :param str kind: The :class:`IFSNamingConvention` object kind.
        :param rh: The binary's ResourceHandler.
        :param actualfmt: The format of the target file.
        :param dict kwargs: Any argument you may see fit.
        """
        nc_args = dict(model=self.model,
                       conf=self.conf,
                       xpname=self.xpname)
        nc_args.update(kwargs)
        nc = footprints.proxy.ifsnamingconv(kind=kind,
                                            actualfmt=actualfmt,
                                            cycle=rh.resource.cycle,
                                            **nc_args)
        if nc is None:
            raise AlgoComponentError("No IFSNamingConvention was found.")
        return nc

    def do_climfile_fixer(self, rh, convkind, actualfmt=None, geo=None, **kwargs):
        """Is it necessary to fix the climatology file ? (i.e link in the appropriate file).

        :param rh: The binary's ResourceHandler.
        :param str convkind: The :class:`IFSNamingConvention` object kind.
        :param actualfmt: The format of the climatology file.
        :param geo: The geometry of the desired geometry file.
        :param dict kwargs: Any argument you may see fit (used to create and call
                            the IFSNamingConvention object.
        """
        nc = self.naming_convention(kind=convkind, rh=rh, actualfmt=actualfmt, **kwargs)
        nc_args = dict()
        if geo:
            nc_args['area'] = geo.area
        nc_args.update(kwargs)
        return not self.system.path.exists(nc(** nc_args))

    def climfile_fixer(self, rh, convkind,
                       month, geo=None, notgeo=None, actualfmt=None,
                       inputrole=None, inputkind=None, **kwargs):
        """Fix the climatology files (by choosing the appropriate month, geometry, ...)

        :param rh: The binary's ResourceHandler.
        :param str convkind: The :class:`IFSNamingConvention` object kind.
        :param ~bronx.stdtypes.date.Month month: The climatlogy file month
        :param geo: The climatlogy file geometry
        :param notgeo: Exclude these geometries during the climatology file lookup
        :param actualfmt: The format of the climatology file.
        :param inputrole: The section's role in which Climatology files are looked for.
        :param inputkind: The section's realkind in which Climatology files are looked for/
        :param dict kwargs: Any argument you may see fit (used to create and call
                            the IFSNamingConvention object).
        """
        if geo is not None and notgeo is not None:
            raise ValueError('*geo* and *notgeo* cannot be provided together.')

        def check_month(actualrh):
            return bool(hasattr(actualrh.resource, 'month') and
                        actualrh.resource.month == month)

        def check_month_and_geo(actualrh):
            return (check_month(actualrh) and
                    actualrh.resource.geometry.tag == geo.tag)

        def check_month_and_notgeo(actualrh):
            return (check_month(actualrh) and
                    actualrh.resource.geometry.tag != notgeo.tag)

        if geo:
            checker = check_month_and_geo
        elif notgeo:
            checker = check_month_and_notgeo
        else:
            checker = check_month

        nc = self.naming_convention(kind=convkind, rh=rh, actualfmt=actualfmt, **kwargs)
        nc_args = dict()
        if geo:
            nc_args['area'] = geo.area
        nc_args.update(kwargs)
        target_name = nc(** nc_args)

        self.system.remove(target_name)

        logger.info("Linking in the %s file (%s) for month %s.", convkind, target_name, month)
        rc = self.setlink(initrole=inputrole, initkind=inputkind, inittest=checker,
                          initname=target_name)
        return target_name if rc else None

    def all_localclim_fixer(self, rh, month, convkind='targetclim', actualfmt=None,
                            inputrole=('LocalClim', 'TargetClim', 'BDAPClim'),
                            inputkind='clim_bdap', **kwargs):
        """Fix all the local/BDAP climatology files (by choosing the appropriate month)

        :param rh: The binary's ResourceHandler.
        :param ~bronx.stdtypes.date.Month month: The climatology file month
        :param str convkind: The :class:`IFSNamingConvention` object kind.
        :param actualfmt: The format of the climatology file.
        :param inputrole: The section's role in which Climatology files are looked for.
        :param inputkind: The section's realkind in which Climatology files are looked for/
        :param dict kwargs: Any argument you may see fit (used to create and call
                            the IFSNamingConvention object.
        :return: The list of linked files
        """

        def check_month(actualrh):
            return bool(hasattr(actualrh.resource, 'month') and
                        actualrh.resource.month == month)

        nc = self.naming_convention(kind=convkind, rh=rh, actualfmt=actualfmt, **kwargs)
        dealtwith = list()

        for tclimrh in [x.rh for x in self.context.sequence.effective_inputs(
                role=inputrole, kind=inputkind,
        ) if x.rh.resource.month == month]:
            thisclim = tclimrh.container.localpath()
            thisname = nc(area=tclimrh.resource.geometry.area)
            if thisclim != thisname:
                logger.info("Linking in the %s to %s for month %s.", thisclim, thisname, month)
                self.system.symlink(thisclim, thisname)
                dealtwith.append(thisname)

        return dealtwith

    def find_namelists(self, opts=None):
        """Find any namelists candidates in actual context inputs."""
        namcandidates = [x.rh
                         for x in self.context.sequence.effective_inputs(kind=('namelist', 'namelistfp'))]
        self.system.subtitle('Namelist candidates')
        for nam in namcandidates:
            nam.quickview()
        return namcandidates

    def prepare_namelist_delta(self, rh, namcontents, namlocal):
        """Apply a namelist delta depending on the cycle of the binary."""
        # TODO: The mapping between the dict that contains the settings
        # (i.e elf.spawn_command_options()) and actual namelist keys should
        # be done by an extra class ... and it could be generalized to mpi
        # setup by the way !
        nam_updated = False
        # For cy41 onward, replace some namelist macros with the command line
        # arguments
        if rh.resource.cycle >= 'cy41':
            if 'NAMARG' in namcontents:
                opts_arg = self.spawn_command_options()
                logger.info('Setup macro CEXP=%s in %s', opts_arg['name'], namlocal)
                namcontents.setmacro('CEXP', opts_arg['name'])
                logger.info('Setup macro TIMESTEP=%g in %s', opts_arg['timestep'], namlocal)
                namcontents.setmacro('TIMESTEP', opts_arg['timestep'])
                fcstop = '{:s}{:d}'.format(opts_arg['fcunit'], opts_arg['fcterm'])
                logger.info('Setup macro FCSTOP=%s in %s', fcstop, namlocal)
                namcontents.setmacro('FCSTOP', fcstop)
                nam_updated = True
            else:
                logger.info('No NAMARG block in %s', namlocal)

        if self.member is not None:
            namcontents.setmacro('MEMBER', self.member)
            namcontents.setmacro('PERTURB', self.member)
            nam_updated = True
            logger.info('Setup macro MEMBER=%s in %s', self.member, namlocal)
            logger.info('Setup macro PERTURB=%s in %s', self.member, namlocal)

        return nam_updated

    def prepare_namelists(self, rh, opts=None):
        """Update each of the namelists."""
        for namrh in self.find_namelists(opts):
            namc = namrh.contents
            if self.prepare_namelist_delta(rh, namc, namrh.container.actualpath()):
                namc.rewrite(namrh.container)

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(IFSParallel, self).prepare(rh, opts)
        # Namelist fixes
        self.prepare_namelists(rh, opts)

    def execute_single(self, rh, opts):
        """Standard IFS-Like execution parallel execution."""
        self.system.ls(output='dirlst')
        super(IFSParallel, self).execute_single(rh, opts)
