"""
This module contains example AlgoComponents that deal with a list of gridpoint
input files (like a real post-procesing task would do).
"""

import collections
import time

from bronx.fancies import loggers

from vortex.algo.components import AlgoComponent
from vortex.layout.monitor import BasicInputMonitor
from bronx.system.hash import HashAdapter

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


GribInfosKey = collections.namedtuple('_GribInfosKey', ('vapp', 'vconf', 'member', 'domain'))


class _AbstractGribInfos(AlgoComponent):
    """
    Elementary bits to build an AlgoComponent that will look for gridpoint
    inputs, classify the information, add some data (the md5 sum of the input
    file and write all that in a JSON output file.
    """

    _abstract = True
    _footprint = dict(
        attr = dict(
            engine = dict(
                default = 'algo',
                optional = True,
            ),
            jsonoutput = dict(
                optional = True,
                default = 'grib_infos.json'
            )
        )
    )

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self._gribstack = collections.defaultdict(dict)

    @property
    def realkind(self):
        return 'gribinfos'

    @staticmethod
    def _gribkey(rh):
        """The dictionaty key describing a grib file."""
        return GribInfosKey(rh.provider.vapp, rh.provider.vconf,
                            int(rh.provider.member), rh.resource.geometry.area)

    def _inputs_list(self):
        """Find all the Vortex' Sections describing the input data."""
        gpsec = self.context.sequence.effective_inputs(role=('Gridpoint',))
        gpsec.sort(key=lambda s: s.rh.resource.term)
        return gpsec

    def _dump_indiviudal_md5_file(self, rh, md5sum):
        """Dump a md5 file alongside the input data."""
        md5file = None
        if isinstance(rh.container.iotarget(), str):
            md5file = rh.container.localpath() + '.md5'
            with open(md5file, 'w', encoding='utf8') as fhm:
                fhm.write("{:s} {:s}".format(md5sum, rh.container.basename))
        return md5file

    def _compute_info_dict(self, rh):
        # Compute the md5 sum using the dedicated Vortex object
        hash_a = HashAdapter('md5')
        with rh.container.iod_context():
            md5sum = hash_a.file2hash(rh.container.iotarget())
            # If the input file is not virtual (i.e. in memory) dump a md5 file
            # alongside the input file (with the .md5 extension
            self._dump_indiviudal_md5_file(rh, md5sum)
            # Return the info dict (to be used in the JSON output file)
            return dict(
                filesize=rh.container.totalsize,
                md5sum=md5sum
            )

    def postfix(self, rh, opts):
        """Create a list of dictionaries and dump it in the JSON output file."""
        dumpable = list()
        for gribk, v in sorted(self._gribstack.items()):
            entry = gribk._asdict()
            entry['terms'] = v
            dumpable.append(entry)
        self.system.json_dump(dumpable, self.jsonoutput, indent=2)


class GribInfosSequential(_AbstractGribInfos):
    """Loop on available grib files to compute their size and MD5 sum.

    The result is written in a JSON file and individual md5 file are produced.

    In this version:

    * The input data may have been promised by another task (thus
      allowing on the fly processing);
    * The input data are processed sequentialy based on their "term" attribute.
    """

    _footprint = dict(
        attr = dict(
            kind = dict(
                values  = ['gribinfos'],
            ),
        )
    )

    def execute(self, rh, opts):
        """Loop on the various Grib files."""
        for sec in self._inputs_list():
            logger.info('Processing < %s >', sec.rh.container.localpath())
            # The input file might have been promised by another tasks: wait
            # for it to be available.
            self.grab(sec, comment='Wait for the Gridpoint input file')
            # Ok let's compute the necessary stuff
            rh = sec.rh
            self._gribstack[self._gribkey(rh)][rh.resource.term.fmthm] = \
                self._compute_info_dict(rh)


class GribInfosArbitraryOrder(_AbstractGribInfos):
    """Loop on available grib files to compute their size and MD5 sum.

    The result is written in a JSON file and individual md5 file are produced.

    In this version:

    * The input data may have been promised by another task (thus
      allowing on the fly processing);
    * The input data are processed as soon as they are available (e.g.
      if there are several members, data with term 06h of member 2 may be
      available before term 03h of member 1);
    * Additionaly, if they have been promised, the individual md5 files
      are stored in cache.
    """

    _footprint = dict(
        attr = dict(
            kind = dict(
                values  = ['gribinfos_ao'],
            ),
        )
    )

    def _dump_indiviudal_md5_file(self, rh, md5sum):
        """Dump a md5 file alongside the input data."""
        md5file = super()._dump_indiviudal_md5_file(rh, md5sum)
        if md5file is not None:
            # Check if the md5file is promised and acts accordingly
            expected = [x for x in self.promises
                        if x.rh.container.localpath() == md5file]
            for thispromise in expected:
                logger.info('A promised was found < %s >',
                            thispromise.rh.container.localpath())
                thispromise.put(incache=True)

    def execute(self, rh, opts):
        """Loop on the various Grib files."""
        # Monitor for the input files
        bm = BasicInputMonitor(self.context,
                               caching_freq=5,  # In a background task, refresh
                                                # the input file list every 5s
                               role='Gridpoint')
        with bm:
            while not bm.all_done or len(bm.available) > 0:
                # Deal with available sections
                while bm.available:
                    rh = bm.pop_available().section.rh
                    logger.info('Processing < %s >', rh.container.localpath())
                    infos = self._compute_info_dict(rh)
                    self._gribstack[self._gribkey(rh)][rh.resource.term.fmthm] = infos
                # Various sanity checks
                if not (bm.all_done or len(bm.available) > 0):
                    # Timeout ? (wait at most self.timeout seconds)
                    tmout = bm.is_timedout(self.timeout)
                    if tmout:
                        break
                    # Wait a little bit to limit the CPU usage :-)
                    time.sleep(1)
                    # Display a nice log message every 30s to explain the
                    # situation
                    bm.health_check(interval=30)
