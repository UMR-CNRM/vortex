#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re, io

from vortex.autolog import logdefault as logger

from vortex.tools import date, odb

from vortex.algo.components import Parallel
from vortex.util.structs    import Foo
from vortex.syntax.stdattrs import a_date

from common.data.obs import ObsMapContent, ObsMapItem, ObsRefItem

from footprints import dump


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
        obsall = [ x.rh for x in self.context.sequence.effective_inputs(kind = 'observations') ]
        obsall.sort(lambda a, b: cmp(a.resource.part, b.resource.part))
        return obsall

    def prepare(self, rh, opts):
        """Mostly used for setting environment."""
        super(OdbProcess, self).prepare(rh, opts)
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
        )
    )

    def prepare(self, rh, opts):
        """Get a look at raw observations input files."""

        sh = self.system

        # First create the proper IO assign table
        self.odb.ioassign_create(
            npool    = self.npool,
            ioassign = self.ioassign
        )

        # Looking for input observations
        obsall = self.input_obs()

        # Looking for valid raw observations
        sizemin = self.env.VORTEX_OBS_SIZEMIN or 80
        obsok   = list()
        for ro in obsall:
            logger.info('Inspect observation ' + ro.resource.part)
            if ro.resource.nativefmt == 'odb':
                logger.warning('Observations set [%s] is ODB ready', ro.resource.part)
                continue
            if ro.container.totalsize < sizemin:
                logger.warning('Observations set [%s] is far too small: %d', ro.resource.part, ro.container.totalsize)
            else:
                logger.info('Obs size: ' + str(ro.container.totalsize))
                obsok.append(Foo(rh=ro, refdata=list(), mapped=False, discarded=False))

        # Building refdata map for direct access to (fmt, data, instr) entries
        refmap = dict()
        refall = [ x.rh for x in self.context.sequence.effective_inputs(kind = 'refdata') ]
        for rd in refall:
            logger.info('Inspect refdata ' + rd.container.localpath())
            sh.subtitle(rd.role)
            rd.container.cat()
            for item in rd.contents:
                refmap[(item.fmt.lower(), item.data, item.instr)] = (rd, item)

        # Build actual refdata
        for obs in obsok:
            thisdate = obs.rh.resource.date
            thispart = obs.rh.resource.part
            thisfmt  = obs.rh.container.actualfmt.lower()
            logger.info(' '.join(('Building information for [', thisfmt, '/', thispart, ']')))

            # Check date
            if thisdate != self.date:
                logger.error('Run date [%s] is not obs date [%s]', thisdate.isoformat(), self.date.isoformat())

            # Gather equivalent refdata lines
            if not sh.path.exists('norefdata.' + thispart) and (
                not self.env.VORTEX_OBSDB_NOREF or not re.search(thispart, self.env.VORTEX_OBSDB_NOREF, re.IGNORECASE)
            ):
                for k, v in refmap.items():
                    x_fmt, x_data, x_instr = k
                    if x_fmt == thisfmt and x_data == thispart:
                        rd, item = v
                        obs.refdata.append(rd.contents.formatted_data(item))

        # Looking for obs maps
        mapitems = list()
        for om in [ x.rh for x in self.context.sequence.effective_inputs(kind = 'obsmap') ]:
            logger.info(' '.join(('Gathering information from map', om.container.localpath())))
            sh.subtitle(om.role)
            om.container.cat()
            mapitems.extend(om.contents)

        # Building actual map / refdata correspondance
        self.obspack = dict()
        for imap in mapitems:
            logger.info('Inspect ' + str(imap))
            candidates = [
                obs for obs in obsok
                    if obs.rh.resource.part == imap.data and obs.rh.container.actualfmt.lower() == imap.fmt.lower()
            ]
            for obs in candidates:
                obs.mapped = True
                if self.ontime and obs.rh.resource.date != self.date:
                    obs.discarded = True
                    logger.warning(
                        'Observation [%s] discarded [time mismatch: %s / %s]',
                        obs.rh.resource.date.isoformat(),
                        self.date.isoformat()
                    )
            candidates = [ obs for obs in candidates if not obs.discarded ]
            if not candidates:
                errmsg = 'No input obsfile could match [data:{0:s}/fmt:{1:s}]'.format(imap.data, imap.fmt)
                if self.mapall:
                    raise ValueError(errmsg)
                else:
                    logger.warning(errmsg)
                    continue
            self.obspack.setdefault(imap.odb, Foo())
            thismap = self.obspack.get(imap.odb)
            thismap.setdefault('mapping', list())
            thismap.mapping.append(imap)
            thismap.setdefault('standalone', False)
            thismap.setdefault('refdata', list())
            thismap.setdefault('obsfile', dict())
            thismap.obsfile[imap.fmt.upper() + '.' + imap.data] = candidates[-1]
            thiskey = (imap.fmt.lower(), imap.data, imap.instr)
            if thiskey in refmap:
                rd, item = refmap[thiskey]
                thismap.refdata.append(rd.contents.formatted_data(item))
            else:
                logger.warning('Creating automatic refdata entry for ' + str(thiskey))
                item = ObsRefItem(imap.data, imap.fmt, imap.instr, self.date.ymd, self.date.hh)
                if refall:
                    thismap.refdata.append(refall[0].contents.formatted_data(item))
                else:
                    logger.critical('No way to format data %s', item)
                    raise ValueError('No default refdata contents to produced formatted data')

        for notmap in [ obs for obs in obsok if not obs.mapped ]:
            thispart = notmap.rh.resource.part
            logger.info('Inspect not mapped obs ' + thispart)
            if thispart not in self.obspack:
                thisfmt = notmap.rh.container.actualfmt.upper()
                thismsg = 'standalone obs entry [data:{0:s} / fmt:{1:s}]'.format(thispart, thisfmt)
                if self.maponly:
                    logger.warning('Ignore ' + thismsg)
                else:
                    logger.warning('Active ' + thismsg)
                    self.obspack.setdefault(thispart, Foo())
                    thismap = self.obspack.get(thispart)
                    thismap.setdefault('mapping', list())
                    thismap.setdefault('standalone', thisfmt)
                    thismap.mapping.append(ObsMapItem(thispart, thispart, thisfmt, 'unknown'))
                    thismap.setdefault('refdata', notmap.refdata)
                    thismap.setdefault('obsfile', dict())
                    thismap.obsfile[thisfmt.upper() + '.' + thispart] = notmap

        # Produces a file with time slots boundaries
        self.slots.as_file(self.date, 'ficdate')

        # Let ancesters handling most of the env setting
        super(Raw2ODB, self).prepare(rh, opts)
        self.env.default(
            TIME_INIT_YYYYMMDD = self.date.ymd,
            TIME_INIT_HHMMSS   = self.date.hm + '00',
        )
        if self.lamflag:
            self.env.update(
                BATOR_LAMFLAG  = 1,
                BATODB_LAMFLAG = 1,
            )

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""

        sh = self.system

        batnam = [ x.rh for x in self.context.sequence.effective_inputs(role = 'NamelistBatodb') ]

        self.obsmapout = list()

        for odbset, thispack in self.obspack.items():
            odbname = self.virtualdb.upper() + '.' + odbset
            sh.title('ODB set ' + odbname)

            # Make a soft link when necessary
            linked = list()
            for obsname, obsinfo in thispack.obsfile.items():
                sh.subtitle(obsname)
                if sh.path.islink(obsname):
                    sh.remove(obsname)
                if obsname != obsinfo.rh.container.localpath():
                    sh.softlink(obsinfo.rh.container.localpath(), obsname)
                    linked.append(obsname)
                if thispack.standalone:
                    sh.softlink(obsinfo.rh.container.localpath(), thispack.standalone)

            # Fill the actual refdata according to information gathered in prepare stage
            if thispack.refdata:
                with io.open('refdata', 'w') as fd:
                    for r in thispack.refdata:
                        fd.write(unicode(r + "\n"))
                sh.subtitle('Local refdata')
                sh.cat('refdata', output=False)

            # Give a glance to the actual namelist
            if batnam:
                sh.subtitle('Namelist Raw2ODB')
                batnam[0].container.cat()

            # Standard execution
            self.env.ODB_SRCPATH_ECMA  = sh.path.abspath(odbname)
            self.env.ODB_DATAPATH_ECMA = sh.path.abspath(odbname)
            super(Raw2ODB, self).execute(rh, opts)

            # Save current stdout
            if sh.path.exists('stdeo.0'):
                sh.mv('stdeo.0', 'listing.' + odbset)

            # Some cleaning
            sh.header('Partial cleaning for ' + odbname)
            sh.remove('refdata')
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
        super(Raw2ODB, self).postfix(rh, opts)
        with io.open('batodb_map.out', 'w') as fd:
            for x in sorted(self.obsmapout):
                fd.write(unicode(ObsMapContent.formatted_data(x) + '\n'))


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
        obsall = [ x for x in self.input_obs() if x.resource.layout == 'ecma' ]

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

        mask = [ x.rh for x in self.context.sequence.effective_inputs(kind = 'atmsmask') ]
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
        super(OdbAverage, self).postfix(rh, opts)

        sh = self.system

        oldpwd = sh.getcwd()
        sh.cd(self.layout_new)
        for ccma in sh.glob('{0:s}.*'.format(self.layout_new)):
            slurp = sh.cat(ccma, outsplit=False).replace(self.layout_new, self.layout_in)
            with io.open(ccma.replace(self.layout_new, self.layout_in), 'w') as fd:
                fd.write(unicode(slurp))
            sh.rm(ccma)

        sh.cd(oldpwd)
        sh.mv(self.layout_new, self.layout_in + '.' + self.bingo.resource.part)
