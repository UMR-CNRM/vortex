#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TODO: Module documentation
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import six

#: No automatic export
__all__ = []

import io
import time
import footprints
import copy

from bronx.datagrip import namelist as bnamelist
from bronx.fancies import loggers
from bronx.stdtypes.date import Date, Time, Period
from footprints.stdtypes import FPList

from vortex.algo.components import Parallel, ParaBlindRun, BlindRun
from vortex.tools import grib

from vortex.tools.parallelism import VortexWorkerBlindRun
from vortex.layout.monitor import BasicInputMonitor

logger = loggers.getLogger(__name__)


class Ww3(Parallel, grib.EcGribDecoMixin):
    """Algocomponent for WW3."""
    _footprint = dict(
        info='Algo for WW3',
        attr = dict(
            kind = dict(
                values = ['ww3'],
            ),
            datpivot = dict(
                type = Date,
                optional = False,
            ),
            stepout = dict(
                type = Period,
                optional = False,
            ),
            flyargs = dict(
                default = ('stdeo.0',),
            ),
            flypoll = dict(
                default = 'iopoll_ww3',
            ),
            anaterm = dict(
                type = int,
                optional = False,
            ),
             fcterm = dict(
                type = int,
                optional = False,
            ),
             restermini = dict(
                type = int,
                optional = True,
                default  = 0,
            ),
             restermfin = dict(
                type = int,
                optional = True,
                default  = 12,
            ),
        )
    )

    def spawn_hook(self):
        """"""
        super(Ww3, self).spawn_hook()

    def prepare(self, rh, opts):
        super(Ww3, self).prepare(rh, opts)
        self.io_poll_sleep = 30
        sstepout='{0:d}'.format(int(self.stepout.length/3600))
        self.io_poll_kwargs = dict(datpivot=self.datpivot.ymdh,stepout=sstepout)
        self.flyput = True

    def execute(self, rh, opts):
        """Set the namelist."""
        # Tweak Namelist parameters
        namcandidate = self.context.sequence.effective_inputs(role=('NamelistShel'),)

        if len(namcandidate) != 1:
            raise IOError("No or too much namelists for WW3_shel")

        namcontents = namcandidate[0].rh.contents
        rundate = self.datpivot
        start_date = rundate - self.anaterm*3600
        end_date = rundate + self.fcterm*3600
        restart_start_date = rundate + self.restermini*3600
        restart_end_date = rundate + self.restermfin*3600

        dictkeyvalue=footprints.stdtypes.FPDict()

        dictkeyvalue["yyyymmdd_start"] = start_date.ymd
        dictkeyvalue["hhmmss_start"]   = start_date.hm+'00'
        dictkeyvalue["yyyymmdd_end"]   = end_date.ymd
        dictkeyvalue["hhmmss_end"]     = end_date.hm+'00'

        dictkeyvalue["restart_yyyymmdd_start"] = restart_start_date.ymd
        dictkeyvalue["restart_hhmmss_start"]   = restart_start_date.hm+'00'
        dictkeyvalue["restart_yyyymmdd_end"]   = restart_end_date.ymd
        dictkeyvalue["restart_hhmmss_end"]     = restart_end_date.hm+'00'

        namcontents.setitems(dictkeyvalue)
        namcandidate[0].rh.save()
        super(Ww3, self).execute(rh, opts)


    def postfix(self, rh, opts):
        """Manually call the iopoll method to deal with the latest files."""
        if self.flyput:
            self.manual_flypolling_job()
        super(Ww3, self).postfix(rh, opts)



class ConvertSpecWW3AsciiAlgo(BlindRun):
    """Algocomponent for conversion of mfwam spectra to WW3 Ascii."""
    _footprint = dict(
        info='Algo for mfwam spectra to ww3',
        attr = dict(
            kind = dict(
                values = ['specww3asciialgo'],
            ),
        )
    )
    def prepare(self, rh, opts):
        """Create list_files file."""
        super(ConvertSpecWW3AsciiAlgo, self).prepare(rh, opts)

        sh = self.system.sh
        inputspec = [x.rh for x in self.context.sequence.effective_inputs(role=('BoundarySpectra'))]
        with io.open('list_files','w') as flist:
            for fname in [x.container.filename for x in inputspec]:
                flist.write(fname)
                flist.write('\n')

#       Creation of results directory
        sh.mkdir('spectre')

class Ww3_ounpAlgo(BlindRun):
    """Algocomponent for extraction of WW3 output point."""
    _footprint = dict(
        info='Algo for extraction of wW3 output point',
        attr = dict(
            kind = dict(
                values = ['ww3_ounp_algo'],
            ),
            anaterm = dict(
                type = int,
                optional = False,
            ),
        )
    )

    def execute(self, rh, opts):
        """Set the namelist."""
        # Tweak Namelist parameters
        namcandidate = self.context.sequence.effective_inputs(role=('NamelistWw3Ounp'),)

        if len(namcandidate) != 1:
            raise IOError("No or too much namelists for WW3_ounp")

        namcontents = namcandidate[0].rh.contents
        rundate = namcandidate[0].rh.resource.date
        start_date = rundate - self.anaterm*3600
        logger.info("substituted values %s  %s",start_date.ymd,start_date.hm+'00')
        dictkeyvalue=footprints.stdtypes.FPDict()
        dictkeyvalue["yyyymmdd"] = start_date.ymd
        dictkeyvalue["hhmmss"] = start_date.hm+'00'
        namcontents.setitems(dictkeyvalue)
        namcandidate[0].rh.save()
        super(Ww3_ounpAlgo, self).execute(rh, opts)

class Ww3_ounpAlgo_para(ParaBlindRun):
    """Algocomponent for extraction of WW3 output point."""
    _footprint = dict(
        info='Algo for extraction of wW3 output point',
        attr = dict(
            kind = dict(
                values = ['ww3_ounp_algo'],
            ),
            refreshtime = dict(
                type = int,
                optional = True,
                default = 20,
            ),
            timeout = dict(
                type = int,
                optional = True,
                default = 600,
            ),
        )
    )
    def execute(self, rh, opts):
        """The algo component launchs a worker per output file."""
        self._default_pre_execute(rh, opts)

        common_i = self._default_common_instructions(rh, opts)
#        common_i.update(dict(header=self.header, param=self.param))
        tmout = False


        # Monitor for the input files
        bm = BasicInputMonitor(self.context, caching_freq=self.refreshtime,
                               role='InputWw3IntermedResult', kind='ww3DatedIntermedResult')

        with bm:
            while not bm.all_done or len(bm.available) > 0:
                while bm.available:
                    gpsec = bm.pop_available().section
                    file_in = gpsec.rh.container.localpath()
                    dateval = gpsec.rh.resource.dateval.ymdh
                    self._add_instructions(common_i,
                                           dict(file_in=[file_in, ],
                                                dateval=[dateval,]))

                if not (bm.all_done or len(bm.available) > 0):
                    # Timeout ?
                    tmout = bm.is_timedout(self.timeout)
                if tmout:
                    break
                # Wait a little bit :-)
                time.sleep(1)
                bm.health_check(interval=30)

        self._default_post_execute(rh, opts)

        for failed_file in [e.section.rh.container.localpath() for e in six.itervalues(bm.failed)]:
            logger.error("We were unable to fetch the following file: %s", failed_file)
            if self.fatal:
                self.delayed_exception_add(IOError("Unable to fetch {:s}".format(failed_file)),
                                           traceback=False)

        if tmout:
            raise IOError("The waiting loop timed out")


class _Ww3_ounpAlgo_paraWorker(VortexWorkerBlindRun):
    """Worker for extraction of WW3 output point."""
    _footprint = dict(
        info='Worker for extraction of wW3 output point',
        attr = dict(
            kind = dict(
                values = ['ww3_ounp_algo'],
            ),
            file_in = dict(),
            dateval = dict(
                optional = False,
            ),
        )
    )

    def vortex_task(self, **kwargs):  # @UnusedVariable
        """Post-processing of a single output pnt file."""
        logger.info("Starting the post-processing")

        sh = self.system.sh
        logger.info("Post-processing of %s", self.file_in)

        # Prepare the working directory
        cwd = sh.pwd()
        output_files = set()
        with sh.cdcontext(sh.path.join(cwd, self.file_in + '.process.d'), create=True):

            sh.softlink(sh.path.join(cwd, self.file_in),'out_pnt.ww3')
            # copy of namelist and constant files
            sh.softlink(sh.path.join(cwd,'mapsta.ww3'),'mapsta.ww3')
            sh.softlink(sh.path.join(cwd,'mask.ww3'),'mask.ww3')
            sh.softlink(sh.path.join(cwd,'mod_def.ww3'),'mod_def.ww3')
            sh.softlink(sh.path.join(cwd,'ww3_ounp.inp'),'ww3_ounp.inp')
            # execution
            self.local_spawn("output.log")
            tarname='ww3_pnt_{0:s}.tar'.format(self.dateval)
            sh.tar(tarname,'ww3.?????_????????????_tab.nc')
            sh.mv(tarname,cwd)
            output_files.add(tarname)

        # Deal with promised resources
        expected = [x for x in self.context.sequence.outputs()
                    if (x.rh.provider.expected and
                        x.rh.container.localpath() in output_files)]
        for thispromise in expected:
            thispromise.put(incache=True)


class Ww3_ounfAlgo(ParaBlindRun):
    """Algocomponent for extraction of WW3 output ounf field."""
    _footprint = dict(
        info='Algo for extraction of wW3 output ounf field',
        attr = dict(
            kind = dict(
                values = ['ww3_ounf_algo'],
            ),
            anaterm = dict(
                type = int,
                optional = False,
            ),
            refreshtime = dict(
                type = int,
                optional = True,
                default = 20,
            ),
            timeout = dict(
                type = int,
                optional = True,
                default = 600,
            ),
        )
    )
    def execute(self, rh, opts):
        """The algo component launchs a worker per output file."""
        self._default_pre_execute(rh, opts)

        common_i = self._default_common_instructions(rh, opts)
        tmout = False


        # Monitor for the input files
        bm = BasicInputMonitor(self.context, caching_freq=self.refreshtime,
                               role='InputWw3IntermedResult', kind='ww3DatedIntermedResult')


        with bm:
            while not bm.all_done or len(bm.available) > 0:
                while bm.available:
                    gpsec = bm.pop_available().section
                    file_in = gpsec.rh.container.localpath()
                    dateval = gpsec.rh.resource.dateval.ymdh
                    self._add_instructions(common_i,
                                           dict(file_in=[file_in,],
                                                dateval=[dateval,]))

                if not (bm.all_done or len(bm.available) > 0):
                    # Timeout ?
                    tmout = bm.is_timedout(self.timeout)
                if tmout:
                    break
                # Wait a little bit :-)
                time.sleep(1)
                bm.health_check(interval=30)

        self._default_post_execute(rh, opts)

        for failed_file in [e.section.rh.container.localpath() for e in six.itervalues(bm.failed)]:
            logger.error("We were unable to fetch the following file: %s", failed_file)
            if self.fatal:
                self.delayed_exception_add(IOError("Unable to fetch {:s}".format(failed_file)),
                                           traceback=False)

        if tmout:
            raise IOError("The waiting loop timed out")


class _Ww3_ounfAlgoWorker(VortexWorkerBlindRun):
    """Worker for extraction of WW3 output field."""
    _footprint = dict(
        info='Worker for extraction of WW3 output field',
        attr = dict(
            kind = dict(
                values = ['ww3_ounf_algo'],
            ),
            file_in = dict(),
            dateval = dict(
                optional = False,
                type     = Date,
            ),
        )
    )

    def vortex_task(self, **kwargs):  # @UnusedVariable
        """Netcdf extraction of a single time step output field file."""
        logger.info("Starting the netcdf extraction")

        sh = self.system.sh
        logger.info("Extraction of netcdf of %s", self.file_in)
        namcandidate = self.context.sequence.effective_inputs(role=('NamelistWw3Ounf'),)
        if len(namcandidate) != 1:
            raise IOError("No or too much namelists for WW3_ounf")
        nam_file=namcandidate[0].rh.container.localpath()
        namcontents = namcandidate[0].rh.contents
        

        # Prepare the working directory
        cwd = sh.pwd()
        output_files = set()
        with sh.cdcontext(sh.path.join(cwd, self.file_in + '.process.d'), create=True):

            sh.softlink(sh.path.join(cwd, self.file_in),'out_grd.ww3')
            # copy of namelist and constant files
            sh.softlink(sh.path.join(cwd,'mapsta.ww3'),'mapsta.ww3')
            sh.softlink(sh.path.join(cwd,'mask.ww3'),'mask.ww3')
            sh.softlink(sh.path.join(cwd,'mod_def.ww3'),'mod_def.ww3')
            dictkeyvalue=footprints.stdtypes.FPDict()
            dictkeyvalue["yyyymmdd"] = self.dateval.ymd
            dictkeyvalue["hhmmss"] = self.dateval.hm+'00'
            namcontents.setitems(dictkeyvalue)
            new_nam= footprints.proxy.container(filename=nam_file,format='ascii')
            namcontents.rewrite(new_nam)
            new_nam.close()
           # execution
            self.local_spawn("output.log")
            tarname='ww3_grd_nc_{0:s}.tar'.format(self.dateval.ymdh)
            sh.tar(tarname,'ww3.*.nc')
            sh.mv(tarname,cwd)
            output_files.add(tarname)

        # Deal with promised resources
        expected = [x for x in self.context.sequence.outputs()
                    if (x.rh.provider.expected and
                        x.rh.container.localpath() in output_files)]
        for thispromise in expected:
            thispromise.put(incache=True)




class InterpolateUGncAlgo(ParaBlindRun):
    """Algocomponent for interpolation to regular grid"""
    _footprint = dict(
        info='Algo for interpolation',
        attr = dict(
            kind = dict(
                values = ['interpalgo'],
            ),
            grid = dict(
                type     = footprints.FPList,
                optional = False,
                ),
            refreshtime = dict(
                type = int,
                optional = True,
                default = 20,
            ),
            timeout = dict(
                type = int,
                optional = True,
                default = 600,
            ),
      )
    )


    def execute(self, rh, opts):
        """The algo component launchs a worker per output file."""
        self._default_pre_execute(rh, opts)

        common_i = self._default_common_instructions(rh, opts)
        tmout = False


        # Monitor for the input files
        bm = BasicInputMonitor(self.context, caching_freq=self.refreshtime,
                               role='Input', kind='ww3outsurf')

        with bm:
            while not bm.all_done or len(bm.available) > 0:
                while bm.available:
                    gpsec = bm.pop_available().section
                    file_in = gpsec.rh.container.localpath()
                    dateval = gpsec.rh.resource.dateval.ymdh
                    self._add_instructions(common_i,
                                           dict(file_in=[file_in,],
                                                grid=[self.grid,],
                                                dateval=[dateval,]))

                if not (bm.all_done or len(bm.available) > 0):
                    # Timeout ?
                    tmout = bm.is_timedout(self.timeout)
                if tmout:
                    break
                # Wait a little bit :-)
                time.sleep(1)
                bm.health_check(interval=30)

        self._default_post_execute(rh, opts)

        for failed_file in [e.section.rh.container.localpath() for e in six.itervalues(bm.failed)]:
            logger.error("We were unable to fetch the following file: %s", failed_file)
            if self.fatal:
                self.delayed_exception_add(IOError("Unable to fetch {:s}".format(failed_file)),
                                           traceback=False)

        if tmout:
            raise IOError("The waiting loop timed out")


class _InterpolateUGncAlgoWorker(VortexWorkerBlindRun):
    """ Worker for interpolation to regular grid."""
    _footprint = dict(
        info='Worker for interpolation to regular grid',
        attr = dict(
            kind = dict(
                values = ['interpalgo'],
            ),
            file_in = dict(),
            grid = dict(
                type     = footprints.FPList,
                optional = False,
                ),
            dateval = dict(
                optional = False,
                type     = Date,
            ),
        )
    )

    def vortex_task(self, **kwargs):  # @UnusedVariable
        """Interpolation of a single time step."""
        logger.info("Starting the interpolation")

        sh = self.system.sh
        logger.info("Interpolation of %s", self.file_in)
        # Prepare the working directory
        cwd = sh.pwd()
        output_files = set()
        with sh.cdcontext(sh.path.join(cwd, self.file_in + '.process.d'), create=True):
            cwdp = sh.pwd()
            sh.softlink(sh.path.join(cwd, self.file_in),'out_grd_nc.tar')
            sh.untar('out_grd_nc.tar')
            with io.open('interpolateUG_nc.list','w') as flist:
                for fname in sh.ls('ww3.*nc'):
                    flist.write(fname)
                    flist.write('\n')
            for i in self.grid:
                with sh.cdcontext(cwdp, create=False):
                    file_grd_in = "interpolateUG_{0:s}.grd".format(i)
                    file_grd_out = "interpolateUG.grd"
                    sh.cp(sh.path.join(cwd,file_grd_in), sh.path.join(cwdp, file_grd_out), fmt='grd')
                    file_inp_in = "interpolateUG_nc_{0:s}.inp".format(i)
                    file_inp_out = "interpolateUG_nc.inp"
                    sh.cp(sh.path.join(cwd,file_inp_in), sh.path.join(cwdp, file_inp_out), fmt='inp')
                    self.local_spawn("output.log")
                    sh.rm(file_grd_out)
                    sh.rm(file_inp_out)

            # Prepare the archive of interpolated outputs
            with io.open('interpolateUG_nc.list','r') as flist:
                for line in flist:
                    line=line.rstrip()
                    sh.rm('{0:s}'.format(line))
            tarname='ww3_reg_nc_{0:s}.tar'.format(self.dateval.ymdh)
            sh.tar(tarname,'ww3.*.nc')
            sh.mv(tarname,cwd)
            output_files.add(tarname)

        # Deal with promised resources
        expected = [x for x in self.context.sequence.outputs()
                    if (x.rh.provider.expected and
                        x.rh.container.localpath() in output_files)]
        for thispromise in expected:
            thispromise.put(incache=True)

class ConvNetcdfGribAlgoold(BlindRun):
    """Algocomponent for interpolation to regular grid"""
    _footprint = dict(
        info='Algo for interpolation',
        attr = dict(
            kind = dict(
                values = ['convncgrbalgoold'],
            ),
            anaterm = dict(
                type = int,
                optional = False,
            ),
             fcterm = dict(
                type = int,
                optional = False,
            ),
   )
)

    def execute(self, rh, opts):
        for namsec in self.context.sequence.effective_inputs(role=('RegularGridNc')):

            r = namsec.rh

            p = r.resource.param
            h = r.resource.header
            nom_param = p
            filename = "ww3.{0:s}_{1:s}.nc".format(h,p)
            file_cst = "fic_constantes_{0:s}".format(p)
            fic_prod = "ww3.{0:s}_{1:s}.grb".format(h,p)

            rundate = r.resource.date
            start_date = rundate - self.anaterm*3600
            forecast_date = rundate + self.fcterm*3600

            logger.info("%s %s %s %s %s %s",p,filename,file_cst,fic_prod,start_date.ymdhm,forecast_date.ymdhm)

            # Tweak Namelist parameters
            namcandidate = self.context.sequence.effective_inputs(role=('NamelistNcGrb'),)
            if len(namcandidate) != 1:
               raise IOError("No or too much namelists for WW3_ncgrb")
            namcontents = namcandidate[0].rh.contents
            namcontents.setmacro('NOM_PARAM', nom_param)
            namcontents.setmacro('FILENAME', filename)
            namcontents.setmacro('FILE_CST', file_cst)
            namcontents.setmacro('FIC_PROD', fic_prod)
            namcontents.setmacro('START_DATE', start_date.ymdhm)
            namcontents.setmacro('FORECAST_DATE', forecast_date.ymdhm)
            namcandidate[0].rh.save()
            super(ConvNetcdfGribAlgo, self).execute(rh, opts)


class ConvNetcdfGribAlgo(ParaBlindRun):
    """Algocomponent for conversion from netcdf to grib"""
    _footprint = dict(
        info='Algo for grib conversion',
        attr = dict(
            kind = dict(
                values = ['convncgrbalgo'],
            ),
            datpivot = dict(
                type = Date,
                optional = False,
            ),
            refreshtime = dict(
                type = int,
                optional = True,
                default = 20,
            ),
            timeout = dict(
                type = int,
                optional = True,
                default = 600,
            ),
        )
    )

    def execute(self, rh, opts):
        """The algo component launchs a worker per output file."""
        self._default_pre_execute(rh, opts)

        common_i = self._default_common_instructions(rh, opts)
        tmout = False


        # Monitor for the input files
        bm = BasicInputMonitor(self.context, caching_freq=self.refreshtime,
                               role='RegularGridNc', kind='ww3outsurf')

        with bm:
            while not bm.all_done or len(bm.available) > 0:
                while bm.available:
                    gpsec = bm.pop_available().section
                    file_in = gpsec.rh.container.localpath()
                    dateval = gpsec.rh.resource.dateval.ymdh
                    self._add_instructions(common_i,
                                           dict(file_in=[file_in,],
                                                datpivot=[self.datpivot,],
                                                dateval=[dateval,]))
                if not (bm.all_done or len(bm.available) > 0):
                    # Timeout ?
                    tmout = bm.is_timedout(self.timeout)
                if tmout:
                    break
                # Wait a little bit :-)
                time.sleep(1)
                bm.health_check(interval=30)

        self._default_post_execute(rh, opts)

        for failed_file in [e.section.rh.container.localpath() for e in six.itervalues(bm.failed)]:
            logger.error("We were unable to fetch the following file: %s", failed_file)
            if self.fatal:
                self.delayed_exception_add(IOError("Unable to fetch {:s}".format(failed_file)),
                                           traceback=False)

        if tmout:
            raise IOError("The waiting loop timed out")

class _ConvNetcdfGribAlgoWorker (VortexWorkerBlindRun):
    """Worker for conversion from netcdf to grib"""
    _footprint = dict(
        info='Worker for grib conversion',
        attr = dict(
            kind = dict(
                values = ['convncgrbalgo'],
            ),
            file_in = dict(),
            datpivot = dict(
                type = Date,
                optional = False,
            ),
            dateval = dict(
                optional = False,
                type     = Date,
            ),
        )
    )

    def vortex_task(self, **kwargs):  # @UnusedVariable
        """Grib conversion for a single time step."""
        logger.info("Starting the netcdf to grib conversion")
        sh = self.system.sh
        logger.info("Conversion of %s", self.file_in)
        namcandidate = self.context.sequence.effective_inputs(role=('NamelistNcGrb'),)
        if len(namcandidate) != 1:
           raise IOError("No or too much namelists for WW3_ncgrb")
        namcontents = namcandidate[0].rh.contents
        nam_file=namcandidate[0].rh.container.localpath()

        cwd = sh.pwd()
        output_files = set()
        with sh.cdcontext(sh.path.join(cwd, self.file_in + '.process.d'), create=True):
            # copy of nc and constant files
            sh.softlink(sh.path.join(cwd, self.file_in),'out_reg_nc.tar')
            sh.untar('out_reg_nc.tar')
            sh.cp(sh.path.join(cwd,'fic_constantes_nc_grb.tgz'),'fic_constantes_nc_grb.tgz')
            sh.untar('fic_constantes_nc_grb.tgz')
            for fname in sh.ls('ww3.*nc'):
               #Retrieval of param and filename without nc
                head_filename=fname.split('_')[0]
                param=fname.split('_')[1]
                param=param.split('.')[0]
                file_cst = "fic_constantes_{0:s}".format(param)
                term=Time(self.dateval-self.datpivot)
               #Split the case of analysis and forecast
                if( term <= Period(0)):
                    fic_prod = "{0:s}_{1:s}_{2:s}.grb".format(head_filename,param,self.dateval.ymdh)
                else:
                    fic_prod = "{0:s}_{1:s}_{2:s}{3:s}.grb".format(head_filename,param,self.datpivot.ymdh,term.fmth)
               # set of namelist
                namcontents.setmacro("NOM_PARAM", param)
                namcontents.setmacro('FILENAME', fname)
                namcontents.setmacro('FILE_CST', file_cst)
                namcontents.setmacro('FIC_PROD', fic_prod)
                namcontents.setmacro('START_DATE', self.dateval.ymdh)
                namcontents.setmacro('FORECAST_DATE', self.datpivot.ymdhm)
                new_nam= footprints.proxy.container(filename=nam_file,format='ascii')
                namcontents.rewrite(new_nam)
                new_nam.close()
                self.local_spawn("output_{0:s}.log".format(fname))
                for fgrib in sh.ls('ww3.*grb'):
                    sh.mv(fgrib,cwd)
                    output_files.add(fgrib)

        # Deal with promised resources
        expected = [x for x in self.context.sequence.outputs()
                    if (x.rh.provider.expected and
                        x.rh.container.localpath() in output_files)]
        for thispromise in expected:
            thispromise.put(incache=True)
