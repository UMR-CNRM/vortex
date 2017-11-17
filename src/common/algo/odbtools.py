#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division

#: No automatic export
__all__ = []

from collections import defaultdict
import io
import re


import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.tools.systems   import ExecutionError
from vortex.tools           import odb
from vortex.algo.components import Parallel
from vortex.util.structs    import Foo
from vortex.syntax.stdattrs import a_date

from common.data.obs import ObsMapContent, ObsMapItem, ObsRefContent, ObsRefItem

from vortex.tools.parallelism import VortexWorkerBlindRun
from vortex.algo.components import TaylorRun
from taylorism.schedulers import LongerFirstScheduler
from taylorism import run_as_server



class Bateur(VortexWorkerBlindRun):
    """
    worker for parallel BATOR run. It returns in his report a synthesis between expected time spent and memory consumed versus predictions
    """

    _footprint = dict(
        info="Bateur",
        attr=dict(
            base=dict(
                info        = 'name of the odb base to process',
                type=str,    
            ),
            workdir=dict(
                info        = 'working directory of the run',
                type=str
            ),
            mem=dict(
                info        = 'memory expected in kb',
                type=int,
                default     = 1000,     
            ),
            time=dict(
                info        = 'time expected in second',
                type=int,
                default     = 1,     
            ),
            

        )
    )

    def __init__(self, *args, **kwargs):
        super(Bateur, self).__init__(*args, **kwargs)


    def vortex_task(self, **kwargs):
        import resource
        cwd = self.system.pwd()
        self.system.cd(self.base)
        self.system.env.BATOR_WINDOW_LEN = 360
        self.system.env.BATOR_WINDOW_SHIFT= -180
        self.system.env.BATOR_SLOT_LEN = 30
        self.system.env.BATOR_CENTER_LEN = 30
        self.system.env.ODB_SRCPATH_ECMA  = self.workdir+'ECMA.'+self.base
        self.system.env.ODB_DATAPATH_ECMA = self.workdir+'ECMA.'+self.base
        
        logger.info("Starting Bateur for base=%s", self.base)
        rdict = dict(rc=True)
        list_name = self.system.path.join(cwd,"listing."+self.base)
        try:
            self.local_spawn(list_name)
        except ExecutionError as e:
            rdict['rc'] = e    

        realTime=resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime
        realMem=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        timeRatio=realTime/float(self.time)
        memRatio=realMem/float(self.mem)
        
        rdict['synthesisList']=[self.base,
                                self.mem,
                                realMem,
                                self.time,
                                realTime,
                                memRatio,                                
                                timeRatio,
                                ]
        if (memRatio>0.9):
            status="!update memory constant!"
        elif (timeRatio>1.2):
            status="!update time constant!"
        elif (timeRatio<0.8):
            status="!decrease time constant!"            
        elif (memRatio<0.5):
            status="!decrease memory constant!"               
        else:
            status="ok"
        
        rdict['synthesisList'].append(status)
                       
        # Save a copy of io assign map in the new database
        if self.system.path.isdir(self.system.env.ODB_SRCPATH_ECMA):
            self.system.cp('../IOASSIGN', self.system.env.ODB_SRCPATH_ECMA + '/' + 'IOASSIGN')
        else:
            logger.warning('DataBase not created: ' + self.base)
    
        logger.info("Bateur for base=%s has finished!", self.base)
        return rdict


class OdbProcess(Parallel, odb.OdbComponent):
    """Base class for any ODB alog component."""
 
    _abstract  = True
    _footprint = dict(
        attr = dict(
            date = a_date,
            npool = dict(
                type     = int,
            ),
            iomethod = dict(
                type     = int,
                optional = True,
                default  = 1,
            ),
            slots = dict(
                type     = odb.TimeSlots,
                optional = True,
                default  = odb.TimeSlots(7, chunk='PT1H'),
            ),
            virtualdb = dict(
                optional = True,
                default  = 'ecma',
                access   = 'rwx',
            ),
        )
    )
 
    def input_obs(self):
        """Find any observations with the proper kind, without any regards to role."""
        obsall = [x.rh for x in self.context.sequence.effective_inputs(kind = 'observations')]
        obsall.sort(key=lambda rh: rh.resource.part)
        return obsall
 
    def prepare(self, rh, opts):
        """Mostly used for setting environment."""
        super(OdbProcess, self).prepare(rh, opts)
        self.export('drhook')
        self.odb.setup(
            date     = self.date,
            npool    = self.npool,
            nslot    = self.slots.nslot,
            iomethod = self.iomethod,
        )
 
 
class Raw2ODB(OdbProcess):
    """Convert raw observations files to ODB."""
 
    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['raw2odb', 'bufr2odb', 'obsoul2odb'],
                remap  = dict(
                    bufr2odb   = 'raw2odb',
                    obsoul2odb = 'raw2odb',
                )
            ),
            ioassign = dict(),
            lamflag = dict(
                type     = bool,
                optional = True,
                default  = False,
            ),
            ontime = dict(
                type     = bool,
                optional = True,
                default  = True,
            ),
            mapall = dict(
                type     = bool,
                optional = True,
                default  = False,
            ),
            maponly = dict(
                type     = bool,
                optional = True,
                default  = False,
            ),
            member = dict(
                info            = ("The current member's number " +
                                   "(may be omitted in deterministibasec configurations)."),
                optional        = True,
                type            = int,
            ),
        )
    )
 
    def __init__(self, *kargs, **kwargs):
        super(Raw2ODB, self).__init__(*kargs, **kwargs)
        self.obspack = dict()
        self.obsmapout = list()
 
    def input_obs(self):
        """Find out which are the usable observations."""
        obsall = super(Raw2ODB, self).input_obs()
 
        # Looking for valid raw observations
        sizemin = self.env.VORTEX_OBS_SIZEMIN or 80
        obsok   = list()
        for rhobs in obsall:
            logger.info('Inspect observation ' + rhobs.resource.part)
            if rhobs.resource.nativefmt == 'odb':
                logger.warning('Observations set [%s] is ODB ready',
                               rhobs.resource.part)
                continue
            if rhobs.container.totalsize < sizemin:
                logger.warning('Observations set [%s] is far too small: %d',
                               rhobs.resource.part, rhobs.container.totalsize)
            else:
                logger.info('Obs size: ' + str(rhobs.container.totalsize))
                obsok.append(Foo(rh=rhobs, refdata=list(), mapped=False))
 
        # Check the observations dates
        for obs in [obs for obs in obsok if obs.rh.resource.date != self.date]:
            logger.warning('Observation [%s] %s [time mismatch: %s / %s]',
                           'discarded' if self.ontime else 'is questionable',
                           obs.rh.resource.part, obs.rh.resource.date.isoformat(),
                           self.date.isoformat())
        if self.ontime:
            obsok = [obs for obs in obsok if obs.rh.resource.date == self.date]
 
        return obsok
 
    def _retrieve_refdatainfo(self, obslist):
        """Look for refdata resources and link their content with the obslist."""
        refmap = dict()
        refall = list(self.context.sequence.effective_inputs(kind = 'refdata'))
        for rdata in refall:
            logger.info('Inspect refdata ' + rdata.rh.container.localpath())
            self.system.subtitle(rdata.role)
            rdata.rh.container.cat()
            for item in rdata.rh.contents:
                refmap[(item.fmt.lower(), item.data, item.instr)] = (rdata.rh, item)
 
        # Build actual refdata
        for obs in obslist:
            thispart = obs.rh.resource.part
            thisfmt  = obs.rh.container.actualfmt.lower()
            logger.info(' '.join(('Building information for [', thisfmt, '/', thispart, ']')))
 
            # Gather equivalent refdata lines
            if not self.system.path.exists('norefdata.' + thispart) and (
                    not self.env.VORTEX_OBSDB_NOREF or
                    not re.search(thispart, self.env.VORTEX_OBSDB_NOREF, re.IGNORECASE)):
                for k, v in refmap.items():
                    x_fmt, x_data = k[:2]
                    if x_fmt == thisfmt and x_data == thispart:
                        rdata, item = v
                        obs.refdata.append(rdata.contents.formatted_data(item))
        return refmap, refall
 
    def _map_refdatainfo(self, refmap, refall, imap, thismap):
        """Associate obsmap entries with refdata entries."""
        thiskey = (imap.fmt.lower(), imap.data, imap.instr)
        if thiskey in refmap:
            rdata, item = refmap[thiskey]
            thismap.refdata.append(rdata.contents.formatted_data(item))
        else:
            logger.warning('Creating automatic refdata entry for ' + str(thiskey))
            item = ObsRefItem(imap.data, imap.fmt, imap.instr, self.date.ymd, self.date.hh)
            if refall:
                thismap.refdata.append(refall[0].rh.contents.formatted_data(item))
            else:
                logger.error('No default for formatting data %s', item)
                thismap.refdata.append(ObsRefContent.formatted_data(item))
 
    @staticmethod
    def _new_obspack_item():
        """Create a now entry in obspack."""
        return Foo(mapping=list(), standalone=False, refdata=list(), obsfile=dict())
 
    def prepare(self, rh, opts):
        """Get a look at raw observations input files."""
 
        sh = self.system
        cycle = rh.resource.cycle
 
        # First create the proper IO assign table
        self.odb.ioassign_create(
            npool    = self.npool,
            ioassign = self.ioassign
        )
 
        # Looking for input observations
        obsok = self.input_obs()
 
        # Building refdata map for direct access to (fmt, data, instr) entries
        if cycle < 'cy42_op1':
            # Refdata information is not needed anymore with cy42_op1
            refmap, refall = self._retrieve_refdatainfo(obsok)
 
        # Looking for obs maps
        mapitems = list()
        for omsec in self.context.sequence.effective_inputs(kind = 'obsmap'):
            logger.info(' '.join(('Gathering information from map',
                                  omsec.rh.container.localpath())))
            sh.subtitle(omsec.role)
            omsec.rh.container.cat()
            mapitems.extend(omsec.rh.contents)
 
        self.obspack = defaultdict(self._new_obspack_item)  # Reset the obspack
        for imap in mapitems:
            # Match observation files and obsmap entries + Various checks
            logger.info('Inspect ' + str(imap))
            candidates = [obs for obs in obsok
                          if (obs.rh.resource.part == imap.data and
                              obs.rh.container.actualfmt.lower() == imap.fmt.lower())]
            if not candidates:
                errmsg = 'No input obsfile could match [data:{0:s}/fmt:{1:s}]'.format(imap.data, imap.fmt)
                if self.mapall:
                    raise ValueError(errmsg)
                else:
                    logger.warning(errmsg)
                    continue
            candidates[-1].mapped = True
            # Build the obspack entry
            thismap = self.obspack[imap.odb]
            thismap.mapping.append(imap)
            thismap.obsfile[imap.fmt.upper() + '.' + imap.data] = candidates[-1]
            # Map refdata and obsmap entries
            if cycle < 'cy42_op1':
                # Refdata information is not needed anymore with cy42_op1
                self._map_refdatainfo(refmap, refall, imap, thismap)
 
        # Deal with observations that are not described in the obsmap
        for notmap in [obs for obs in obsok if not obs.mapped]:
            thispart = notmap.rh.resource.part
            logger.info('Inspect not mapped obs ' + thispart)
            if thispart not in self.obspack:
                thisfmt = notmap.rh.container.actualfmt.upper()
                thismsg = 'standalone obs entry [data:{0:s} / fmt:{1:s}]'.format(thispart, thisfmt)
                if self.maponly:
                    logger.warning('Ignore ' + thismsg)
                else:
                    logger.warning('Active ' + thismsg)
                    thismap = self.obspack[thispart]
                    thismap.standalone = thisfmt
                    thismap.mapping.append(ObsMapItem(thispart, thispart, thisfmt, thispart))
                    thismap.refdata = notmap.refdata
                    thismap.obsfile[thisfmt.upper() + '.' + thispart] = notmap
 
        # Informations about timeslots
        logger.info("The timeslot definition is: %s", str(self.slots))
        if cycle < 'cy42_op1':
            # ficdate is not needed anymore with cy42_op1...
            self.slots.as_file(self.date, 'ficdate')
        else:
            # From cy42_op1 onward, we only need environment variables
            for var, value in self.slots.as_environment().iteritems():
                logger.info('Setting env %s = %s', var, str(value))
                self.env[var] = value
 
        # Let ancestors handling most of the env setting
        super(Raw2ODB, self).prepare(rh, opts)
        self.env.default(
            TIME_INIT_YYYYMMDD = self.date.ymd,
            TIME_INIT_HHMMSS   = self.date.hm + '00',
        )
        if self.lamflag:
            for lamvar in ('BATOR_LAMFLAG', 'BATODB_LAMFLAG'):
                logger.info('Setting env %s = %d', lamvar, 1)
                self.env[lamvar] = 1
 
        if self.member is not None:
            for nam in self.context.sequence.effective_inputs(kind=('namelist', 'namelistfp')):
                nam.rh.contents.setmacro('MEMBER', self.member)
                logger.info('Setup macro MEMBER=%s in %s', self.member, nam.rh.container.actualpath())
                nam.rh.save()
 
    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""
 
        sh = self.system
        cycle = rh.resource.cycle
 
        batnam = [x.rh for x in self.context.sequence.effective_inputs(role = 'NamelistBatodb')]
 
        self.obsmapout = list()  # Reset the obsmapout
 
        for odbset, thispack in self.obspack.items():
            odbname = self.virtualdb.upper() + '.' + odbset
            sh.title('ODB set ' + odbname)
 
            # Make a soft link when necessary
            linked = list()
            for obsname, obsinfo in thispack.obsfile.items():
                if sh.path.islink(obsname):
                    sh.remove(obsname)
                if obsname != obsinfo.rh.container.localpath():
                    sh.softlink(obsinfo.rh.container.localpath(), obsname)
                    logger.info('creating softlink: %s -> %s', obsname,
                                obsinfo.rh.container.localpath())
                    linked.append(obsname)
                if thispack.standalone and cycle < 'cy42_op1':
                    sh.softlink(obsinfo.rh.container.localpath(), thispack.standalone)
                    logger.info('creating softlink: %s -> %s', thispack.standalone,
                                obsinfo.rh.container.localpath())
                    linked.append(thispack.standalone)
 
            # Fill the actual refdata according to information gathered in prepare stage
            if cycle < 'cy42_op1':
                if thispack.refdata:
                    with io.open('refdata', 'w') as fd:
                        for rdentry in thispack.refdata:
                            fd.write(unicode(rdentry + "\n"))
                    sh.subtitle('Local refdata')
                    sh.cat('refdata', output=False)
            # Drive bator with a batormap file (from cy42_op1 onward)
            else:
                with io.open('batormap', 'w') as fd:
                    for mapentry in sorted(thispack.mapping):
                        fd.write(unicode(ObsMapContent.formatted_data(mapentry) + '\n'))
                sh.subtitle('Local batormap')
                sh.cat('batormap', output=False)
 
            # Give a glance to the actual namelist
            if batnam:
                sh.subtitle('Namelist Raw2ODB')
                batnam[0].container.cat()
 
            # Standard execution
            self.env.ODB_SRCPATH_ECMA  = sh.path.abspath(odbname)
            self.env.ODB_DATAPATH_ECMA = sh.path.abspath(odbname)
            try:
                super(Raw2ODB, self).execute(rh, opts)
            except ExecutionError:
                customised = ExecutionError("Error while processing the {} database.".format(odbname))
                self.delayed_exception_add(customised)
 
            # Save current stdout
            if sh.path.exists('stdeo.0'):
                sh.mv('stdeo.0', 'listing.' + odbset)
 
            # Some cleaning
            sh.header('Partial cleaning for ' + odbname)
            sh.remove('refdata')
            sh.remove('batormap')
            for obslink in linked:
                sh.remove(obslink)
 
            # Save a copy of io assign map in the new database
            if sh.path.isdir(odbname):
                sh.cp('IOASSIGN', odbname + '/' + 'IOASSIGN')
                self.obsmapout.extend(thispack.mapping)
            else:
                logger.warning('DataBase not created: ' + odbname)
 
    def postfix(self, rh, opts):
        """Post conversion cleaning."""
 
        # Remove empty ECMA databases from the output obsmap
        self.obsmapout = [x for x in self.obsmapout
                          if self.system.path.isdir('ECMA.' + x.odb + '/1')]
 
        # Generate the output bator_map
        with io.open('batodb_map.out', 'w') as fd:
            for x in sorted(self.obsmapout):
                fd.write(unicode(ObsMapContent.formatted_data(x) + '\n'))
 
        # Generate a global refdata (if cycle allows it and if possible)
        if rh.resource.cycle < 'cy42_op1':
            rdrh_dict = {y.rh.resource.part: y.rh
                         for y in self.context.sequence.effective_inputs(kind = 'refdata')
                         if y.rh.resource.part != 'all'}
            with io.open('refdata_global', 'w') as rdg:
                for x in sorted(self.obsmapout):
                    if (x.data in rdrh_dict and
                            self.system.path.getsize(rdrh_dict[x.data].container.localpath()) > 0):
                        with io.open(rdrh_dict[x.data].container.localpath(), 'r') as rdl:
                            rdg.write(rdl.readline())
                    elif (self.system.path.exists('refdata.' + x.data) and
                          self.system.path.getsize('refdata.' + x.data) > 0):
                        with io.open('refdata.' + x.data, 'r') as rdl:
                            rdg.write(rdl.readline())
                    else:
                        logger.info("Unable to create a global refdata entry for data=" + x.data)
 
        super(Raw2ODB, self).postfix(rh, opts)


class OdbProcessParallel(TaylorRun, odb.OdbComponent):
    """Base class for any ODB algo component."""

    _abstract  = True
    _footprint = dict(
        attr = dict(
            date = a_date,
            npool = dict(
                type     = int,
            ),
            iomethod = dict(
                type     = int,
                optional = True,
                default  = 1,
            ),
            slots = dict(
                type     = odb.TimeSlots,
                optional = True,
                default  = odb.TimeSlots(7, chunk='PT1H'),
            ),
            virtualdb = dict(
                optional = True,
                default  = 'ecma',
                access   = 'rwx',
            ),
        )
    )

    def input_obs(self):
        """Find any observations with the proper kind, without any regards to role."""
        obsall = [x.rh for x in self.context.sequence.effective_inputs(kind = 'observations')]
        obsall.sort(key=lambda rh: rh.resource.part)
        return obsall

    def prepare(self, rh, opts):
        """Mostly used for setting environment."""
        super(OdbProcessParallel, self).prepare(rh, opts)
        self.export('drhook')
        self.odb.setup(
            date     = self.date,
            npool    = self.npool,
            nslot    = self.slots.nslot,
            iomethod = self.iomethod,
        )


class Raw2ODBparallel(OdbProcessParallel):
    """Convert raw observations files to ODB using taylorism."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['raw2odbparallel', 'bufr2odbparallel', 'obsoul2odbparallel'],
                remap  = dict(
                    bufr2odb   = 'raw2odbparallel',
                    obsoul2odb = 'raw2odbparallel',
                )
            ),
            ioassign = dict(),
            lamflag = dict(
                type     = bool,
                optional = True,
                default  = False,
            ),
            ontime = dict(
                type     = bool,
                optional = True,
                default  = True,
            ),
            mapall = dict(
                type     = bool,
                optional = True,
                default  = False,
            ),
            maponly = dict(
                type     = bool,
                optional = True,
                default  = False,
            ),
            member = dict(
                info            = ("The current member's number " +
                                   "(may be omitted in deterministibasec configurations)."),
                optional        = True,
                type            = int,
            ),
            maxmemory = dict(
                type     = int,
                optional = True,
                default  =  dict((i.split()[0].rstrip(':'),int(i.split()[1])) for i in open('/proc/meminfo').readlines())['MemTotal']
            ),                    
        )
    )

    def __init__(self, *kargs, **kwargs):
        super(Raw2ODBparallel, self).__init__(*kargs, **kwargs)
        self.obspack = dict()
        self.obsmapout = list()

    def input_obs(self):
        """Find out which are the usable observations."""
        obsall = super(Raw2ODBparallel, self).input_obs()

        # Looking for valid raw observations
        sizemin = self.env.VORTEX_OBS_SIZEMIN or 80
        obsok   = list()
        for rhobs in obsall:
            logger.info('Inspect observation ' + rhobs.resource.part)
            if rhobs.resource.nativefmt == 'odb':
                logger.warning('Observations set [%s] is ODB ready',
                               rhobs.resource.part)
                continue
            if rhobs.container.totalsize < sizemin:
                logger.warning('Observations set [%s] is far too small: %d',
                               rhobs.resource.part, rhobs.container.totalsize)
            else:
                logger.info('Obs size: ' + str(rhobs.container.totalsize))
                obsok.append(Foo(rh=rhobs, refdata=list(), mapped=False))

        # Check the observations dates
        for obs in [obs for obs in obsok if obs.rh.resource.date != self.date]:
            logger.warning('Observation [%s] %s [time mismatch: %s / %s]',
                           'discarded' if self.ontime else 'is questionable',
                           obs.rh.resource.part, obs.rh.resource.date.isoformat(),
                           self.date.isoformat())
        if self.ontime:
            obsok = [obs for obs in obsok if obs.rh.resource.date == self.date]

        return obsok

    def _retrieve_refdatainfo(self, obslist):
        """Look for refdata resources and link their content with the obslist."""
        refmap = dict()
        refall = list(self.context.sequence.effective_inputs(kind = 'refdata'))
        for rdata in refall:
            logger.info('Inspect refdata ' + rdata.rh.container.localpath())
            self.system.subtitle(rdata.role)
            rdata.rh.container.cat()
            for item in rdata.rh.contents:
                refmap[(item.fmt.lower(), item.data, item.instr)] = (rdata.rh, item)

        # Build actual refdata
        for obs in obslist:
            thispart = obs.rh.resource.part
            thisfmt  = obs.rh.container.actualfmt.lower()
            logger.info(' '.join(('Building information for [', thisfmt, '/', thispart, ']')))

            # Gather equivalent refdata lines
            if not self.system.path.exists('norefdata.' + thispart) and (
                    not self.env.VORTEX_OBSDB_NOREF or
                    not re.search(thispart, self.env.VORTEX_OBSDB_NOREF, re.IGNORECASE)):
                for k, v in refmap.items():
                    x_fmt, x_data = k[:2]
                    if x_fmt == thisfmt and x_data == thispart:
                        rdata, item = v
                        obs.refdata.append(rdata.contents.formatted_data(item))
        return refmap, refall

    def _map_refdatainfo(self, refmap, refall, imap, thismap):
        """Associate obsmap entries with refdata entries."""
        thiskey = (imap.fmt.lower(), imap.data, imap.instr)
        if thiskey in refmap:
            rdata, item = refmap[thiskey]
            thismap.refdata.append(rdata.contents.formatted_data(item))
        else:
            logger.warning('Creating automatic refdata entry for ' + str(thiskey))
            item = ObsRefItem(imap.data, imap.fmt, imap.instr, self.date.ymd, self.date.hh)
            if refall:
                thismap.refdata.append(refall[0].rh.contents.formatted_data(item))
            else:
                logger.error('No default for formatting data %s', item)
                thismap.refdata.append(ObsRefContent.formatted_data(item))

    @staticmethod
    def _new_obspack_item():
        """Create a now entry in obspack."""
        return Foo(mapping=list(), standalone=False, refdata=list(), obsfile=dict())

    def prepare(self, rh, opts):
        """Get a look at raw observations input files."""

        sh = self.system
        cycle = rh.resource.cycle

        # First create the proper IO assign table
        self.odb.ioassign_create(
            npool    = self.npool,
            ioassign = self.ioassign
        )

        # Looking for input observations
        obsok = self.input_obs()

        # Building refdata map for direct access to (fmt, data, instr) entries
        if cycle < 'cy42_op1':
            # Refdata information is not needed anymore with cy42_op1
            refmap, refall = self._retrieve_refdatainfo(obsok)

        # Looking for obs maps
        mapitems = list()
        for omsec in self.context.sequence.effective_inputs(kind = 'obsmap'):
            logger.info(' '.join(('Gathering information from map',
                                  omsec.rh.container.localpath())))
            sh.subtitle(omsec.role)
            omsec.rh.container.cat()
            mapitems.extend(omsec.rh.contents)

        self.obspack = defaultdict(self._new_obspack_item)  # Reset the obspack
        for imap in mapitems:
            # Match observation files and obsmap entries + Various checks
            logger.info('Inspect ' + str(imap))
            candidates = [obs for obs in obsok
                          if (obs.rh.resource.part == imap.data and
                              obs.rh.container.actualfmt.lower() == imap.fmt.lower())]
            if not candidates:
                errmsg = 'No input obsfile could match [data:{0:s}/fmt:{1:s}]'.format(imap.data, imap.fmt)
                if self.mapall:
                    raise ValueError(errmsg)
                else:
                    logger.warning(errmsg)
                    continue
            candidates[-1].mapped = True
            # Build the obspack entry
            thismap = self.obspack[imap.odb]
            thismap.mapping.append(imap)
            thismap.obsfile[imap.fmt.upper() + '.' + imap.data] = candidates[-1]
            # Map refdata and obsmap entries
            if cycle < 'cy42_op1':
                # Refdata information is not needed anymore with cy42_op1
                self._map_refdatainfo(refmap, refall, imap, thismap)

        # Deal with observations that are not described in the obsmap
        for notmap in [obs for obs in obsok if not obs.mapped]:
            thispart = notmap.rh.resource.part
            logger.info('Inspect not mapped obs ' + thispart)
            if thispart not in self.obspack:
                thisfmt = notmap.rh.container.actualfmt.upper()
                thismsg = 'standalone obs entry [data:{0:s} / fmt:{1:s}]'.format(thispart, thisfmt)
                if self.maponly:
                    logger.warning('Ignore ' + thismsg)
                else:
                    logger.warning('Active ' + thismsg)
                    thismap = self.obspack[thispart]
                    thismap.standalone = thisfmt
                    thismap.mapping.append(ObsMapItem(thispart, thispart, thisfmt, thispart))
                    thismap.refdata = notmap.refdata
                    thismap.obsfile[thisfmt.upper() + '.' + thispart] = notmap

        # Informations about timeslots
        logger.info("The timeslot definition is: %s", str(self.slots))
        if cycle < 'cy42_op1':
            # ficdate is not needed anymore with cy42_op1...
            self.slots.as_file(self.date, 'ficdate')
        else:
            # From cy42_op1 onward, we only need environment variables
            for var, value in self.slots.as_environment().iteritems():
                logger.info('Setting env %s = %s', var, str(value))
                self.env[var] = value

        # Let ancestors handling most of the env setting
        super(Raw2ODBparallel, self).prepare(rh, opts)
        self.env.default(
            TIME_INIT_YYYYMMDD = self.date.ymd,
            TIME_INIT_HHMMSS   = self.date.hm + '00',
        )
        if self.lamflag:
            for lamvar in ('BATOR_LAMFLAG', 'BATODB_LAMFLAG'):
                logger.info('Setting env %s = %d', lamvar, 1)
                self.env[lamvar] = 1

        if self.member is not None:
            for nam in self.context.sequence.effective_inputs(kind=('namelist', 'namelistfp')):
                nam.rh.contents.setmacro('MEMBER', self.member)
                logger.info('Setup macro MEMBER=%s in %s', self.member, nam.rh.container.actualpath())
                nam.rh.save()

    def _default_pre_execute(self, rh, opts):
        '''Change default initialisation to use LongerFirstScheduler'''
        # Start the task scheduler
        self._boss = Boss(verbose=self.verbose,
                          scheduler=LongerFirstScheduler(max_threads=self.ntasks,max_memory=self.maxmemory))
        self._boss.make_them_work()


    def execute(self, rh, opts):
        """For each base, a directory is created such that each worker works in his directory.
        Symlinks are created into these working directories. """

        sh = self.system
        cycle = rh.resource.cycle

        batnam = [x.rh for x in self.context.sequence.effective_inputs(role = 'NamelistBatodb')]

        self.obsmapout = list()  # Reset the obsmapout
        odbInputSize=dict()
        
        workdir=sh.pwd()+'/'
        for odbset, thispack in self.obspack.items():
            odbname = self.virtualdb.upper() + '.' + odbset
            sh.title('ODB set ' + odbname)
            sh.mkdir(odbset)
            sh.cd(odbset)
            inputSize=0

            
            for obsname, obsinfo in thispack.obsfile.items():
                for inpt in self.context.sequence.inputs():
                    if ('usualtools' not in inpt.rh.container.localpath() and not (inpt.role == 'Observations')):
                        if not (sh.path.exists(inpt.rh.container.localpath())):
                            sh.softlink(workdir+inpt.rh.container.localpath(),inpt.rh.container.localpath())                    
                                
                logger.info('creating softlink: %s -> %s', obsname,
                            workdir+obsinfo.rh.container.localpath())
                sh.softlink(workdir+obsinfo.rh.container.localpath(),obsname)
                
                if thispack.standalone and cycle < 'cy42_op1':
                    sh.softlink(workdir+obsinfo.rh.container.localpath(), thispack.standalone)
                    logger.info('creating softlink: %s -> %s', thispack.standalone,
                                workdir+obsinfo.rh.container.localpath())
                    
                inputSize+=obsinfo.rh.container.totalsize
                
            # Fill the actual refdata according to information gathered in prepare stage
            if cycle < 'cy42_op1':
                if thispack.refdata:
                    with io.open('refdata', 'w') as fd:
                        for rdentry in thispack.refdata:
                            fd.write(unicode(rdentry + "\n"))
#                     sh.subtitle('Local refdata')
#                     sh.cat('refdata', output=False)
            # Drive bator with a batormap file (from cy42_op1 onward)
            else:
                with io.open('batormap', 'w') as fd:
                    for mapentry in sorted(thispack.mapping):
                        fd.write(unicode(ObsMapContent.formatted_data(mapentry) + '\n'))



            
            odbInputSize[odbset]=inputSize
            self.obsmapout.extend(thispack.mapping)
            sh.cd('..')
            
        # Give a glance to the actual namelist
        if batnam:
            sh.subtitle('Namelist Raw2ODB')
            batnam[0].container.cat()            

        # mem time
        parallelConst=dict()
        parallelConst['airs']=(0.19,4.5)    
        parallelConst['atms']=(0.06,1.5) 
        parallelConst['conv']=(0.55,4) 
        parallelConst['cris']=(0.07,1.) 
        parallelConst['geow']=(0.06,3.5) 
        parallelConst['gmi']=(0.07,1.0) 
        parallelConst['gps']=(0.62,8) 
        parallelConst['gpssol']=(0.08,3) 
        parallelConst['iasi']=(0.06,1.5) 
        parallelConst['mwhsx']=(0.08,1.7) 
        parallelConst['scat']=(0.12,3.8) 
        parallelConst['sev']=(0.08,3.0) 
        parallelConst['ssmis']=(0.09,3.5) 
        parallelConst['tovsa']=(0.20,6) 
        parallelConst['tovsb']=(0.05,1.4) 
        parallelConst['tovsh']=(0.15,1.9) 
        parallelConst['virtual']=(0.07,4.5) 
        parallelConst['default']=(0.5,20) 
        
        schedulerInstructions=[]
        
        for b in odbInputSize.keys():
            if b in parallelConst.keys():
                bTime=odbInputSize[b] * parallelConst[b][1]  / 10000000
                bMemory=odbInputSize[b] * parallelConst[b][0] 
                odbInputSize.pop(b, None)
            else:
                bTime=odbInputSize[b] * parallelConst['default'][1]  / 10000000
                bMemory=odbInputSize[b] * parallelConst['default'][0] 
                odbInputSize.pop(b, None)
            schedulerInstructions.append((b,bMemory,bTime))

        synthesis=""
        baseList=[]
        memList=[]
        timeList=[]
        for base,mem,time in schedulerInstructions:
            baseList.append(base)
            memList.append(mem)
            timeList.append(time)
        
        sh.subtitle('Launching Parallel Bator Run')
        boss = run_as_server(common_instructions={'workdir':workdir,
                                       'progname':'./BATODB.EX'},
                        individual_instructions={'base': baseList,
                                                 'mem':memList,
                                                 'time':timeList,
                                                 'scheduler_ticket': range(0,len(baseList))},
                        scheduler=LongerFirstScheduler(max_memory=self.maxmemory,max_threads=self.ntasks),
                        verbose=False)
        boss.wait_till_finished()
        sh.subtitle('Parallel Bator Run is finished! Printing report')
        
        report = boss.get_report()
        reportList=[]
        for l in report['workers_report']:
            reportList.append(l['report']['synthesisList'])
        #sort alphabetically
        reportList.sort() 
        row_format ="{:>15}" * (8)            
        cols=['base','pred memory','used memory','pred time','elapsed time','mem ratio','time ratio','status']
        logger.info((row_format.format(*cols))) 
        for row in  reportList:
            logger.info((row_format.format(*row)))    
        sh.subtitle('End of report')

    def postfix(self, rh, opts):
        """Post conversion cleaning."""

        # Remove empty ECMA databases from the output obsmap
        self.obsmapout = [x for x in self.obsmapout
                          if self.system.path.isdir('ECMA.' + x.odb + '/1')]

        # Generate the output bator_map
        with io.open('batodb_map.out', 'w') as fd:
            for x in sorted(self.obsmapout):
                fd.write(unicode(ObsMapContent.formatted_data(x) + '\n'))

        # Generate a global refdata (if cycle allows it and if possible)
        if rh.resource.cycle < 'cy42_op1':
            rdrh_dict = {y.rh.resource.part: y.rh
                         for y in self.context.sequence.effective_inputs(kind = 'refdata')
                         if y.rh.resource.part != 'all'}
            with io.open('refdata_global', 'w') as rdg:
                for x in sorted(self.obsmapout):
                    if (x.data in rdrh_dict and
                            self.system.path.getsize(rdrh_dict[x.data].container.localpath()) > 0):
                        with io.open(rdrh_dict[x.data].container.localpath(), 'r') as rdl:
                            rdg.write(rdl.readline())
                    elif (self.system.path.exists('refdata.' + x.data) and
                          self.system.path.getsize('refdata.' + x.data) > 0):
                        with io.open('refdata.' + x.data, 'r') as rdl:
                            rdg.write(rdl.readline())
                    else:
                        logger.info("Unable to create a global refdata entry for data=" + x.data)

        super(Raw2ODBparallel, self).postfix(rh, opts)



class OdbAverage(OdbProcess):
    """TODO the father of this component is very much welcome."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['average'],
            ),
            ioassign = dict(),
            outdb = dict(
                optional = True,
                default  = 'ccma',
                value    = ['ecma', 'ccma'],
            ),
            maskname = dict(
                optional = True,
                default  = 'mask4x4.txt',
            ),
        )
    )

    def prepare(self, rh, opts):
        """Find any ODB candidate in input files."""

        sh = self.system

        # Looking for input observations
        obsall = [x for x in self.input_obs() if x.resource.layout == 'ecma']

        # One database at a time
        if not obsall:
            raise ValueError('Could not find any ECMA input')
        self.bingo = ecma = obsall[0]

        # First create a fake CCMA
        self.layout_new = self.outdb.upper()
        sh.mkdir(self.layout_new)
        ccma_path = sh.path.abspath(self.layout_new)
        ccma_io   = sh.path.join(ccma_path, 'IOASSIGN')
        self.layout_in = ecma.resource.layout.upper()
        ecma_path = sh.path.abspath(ecma.container.localpath())
        ecma_pool = sh.path.join(ecma_path, '1')

        if not sh.path.isdir(ecma_pool):
            logger.error('The input ECMA base is empty')
            self.abort('No ECMA input')
            return

        ecma_io = sh.path.join(ecma_path, 'IOASSIGN')
        self.env.ODB_SRCPATH_CCMA  = ccma_path
        self.env.ODB_DATAPATH_CCMA = ccma_path
        self.env.ODB_SRCPATH_ECMA  = ecma_path
        self.env.ODB_DATAPATH_ECMA = ecma_path

        # Some extra settings
        self.env.update(
            ODB_CCMA_CREATE_POOLMASK = 1,
            ODB_CCMA_POOLMASK_FILE   = sh.path.join(ccma_path, self.layout_new + '.poolmask'),
            TO_ODB_CANARI            = 0,
            TO_ODB_REDUC             = self.env.TO_ODB_REDUC or 1,
            TO_ODB_SETACTIVE         = 1,
        )

        # Then create the proper IO assign table
        self.odb.ioassign_create(
            layout   = self.layout_new,
            npool    = self.npool,
            ioassign = self.ioassign
        )

        sh.cat(ecma_io, 'IOASSIGN', output='IOASSIGN.full')
        sh.mv('IOASSIGN.full', 'IOASSIGN')
        sh.cp('IOASSIGN', ccma_io)
        sh.cp('IOASSIGN', ecma_io)

        # Let ancesters handling most of the env setting
        super(OdbAverage, self).prepare(rh, opts)

    def spawn_command_options(self):
        """Prepare command line options to binary."""
        return dict(
            dbin     = self.layout_in,
            dbout    = self.layout_new,
            npool    = self.npool,
            nslot    = self.slots.nslot,
            date     = self.date,
            masksize = 4,
        )

    def execute(self, rh, opts):
        """ to mask input."""

        sh = self.system

        mask = [x.rh for x in self.context.sequence.effective_inputs(kind = 'atmsmask')]
        if not mask:
            raise ValueError('Could not find any MASK input')

        # Have a look to mask file
        if mask[0].container.localpath() != self.maskname:
            sh.softlink(mask[0].container.localpath(), self.maskname)

        sh.subtitle('Mask')
        mask[0].container.cat()

        # Standard execution
        super(OdbAverage, self).execute(rh, opts)

    def postfix(self, rh, opts):
        """Post shuffle / average cleaning."""
        sh = self.system

        with sh.cdcontext(self.layout_new):
            for ccma in sh.glob('{0:s}.*'.format(self.layout_new)):
                slurp = sh.cat(ccma, outsplit=False).replace(self.layout_new, self.layout_in)
                with io.open(ccma.replace(self.layout_new, self.layout_in), 'w') as fd:
                    fd.write(unicode(slurp))
                sh.rm(ccma)

        sh.mv(self.layout_new, self.layout_in + '.' + self.bingo.resource.part)

        super(OdbAverage, self).postfix(rh, opts)


class OdbMatchup(OdbProcess):
    """Report some information from post-minim CCMA to post-screening ECMA base."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['matchup'],
            ),
        )
    )

    def prepare(self, rh, opts):
        """Find ODB candidates in input files."""

        sh = self.system

        # Looking for input observations
        obsscr = [
            x for x in self.input_obs()
            if x.resource.stage.startswith('screen') and x.resource.part == 'virtual'
        ]
        obscompressed = [
            x for x in self.input_obs()
            if x.resource.stage.startswith('min') or x.resource.stage.startswith('traj')
        ]

        # One database at a time
        if not obsscr:
            raise ValueError('Could not find any ODB screening input')
        if not obscompressed:
            raise ValueError('Could not find any ODB minim input')

        # Set actual layout and path
        ecma = obsscr.pop(0)
        ccma = obscompressed.pop(0)
        self.layout_screening  = ecma.resource.layout
        self.layout_compressed = ccma.resource.layout
        ecma_path = sh.path.abspath(ecma.container.localpath())
        ccma_path = sh.path.abspath(ccma.container.localpath())
        self.env.ODB_SRCPATH_CCMA  = ccma_path
        self.env.ODB_DATAPATH_CCMA = ccma_path
        self.env.ODB_SRCPATH_ECMA  = ecma_path
        self.env.ODB_DATAPATH_ECMA = ecma_path

        sh.cp(sh.path.join(ecma_path, 'ECMA.dd'), sh.path.join(ccma_path, 'ECMA.dd'))
        sh.cat(
            sh.path.join(ccma_path, 'IOASSIGN'),
            sh.path.join(ecma_path, 'IOASSIGN'),
            output='IOASSIGN'
        )

        # Let ancesters handling most of the env setting
        super(OdbMatchup, self).prepare(rh, opts)

    def spawn_command_options(self):
        """Prepare command line options to binary."""
        return dict(
            dbin     = self.layout_compressed,
            dbout    = self.layout_screening,
            npool    = self.npool,
            nslot    = self.slots.nslot,
            date     = self.date,
            fcma     = self.layout_compressed,
        )


class FlagsCompute(OdbProcess):
    """Compute observations flags."""

    _footprint = dict(
        info = 'Computation of observations flags.',
        attr = dict(
            kind = dict(
                values = ['flagscomp'],
            ),
            ioassign = dict(),
            iomethod = dict(
                type = int,
                default = 1,
                optional = True,
            ),
            npool = dict(
                default = 1,
                type = int,
                optional = True,
            ),
        ),
    )

    def prepare(self, rh, opts):
        """Prepare the execution."""
        # Look for the input databases
        input_databases = self.context.sequence.effective_inputs(
            role = 'ECMA',
            kind = 'observations',
        )
        # Check that there is at least one database
        if len(input_databases) < 1:
            logger.exception('No database in input. Stop.')
            raise AttributeError
        self.odb.ioassign_create(
            npool=self.npool,
        )
        # Let ancesters handling most of the env setting
        super(FlagsCompute, self).prepare(rh, opts)

    def spawn(self, args, opts):
        """Spawn the binary."""
        # Look for the input databases
        input_databases = self.context.sequence.effective_inputs(
            role = 'ECMA',
            kind = 'observations',
        )
        for input_database in input_databases:
            ecma = input_database.rh
            ecma_filename = ecma.container.filename
            ecma_part = ecma.resource.part
            ecma_abspath = ecma.container.abspath
            self.env.ODB_SRCPATH_ECMA  = ecma_abspath
            logger.info('Variable %s set to %s.', 'ODB_SRCPATH_ECMA', ecma_abspath)
            self.env.ODB_DATAPATH_ECMA = ecma_abspath
            logger.info('Variable %s set to %s.', 'ODB_DATAPATH_ECMA', ecma_abspath)
            self.env.setvar('ODB_ECMA', ecma_filename)
            logger.info('Variable %s set to %s.', 'ODB_ECMA', ecma_filename)
            if not self.system.path.exists('IOASSIGN'):
                self.system.cp('/'.join([ecma_filename, 'IOASSIGN']), 'IOASSIGN')
            # Let ancesters handling most of the env setting
            super(FlagsCompute, self).spawn(args, opts)
            # Rename the output file according to the name of the part of the observations treated
            self.system.mv('BDM_CQ', '_'.join(['BDM_CQ', ecma_part]))
