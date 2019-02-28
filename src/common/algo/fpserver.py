#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

"""
AlgoComponents for the next generation of Fullpos runs (based on the 903 configuration).
"""

import six

import collections
import functools
import io
import math
import re
from six.moves import filterfalse
import time

from bronx.stdtypes.date import Time
from bronx.fancies import loggers

import footprints

from vortex.algo.components import AlgoComponentError
import vortex.layout.monitor as _lmonitor

from .ifsroot import IFSParallel

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


fullpos_server_flypoll_pickle = '.fullpos_server_flypoll'


class FullPosServerFlyPollPersistantState(object):
    """Persistent storage object for Fullpos's polling method."""

    def __init__(self):
        self.cursor = Time(-9999)
        self.found = list()


def fullpos_server_flypoll(sh, outputprefix, termfile, directories=('.'), **kwargs):  # @UnusedVariable
    """Check sub-**directories** to determine wether new output files are available or not."""
    new = list()
    for directory in directories:
        with sh.cdcontext(directory, create=True):
            if sh.path.exists(fullpos_server_flypoll_pickle):
                fpoll_st = sh.pickle_load(fullpos_server_flypoll_pickle)
            else:
                fpoll_st = FullPosServerFlyPollPersistantState()
            try:
                if sh.path.exists(termfile):
                    with io.open(termfile, 'r') as wfh:
                        rawcursor = wfh.readline().rstrip('\n')
                    try:
                        cursor = Time(rawcursor)
                    except TypeError:
                        logger.warning('Unable to convert "%s" to a Time object', rawcursor)
                        return new
                    pre = re.compile(r'^{:s}\w*\+(\d+(?::\d\d)?)(?:\.\w+)?$'.format(outputprefix))
                    candidates = [pre.match(f) for f in sh.listdir()]
                    lnew = list()
                    for candidate in filterfalse(lambda c: c is None, candidates):
                        ctime = Time(candidate.group(1))
                        if ctime > fpoll_st.cursor and ctime <= cursor:
                            lnew.append(candidate.group(0))
                    fpoll_st.cursor = cursor
                    fpoll_st.found.extend(lnew)
                    new.extend([sh.path.normpath(sh.path.join(directory, anew))
                                for anew in lnew])
            finally:
                sh.pickle_dump(fpoll_st, fullpos_server_flypoll_pickle)
    return new


class FullPosServer(IFSParallel):
    """Fullpos Server for geometry transforms & post-processing in IFS-like Models.

    :note: To use this algocomponent, the c903's server needs to be activated
           in the namelist (NFPSERVER != 0).

    :note: With the current IFS/Arpege code an ``ECHFP`` have to be incremented
           by the server, in each of the output directories, in order for the
           output's polling to work properly.

    :note: Climatology files are not managed (only few sanity checks are
           performed). The user needs to name the input climatology file
           consistently with the c903' namelist.

    Interesting features:

        * Input files can be expected (for on the fly processing)
        * Input files are dealt with in arbitrary order depending on their
          availability (useful for ensemble processing).
        * Output files can be promised

    """

    _INITIALCONDITION_ROLE = re.compile(r'InitialCondition((?:\w+)?)')
    _INPUTDATA_ROLE_STR = 'ModelState'
    _INPUTDATA_ROLE = re.compile(r'ModelState((?:\w+)?)')

    _MODELSIDE_INPUTPREFIX0 = 'ICM'
    _MODELSIDE_INPUTPREFIX1 = 'SH'
    _MODELSIDE_OUTPUTPREFIX = 'PF'
    _MODELSIDE_TERMFILE = './ECHFP'
    _MODELSIDE_OUT_SUFFIXLEN_MIN = 4
    _MODELSIDE_IND_SUFFIXLEN_MIN = 4
    _MODELSIDE_INE_SUFFIXLEN_MIN = dict(grib=6)

    _SERVERSYNC_RAISEONEXIT = False
    _SERVERSYNC_RUNONSTARTUP = False
    _SERVERSYNC_STOPONEXIT = False

    _footprint = dict(
        attr = dict(
            kind = dict(
                values   = ['fpserver', ],
            ),
            outputid = dict(
                info     = "The identifier for the encoding of post-processed fields.",
                optional = True,
            ),
            outdirectories = dict(
                info     = "The list of possible output directories.",
                type     = footprints.stdtypes.FPList,
                default  = footprints.stdtypes.FPList(['.', ]),
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
            maxpollingthreads = dict(
                type     = int,
                optional = True,
                default  = 8,
            ),
            flypoll = dict(
                default  = 'internal',
            ),
        )
    )

    @property
    def realkind(self):
        return 'fullpos'

    def __init__(self, *args, **kw):
        super(FullPosServer, self).__init__(*args, **kw)
        self._flyput_mapping_d = dict()

    def flyput_outputmapping(self, item):
        """Map an output file to its final name."""
        sh = self.system
        for out_re, data in self._flyput_mapping_d.items():
            m_re = out_re.match(sh.path.basename(item))
            if m_re:
                return sh.path.join(sh.path.dirname(item),
                                    data[0].format(m_re.group('fpdom')))

    def _setmacro(self, rh, macro, value):
        """Set a namelist macro and log it!"""
        rh.contents.setmacro(macro, value)
        logger.info('%s: Setting up the %s macro to %s',
                    str(rh.container.iotarget()), macro, value)

    def _actual_suffixlen(self, tododata, minlen):
        """Find out the required suffixlen given the **todorh** list of  Rhs to porcess."""
        return max(minlen,
                   int(math.floor(math.log10(len(tododata)))))

    def _inputs_discover(self):
        """Retrieve the lists in input sections/ResourceHandlers."""
        # Initial conditions
        inisec = self.context.sequence.effective_inputs(role = self._INITIALCONDITION_ROLE)
        inidata = dict()
        if inisec:
            for s in inisec:
                iprefix = ((self._INITIALCONDITION_ROLE.match(s.role) or
                            self._INITIALCONDITION_ROLE.match(s.atlernate)).group(1) or
                           self._MODELSIDE_INPUTPREFIX1)
                fprefix = self._MODELSIDE_INPUTPREFIX0 + iprefix
                if fprefix in inidata:
                    raise AlgoComponentError('Only one Initial Condition is allowed.')
                else:
                    inidata[fprefix] = s

        # Model states
        todosec0 = self.context.sequence.effective_inputs(role = self._INPUTDATA_ROLE)
        todosec1 = collections.defaultdict(list)
        tododata = list()
        outprefix = None
        informat = 'fa'
        anyexpected = any([isec.rh.is_expected() for isec in todosec0])
        if todosec0:
            for iseq, s in enumerate(todosec0):
                rprefix = ((self._INPUTDATA_ROLE.match(s.role) or
                            self._INPUTDATA_ROLE.match(s.atlernate)).group(1) or
                           self._MODELSIDE_INPUTPREFIX1)
                todosec1[rprefix].append(s)
                if iseq == 0:
                    outprefix = rprefix
                    informat = s.rh.container.actualfmt
            iprefixes = sorted(todosec1.keys())
            if len(iprefixes) == 1:
                tododata = list()
                for s in sorted(todosec0,
                                key=lambda isec: (isec.rh.resource.term
                                                  if hasattr(isec.rh.resource, 'term')
                                                  else None)):
                    tododata.append({self._MODELSIDE_INPUTPREFIX0 + iprefixes[0]: s})
            else:
                if len(set([len(secs) for secs in todosec1.values()])) > 1:
                    raise AlgoComponentError('Inconsistent number of input data.')
                for sections in zip(* [iter(todosec1[i]) for i in iprefixes]):
                    tododata.append({self._MODELSIDE_INPUTPREFIX0 + k: v
                                     for k, v in zip(iprefixes, sections)})

        # Selection namelists
        namxxrh = collections.defaultdict(dict)
        for isec in self.context.sequence.effective_inputs(role = 'FullPosSelection',
                                                           kind = 'namselect'):
            lpath = isec.rh.container.localpath()
            dpath = self.system.path.dirname(lpath)
            namxxrh[dpath][isec.rh.resource.term] = isec.rh

        inputsminlen = self._MODELSIDE_INE_SUFFIXLEN_MIN.get(informat,
                                                             self._MODELSIDE_IND_SUFFIXLEN_MIN)

        return inidata, tododata, namxxrh, anyexpected, outprefix, inputsminlen

    def _link_input(self, iprefix, irh, i, inputs_mapping, outputs_mapping,
                    i_fmt, o_raw_re_fmt, o_suffix, outprefix):
        """Link an input file and update the mappings dictionaries."""
        sourcepath = irh.container.localpath()
        inputs_mapping[sourcepath] = i_fmt.format(iprefix, i)
        self.system.cp(sourcepath, inputs_mapping[sourcepath], intent='in', fmt=irh.container.actualfmt)
        if iprefix == self._MODELSIDE_INPUTPREFIX0 + outprefix:
            outputs_mapping[re.compile(o_raw_re_fmt.format(i))] = (self.system.path.basename(sourcepath) +
                                                                   o_suffix,
                                                                   irh.container.actualfmt)
            logger.info('%s copied as %s -> Output %s mapped as %s.',
                        sourcepath, inputs_mapping[sourcepath],
                        o_raw_re_fmt.format(i), sourcepath + o_suffix)
        else:
            logger.info('%s copied as %s.',
                        sourcepath, inputs_mapping[sourcepath])

    def _link_xxt(self, todorh, i, xxtmapping):
        """If necessary, link in the appropriate xxtNNNNNNMM file."""
        for sdir, tdict in xxtmapping.items():
            xxtsource = tdict[todorh.resource.term].container.localpath()
            # The file is expected to follow the xxtDDDDHHMM syntax where DDDD
            # is the number of days
            days_hours = (i // 24) * 100 + i % 24
            xxttarget = 'xxt{:06d}00'.format(days_hours)
            xxttarget = self.system.path.join(sdir, xxttarget)
            self.system.symlink(xxtsource, xxttarget)
            logger.info('XXT %s linked in as %s.', xxtsource, xxttarget)

    def _init_poll_and_move(self, outputs_mapping):
        """Deal with the PF*INIT file."""
        sh = self.system
        candidates = self.system.glob('{:s}{:s}*INIT'.format(self._MODELSIDE_OUTPUTPREFIX, self.xpname))
        outputnames = list()
        for thisdata in candidates:
            for out_re, data in outputs_mapping.items():
                m_re = out_re.match(thisdata)
                if m_re:
                    mappeddata = (sh.path.join(sh.path.dirname(thisdata),
                                               data[0].format(m_re.group('fpdom'))),
                                  data[1])
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
        sh = self.system
        data = self.manual_flypolling()
        outputnames = list()
        for thisdata in data:
            mappeddata = None
            for out_re, data in outputs_mapping.items():
                m_re = out_re.match(sh.path.basename(thisdata))
                if m_re:
                    mappeddata = (sh.path.join(sh.path.dirname(thisdata),
                                               data[0].format(m_re.group('fpdom'))),
                                  data[1])
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
                candidates = [x for x in self.promises
                              if x.rh.container.abspath == self.system.path.abspath(afile)]
                if candidates:
                    logger.info('The output data is promised <%s>', afile)
                    bingo = candidates.pop()
                    bingo.put(incache=True)

    def prepare(self, rh, opts):
        """Various sanity checks + namelist tweaking."""
        super(FullPosServer, self).prepare(rh, opts)

        inidata, tododata, namxx, anyexpected, _, inputsminlen = self._inputs_discover()

        # Sanity check over climfiles and geometries
        input_geo = set([sec.rh.resource.geometry
                         for sdict in tododata for sec in sdict.values()])
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
        if inidata and any([sec.rh.resource.geometry != input_geo for sec in inidata.values()]):
            raise AlgoComponentError('The Initial Condition geometry differs from other input data.')

        # Sanity check on target climatology files
        target_climgeos = set([x.rh.resource.geometry
                               for x in self.context.sequence.effective_inputs(role='TargetClim')])
        if len(target_climgeos) == 0:
            raise AlgoComponentError('No target clim are provided.')

        # Sanity check on selection namelists
        if namxx:
            for tdict in namxx.values():
                if (set([sec.rh.resource.term for sdict in tododata for sec in sdict.values()]) !=
                        set(tdict.keys())):
                    raise AlgoComponentError("The list of terms between input data and selection namelists differs")
        else:
            logger.info("No selection namelists detected. That's fine")

        # Link in the intial condition file (if necessary)
        for iprefix, isec in inidata.items():
            i_init = '{:s}{:s}INIT'.format(iprefix, self.xpname)
            if isec.rh.container.basename != i_init:
                self.system.cp(isec.rh.container.localpath(), i_init,
                               intent='in', fmt=isec.rh.container.actualfmt)
                logger.info('Initial condition file %s copied as %s.',
                            isec.rh.container.localpath(), i_init)

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
            # With cy43: &NAMCT0 CFPNCF=__IOPOLL_WHITNESSFILE__, /
            self._setmacro(namrh, 'IOPOLL_WHITNESSFILE', self._MODELSIDE_TERMFILE)
            # With cy43: No matching namelist key
            # a/c cy44: &NAMFPIOS NFPDIGITS=__SUFFIXLEN__, /
            self._setmacro(namrh, 'SUFFIXLEN',
                           self._actual_suffixlen(tododata, self._MODELSIDE_OUT_SUFFIXLEN_MIN))
            # No matching namelist yet
            self._setmacro(namrh, 'INPUT_SUFFIXLEN',
                           self._actual_suffixlen(tododata, inputsminlen))
            # With cy43: &NAMCT0 NFRPOS=__INPUTDATALEN__, /
            self._setmacro(namrh, 'INPUTDATALEN', len(tododata))
            namrh.save()

    def execute(self, rh, opts):
        """Server still or Normal execution depending on the input sequence."""
        sh = self.system
        inidata, tododata, namxx, anyexpected, outprefix, inputsminlen = self._inputs_discover()

        # Input/Output formats
        i_fmt = ('{:s}' + '{:s}+'.format(self.xpname) +
                 '{:0' + str(self._actual_suffixlen(tododata, inputsminlen)) +
                 'd}')
        o_raw_re_fmt = ('^{:s}{:s}'.format(self._MODELSIDE_OUTPUTPREFIX, self.xpname) +
                        r'(?P<fpdom>\w+)\+' +
                        '{:0' + str(self._actual_suffixlen(tododata, self._MODELSIDE_OUT_SUFFIXLEN_MIN)) +
                        'd}$')
        o_init_re = ('^{:s}{:s}'.format(self._MODELSIDE_OUTPUTPREFIX, self.xpname) +
                     r'(?P<fpdom>\w+)INIT$')
        o_suffix = '.{:s}.out'

        # Input and Output mapping
        inputs_mapping = dict()
        outputs_mapping = dict()
        # Initial condition file ?
        if inidata:
            for iprefix, isec in inidata.items():
                # The initial condition resource may be expected
                self.grab(isec)
                # Fix potential links and output mappings
                sourcepath = isec.rh.container.basename
                if iprefix == self._MODELSIDE_INPUTPREFIX0 + outprefix:
                    outputs_mapping[re.compile(o_init_re)] = (sourcepath + o_suffix,
                                                              isec.rh.container.actualfmt)
                i_init = '{:s}{:s}INIT'.format(iprefix, self.xpname)
                if isec.rh.container.basename != i_init:
                    self.system.cp(sourcepath, i_init,
                                   intent='in', fmt=isec.rh.container.actualfmt)
                    logger.info('Initial condition file %s copied as %s.',
                                isec.rh.container.localpath(), i_init)
        else:
            if tododata:
                # Just in case the INIT file is transformed
                outputs_mapping[re.compile(o_init_re)] = (self._MODELSIDE_INPUTPREFIX0 +
                                                          outprefix + self.xpname + 'INIT' + o_suffix,
                                                          tododata[0][self._MODELSIDE_INPUTPREFIX0 +
                                                                      outprefix].rh.container.actualfmt)
        # Initialise the flying stuff
        self.flyput = False  # Do not use flyput every time...
        self.io_poll_args = tuple([self._MODELSIDE_OUTPUTPREFIX, ])
        self.io_poll_kwargs = dict(directories=tuple(set(self.outdirectories)))
        for directory in set(self.outdirectories):
            sh.mkdir(directory)  # Create possible output directories
        if self.flypoll == 'internal':
            self.io_poll_method = functools.partial(fullpos_server_flypoll, sh)
            self.io_poll_kwargs['termfile'] = sh.path.basename(self._MODELSIDE_TERMFILE)
        self._flyput_mapping_d = outputs_mapping

        if anyexpected:
            # Some server sync here...
            self.server_run = True
            self.system.subtitle('Starting computation with server_run=T')

            # IO poll settings
            self.io_poll_kwargs['nthreads'] = self.maxpollingthreads

            # Is there already an Initial Condition file ?
            # If so, start the binary...
            if inidata:
                super(FullPosServer, self).execute(rh, opts)
                # Did the server stopped ?
                if not self.server_alive():
                    logger.error("Server initialisation failed.")
                    return
                self._deal_with_promises(outputs_mapping, self._init_poll_and_move)

            # Setup the InputMonitor
            metagang = _lmonitor.MetaGang()
            for istuff in tododata:
                iinputs = {_lmonitor.InputMonitorEntry(s) for s in istuff.values()}
                bgang = _lmonitor.BasicGang()
                bgang.info = istuff
                bgang.add_member(* iinputs)
                metagang.add_member(bgang)
            bm = _lmonitor.ManualInputMonitor(self.context,
                                              [ime
                                               for g in metagang.memberslist
                                               for ime in g.memberslist],
                                              caching_freq=self.refreshtime,)

            # Start the InputMonitor
            tmout = False
            current_i = 0
            server_stopped = False
            with bm:
                while not bm.all_done or len(bm.available) > 0:
                    while metagang.has_collectable():
                        thegang = metagang.pop_collectable()
                        istuff = thegang.info
                        sh.highlight("The Fullpos Server is triggered (step={:d})..."
                                     .format(current_i))

                        # Link for the initfile (if needed)
                        if current_i == 0 and not inidata:
                            for iprefix, isec in istuff.items():
                                i_init = '{:s}{:s}INIT'.format(iprefix, self.xpname)
                                if not sh.path.exists(i_init):
                                    sh.cp(isec.rh.container.localpath(), i_init,
                                          intent='in', fmt=isec.rh.container.actualfmt)
                                    logger.info('%s copied as %s. For initialisation purposes only.',
                                                isec.rh.container.localpath(), i_init)
                            super(FullPosServer, self).execute(rh, opts)
                            # Did the server stopped ?
                            if not self.server_alive():
                                logger.error("Server initialisation failed.")
                                return
                            self._deal_with_promises(outputs_mapping, self._init_poll_and_move)

                        # Link input files and XXT files
                        for iprefix, isec in istuff.items():
                            self._link_input(iprefix, isec.rh, current_i,
                                             inputs_mapping, outputs_mapping,
                                             i_fmt, o_raw_re_fmt, o_suffix, outprefix)
                        self._link_xxt(istuff[self._MODELSIDE_INPUTPREFIX0 + outprefix].rh,
                                       current_i, namxx)

                        # Let's go...
                        super(FullPosServer, self).execute(rh, opts)
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

            # Link for the inifile (if needed)
            if not inidata:
                for iprefix, isec in tododata[0].items():
                    i_init = '{:s}{:s}INIT'.format(iprefix, self.xpname)
                    if not sh.path.exists(i_init):
                        sh.cp(isec.rh.container.localpath(), i_init,
                              intent='in', fmt=isec.rh.container.actualfmt)
                        logger.info('%s copied as %s. For initialisation purposes only.',
                                    isec.rh.container.localpath(), i_init)

            # Create all links well in advance
            for i, iinputs in enumerate(tododata):
                for iprefix, isec in iinputs.items():
                    self._link_input(iprefix, isec.rh, i, inputs_mapping, outputs_mapping,
                                     i_fmt, o_raw_re_fmt, o_suffix, outprefix)
                self._link_xxt(iinputs[self._MODELSIDE_INPUTPREFIX0 + outprefix].rh,
                               i, namxx)

            # On the fly ?
            if self.promises:
                self.flyput = True
                self.flymapping = True

            # Let's roll !
            super(FullPosServer, self).execute(rh, opts)

        # Map all outputs to destination (using io_poll)
        self._init_poll_and_move(outputs_mapping)
        self._poll_and_move(outputs_mapping)
