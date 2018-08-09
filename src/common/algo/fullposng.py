#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

"""
AlgoComponents for the next generation of Fullpos runs (based on the 903 configuration).
"""

import six

import math
import re
import time

import footprints

from vortex.algo.components import AlgoComponentError
from vortex.layout.monitor    import BasicInputMonitor

from .ifsroot import IFSParallel

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


class FullPosNg(IFSParallel):
    """Fullpos for geometry transforms & post-processing in IFS-like Models.

    :note: The **io_poll** method is used to retrieve output files. Consequently,
           the corresponding addon needs to be loaded and properly configured.
           with the current IFS/Arpege code an ``ECHFP`` have to be incremented
           by the server in order for **io_poll** to work properly.

    :note: Climatology files are not managed (only few sanity checks are
           performed). The user needs to name the input climatology file
           consistently with the c903' namelist.

    Interesting features:

        * Input files can be expected (for on the fly processing)
        * Input files are dealt with in arbitrary order depending on their
          availability (useful for ensemble processing).
        * Output files can be promised

    """

    _INITIALCONDITION_ROLE = 'InitialCondition'
    _INPUTDATA_ROLE = 'ModelState'

    _MODELSIDE_INPUTPREFIX = 'ICMSH'
    _MODELSIDE_OUTPUTPREFIX = 'PF'
    _MODELSIDE_SUFFIXLEN_MIN = 4

    _SERVERSYNC_RAISEONEXIT = False
    _SERVERSYNC_RUNONSTARTUP = False
    _SERVERSYNC_STOPONEXIT = False

    _footprint = dict(
        attr = dict(
            kind = dict(
                values   = ['fullposng', ],
            ),
            outputid = dict(
                info     = "The identifier for the encoding of post-processed fields.",
                optional = True,
            ),
            xpname = dict(
                default  = 'FPOS'
            ),
            conf = dict(
                default  = 903,
            ),
            timeout = dict(
                type = int,
                optional = True,
                default = 300,
            ),
            refreshtime = dict(
                info = "How frequently are the expected input files looked for ? (seconds)",
                type = int,
                optional = True,
                default = 20,
            ),
            server_run = dict(
                # This is a rw attribute: it will be managed internally
                values   = [True, False]
            ),
            serversync_method = dict(
                default  = 'simple_socket',
            ),
            serversync_medium = dict(
                default  = 'nextfile_wait',
            ),
        )
    )

    @property
    def realkind(self):
        return 'fullpos'

    def __init__(self, *args, **kw):
        super(FullPosNg, self).__init__(*args, **kw)
        self._flyput_mapping_d = dict()

    def flyput_outputmapping(self, item):
        """Map an output file to its final name."""
        for out_re, data in self._flyput_mapping_d.items():
            m_re = out_re.match(item)
            if m_re:
                return data[0].format(m_re.group('fpdom'))

    def _setmacro(self, rh, macro, value):
        """Set a namelist macro and log it!"""
        rh.contents.setmacro(macro, value)
        logger.info('%s: Setting up the %s macro to %s',
                    str(rh.container.iotarget()), macro, value)

    def _actual_suffixlen(self, todorh):
        """Find out the required suffixlen given the **todorh** list of  Rhs to porcess."""
        return max(self._MODELSIDE_SUFFIXLEN_MIN,
                   int(math.floor(math.log10(len(todorh)))))

    def _inputs_discover(self):
        """Retrieve the lists in input sections/ResourceHandlers."""
        # Initial conditions
        inisec = self.context.sequence.effective_inputs(role = self._INITIALCONDITION_ROLE)
        if len(inisec) == 1:
            inisec = inisec[0]
        elif len(inisec) == 0:
            inisec = None
        else:
            raise AlgoComponentError('Only one Initial Condition is allowed.')
        # Model states
        todorh = [x.rh for x in self.context.sequence.effective_inputs(role = self._INPUTDATA_ROLE)]
        todorh.sort(key=lambda irh: irh.resource.term)
        anyexpected = any([irh.is_expected() for irh in todorh])
        # Selection namelists
        namxxrh = [x.rh for x in self.context.sequence.effective_inputs(role = 'FullPosSelection',
                                                                        kind = 'namselect',)]
        return inisec, todorh, namxxrh, anyexpected

    def _link_input(self, irh, i, inputs_mapping, outputs_mapping,
                    i_fmt, o_raw_re_fmt, o_suffix):
        """Link an input file and update the mappings dictionaries."""
        sourcepath = irh.container.localpath()
        inputs_mapping[sourcepath] = i_fmt.format(i)
        self.system.cp(sourcepath, inputs_mapping[sourcepath], intent='in', fmt=irh.container.actualfmt)
        outputs_mapping[re.compile(o_raw_re_fmt.format(i))] = (sourcepath + o_suffix,
                                                               irh.container.actualfmt)
        logger.info('%s copied as %s -> Output %s mapped as %s.',
                    sourcepath, inputs_mapping[sourcepath],
                    o_raw_re_fmt.format(i), sourcepath + o_suffix)

    def _link_xxt(self, todorh, i, xxtmapping):
        """If necessary, link in the appropriate xxtNNNNNNMM file."""
        if xxtmapping:
            xxtsource = xxtmapping[todorh.resource.term].container.localpath()
            # The file is expected to follow the xxtDDDDHHMM syntax where DDDD
            # is the number of days
            days_hours = (i // 24) * 100 + i % 24
            xxttarget = 'xxt{:06d}00'.format(days_hours)
            self.system.symlink(xxtsource, xxttarget)
            logger.info('XXT %s linked in as %s.', xxtsource, xxttarget)

    def _init_poll_and_move(self, outputs_mapping):
        """Deal with the PF*INIT file."""
        candidates = self.system.glob('{:s}{:s}*INIT'.format(self._MODELSIDE_OUTPUTPREFIX, self.xpname))
        outputnames = list()
        for thisdata in candidates:
            for out_re, data in outputs_mapping.items():
                m_re = out_re.match(thisdata)
                if m_re:
                    mappeddata = (data[0].format(m_re.group('fpdom')), data[1])
                    break
            if mappeddata is None:
                raise AlgoComponentError('The mapping failed for {:s}.'.format(thisdata))
            # Already dealt with ?
            if not self.system.path.exists(mappeddata[0]):
                logger.info('Linking <%s> to <%s> (fmt=%s).', thisdata, mappeddata[0], mappeddata[1])
                outputnames.append(mappeddata[0])
                self.system.cp(thisdata, mappeddata[0], intent='in', fmt=mappeddata[1])
        return outputnames

    def _poll_and_move(self, outputs_mapping):
        """Call **io_poll** and rename available output files."""
        data = self.manual_flypolling()
        outputnames = list()
        for thisdata in data:
            mappeddata = None
            for out_re, data in outputs_mapping.items():
                m_re = out_re.match(thisdata)
                if m_re:
                    mappeddata = (data[0].format(m_re.group('fpdom')), data[1])
                    break
            if mappeddata is None:
                raise AlgoComponentError('The mapping failed for {:s}.'.format(thisdata))
            logger.info('Linking <%s> to <%s> (fmt=%s).', thisdata, mappeddata[0], mappeddata[1])
            outputnames.append(mappeddata[0])
            self.system.cp(thisdata, mappeddata[0], intent='in', fmt=mappeddata[1])
        return outputnames

    def _deal_with_promises(self, outputs_mapping, pollingcb):
        if self.promises:
            seen = pollingcb(outputs_mapping)
            for afile in seen:
                candidates = [x for x in self.promises if x.rh.container.basename == afile]
                if candidates:
                    logger.info('The output data is promised <%s>', afile)
                    bingo = candidates.pop()
                    bingo.put(incache=True)

    def prepare(self, rh, opts):
        """Various sanity checks + namelist tweaking."""
        super(FullPosNg, self).prepare(rh, opts)

        inisec, todorh, namxx, anyexpected = self._inputs_discover()

        # Sanity check over climfiles and geometries
        input_geo = set([rh.resource.geometry for rh in todorh])
        if len(input_geo) == 0:
            raise AlgoComponentError('No input data are provided, ...')
        elif len(input_geo) > 1:
            raise AlgoComponentError('Multiple geometries are not allowed for input data.')
        else:
            input_geo = input_geo.pop()

        input_climgeo = set([x.rh.resource.geometry
                             for x in self.context.sequence.effective_inputs(role='InputClim')])
        if len(input_climgeo) == 0:
            logger.info('No input clim provided. Going on without it...')
        elif len(input_climgeo) > 1:
            raise AlgoComponentError('Multiple geometries are not allowed for input climatology.')
        else:
            if input_climgeo.pop() != input_geo:
                raise AlgoComponentError('The input data and input climatology geometries does not match.')

        # Initial Condition geometry sanity check
        if inisec and inisec.rh.resource.geometry != input_geo:
            raise AlgoComponentError('The Initial Condition geometry differs from other input data.')

        # Sanity check on target climatology files
        target_climgeos = set([x.rh.resource.geometry
                               for x in self.context.sequence.effective_inputs(role='TargetClim')])
        if len(target_climgeos) == 0:
            raise AlgoComponentError('No target clim are provided.')
        if len(target_climgeos) > 1:
            lonlat_only = all([g.kind == 'lonlat' for g in target_climgeos])
            if not lonlat_only:
                raise AlgoComponentError('Multiple target geometries are not allowed except for lon/lat geometries.')

        # Sanity check on selection namelists
        if namxx:
            if set([irh.resource.term for irh in todorh]) != set([irh.resource.term for irh in namxx]):
                raise AlgoComponentError("The list of terms between input data and selection namelists differs")
        else:
            logger.info("No selection namelists detected. That's fine")

        # Link in the intial condition file (if necessary)
        i_init = '{:s}{:s}INIT'.format(self._MODELSIDE_INPUTPREFIX, self.xpname)
        if inisec and inisec.rh.container.basename != i_init:
            self.system.cp(inisec.rh.container.localpath(), i_init,
                           intent='in', fmt=inisec.rh.container.actualfmt)
            logger.info('Initial condition file %s copied as %s.',
                        inisec.rh.container.localpath(), i_init)

        # Prepare the namelist
        self.system.subtitle('Setting 903 namelist settings')
        namrhs = [x.rh for x in self.context.sequence.effective_inputs(role = 'Namelist',
                                                                       kind = 'namelist')]
        for namrh in namrhs:
            # With cy43: &NAMCT0 CSCRIPT_PPSERVER=__SERVERSYNC_SCRIPT__, /
            if anyexpected:
                self._setmacro(namrh, 'SERVERSYNC_SCRIPT',
                               self.system.path.join('.', self.serversync_medium))
            else:
                # Do not harass the filesystem...
                self._setmacro(namrh, 'SERVERSYNC_SCRIPT', ' ')
            # With cy43: No matching namelist key
            self._setmacro(namrh, 'INPUTPREFIX', self._MODELSIDE_INPUTPREFIX)
            # With cy43: &NAMFPC CFPDIR=__OUTPUTPREFIX__, /
            self._setmacro(namrh, 'OUTPUTPREFIX', self._MODELSIDE_OUTPUTPREFIX)
            # With cy43: No matching namelist key
            # a/c cy44: &NAMFPIOS NFPDIGITS=__SUFFIXLEN__, /
            self._setmacro(namrh, 'SUFFIXLEN', self._actual_suffixlen(todorh))
            # With cy43: &NAMCT0 NFRPOS=__INPUTDATALEN__, /
            self._setmacro(namrh, 'INPUTDATALEN', len(todorh))
            namrh.save()

    def execute(self, rh, opts):
        """Server still or Normal execution depending on the input sequence."""
        sh = self.system
        inisec, todorh, namxx, anyexpected = self._inputs_discover()

        # Create a terms map for namxx files
        namxx_map = {irh.resource.term: irh for irh in namxx}

        # Input/Output formats
        i_init = '{:s}{:s}INIT'.format(self._MODELSIDE_INPUTPREFIX, self.xpname)
        i_fmt = ('{:s}{:s}+'.format(self._MODELSIDE_INPUTPREFIX, self.xpname) +
                 '{:0' + str(self._actual_suffixlen(todorh)) + 'd}')
        o_raw_re_fmt = ('^{:s}{:s}'.format(self._MODELSIDE_OUTPUTPREFIX, self.xpname) +
                        r'(?P<fpdom>\w+)\+' +
                        '{:0' + str(self._actual_suffixlen(todorh)) + 'd}$')
        o_init_re = ('^{:s}{:s}'.format(self._MODELSIDE_OUTPUTPREFIX, self.xpname) +
                     r'(?P<fpdom>\w+)INIT$')
        o_suffix = '.{:s}.out'

        # Input and Output mapping
        inputs_mapping = dict()
        outputs_mapping = dict()
        # Initial condition file ?
        if inisec:
            sourcepath = inisec.rh.container.localpath()
            outputs_mapping[re.compile(o_init_re)] = (sourcepath + o_suffix,
                                                      inisec.rh.container.actualfmt)
            # The initial condition resource may be expected
            self.grab(inisec)
        else:
            # Just in case the INIT file is transformed
            outputs_mapping[re.compile(o_init_re)] = (i_init + o_suffix,
                                                      todorh[0].container.actualfmt)
        # Initialise the flying stuff
        self.flyput = False  # Do not use flyput every time...
        self.io_poll_args = tuple([self._MODELSIDE_OUTPUTPREFIX, ])
        self._flyput_mapping_d = outputs_mapping

        if anyexpected:
            # Some server sync here...
            self.server_run = True
            self.system.subtitle('Starting computation with server_run=T')

            # Is there already an Initial Condition file ?
            # If so, start the binary...
            if sh.path.exists(i_init):
                super(FullPosNg, self).execute(rh, opts)
                # Did the server stopped ?
                if not self.server_alive():
                    logger.error("Server initialisation failed.")
                    return
                self._deal_with_promises(outputs_mapping, self._init_poll_and_move)

            # Start the InputMonitor
            bm = BasicInputMonitor(self.context, caching_freq=self.refreshtime,
                                   role=self._INPUTDATA_ROLE)
            tmout = False
            current_i = 0
            server_stopped = False
            with bm:
                while not bm.all_done or len(bm.available) > 0:
                    while bm.available:
                        s = bm.pop_available().section
                        sourcepath = s.rh.container.localpath()
                        # Link for the initfile (if needed)
                        if current_i == 0 and not sh.path.exists(i_init):
                            sh.cp(sourcepath, i_init, intent='in', fmt=s.rh.container.actualfmt)
                            logger.info('%s copied as %s. For initialisation purposes only.',
                                        sourcepath, i_init,)
                            super(FullPosNg, self).execute(rh, opts)
                            # Did the server stopped ?
                            if not self.server_alive():
                                logger.error("Server initialisation failed.")
                                return
                            self._deal_with_promises(outputs_mapping, self._init_poll_and_move)
                        # Link input files and XXT files
                        self._link_input(s.rh, current_i, inputs_mapping, outputs_mapping,
                                         i_fmt, o_raw_re_fmt, o_suffix)
                        self._link_xxt(s.rh, current_i, namxx_map)
                        # Let's go...
                        super(FullPosNg, self).execute(rh, opts)
                        self._deal_with_promises(outputs_mapping, self._poll_and_move)
                        current_i += 1
                        # Did the server stopped ?
                        if not self.server_alive():
                            server_stopped = True
                            if not bm.all_done:
                                logger.error("The server stopped but everything wasn't processed...")
                            break

                    if server_stopped:
                        break

                    if not (bm.all_done or len(bm.available) > 0):
                        # Timeout ?
                        tmout = bm.is_timedout(self.timeout)
                        if tmout:
                            break
                        # Wait a little bit :-)
                        time.sleep(1)
                        bm.health_check(interval=30)

            for failed_file in [e.section.rh.container.localpath()
                                for e in six.itervalues(bm.failed)]:
                logger.error("We were unable to fetch the following file: %s", failed_file)
                if self.fatal:
                    self.delayed_exception_add(IOError("Unable to fetch {:s}".format(failed_file)),
                                               traceback=False)

            if tmout:
                raise IOError("The waiting loop timed out")

        else:
            # Direct Run !
            self.server_run = False
            self.system.subtitle('Starting computation with server_run=F')

            # Link for the initfile (if needed)
            if not sh.path.exists(i_init):
                sh.cp(todorh[0].container.localpath(), i_init,
                      intent='in', fmt=todorh[0].container.actualfmt)
                logger.info('%s copied as %s. For initialisation purposes only.',
                            todorh[0].container.localpath(), i_init,)
            # Create all links well in advance
            for i, irh in enumerate(todorh):
                self._link_input(irh, i, inputs_mapping, outputs_mapping, i_fmt, o_raw_re_fmt, o_suffix)
                self._link_xxt(irh, i, namxx_map)
            # On the fly ?
            if self.promises:
                self.flyput = True
                self.flymapping = True
            # Let's roll !
            super(FullPosNg, self).execute(rh, opts)

        # Map all outputs to destination (using io_poll)
        self._init_poll_and_move(outputs_mapping)
        self._poll_and_move(outputs_mapping)
