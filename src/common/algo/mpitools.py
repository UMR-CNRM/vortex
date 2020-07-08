#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
General interest and NWP specific MPI launchers.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import re
import six

from bronx.fancies import loggers
import footprints
import io

from vortex.algo import mpitools
from vortex.syntax.stdattrs import DelayedEnvValue
from vortex.util import config

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class MpiAuto(mpitools.ConfigurableMpiTool):
    """MpiTools that uses mpiauto as a proxy to several MPI implementations"""

    _footprint = dict(
        attr = dict(
            mpiname = dict(
                values = ['mpiauto', ],
            ),
            mpiopts = dict(
                default = None
            ),
            optprefix = dict(
                default = '--'
            ),
            optmap = dict(
                default  = footprints.FPDict(nn='nn', nnp='nnp', openmp='openmp',
                                             np='np', prefixcommand='prefix-command',
                                             allowodddist='mpi-allow-odd-dist')
            ),
            timeoutrestart = dict(
                info            = 'The number of attempts made by mpiauto',
                optional        = True,
                default         = DelayedEnvValue('MPI_INIT_TIMEOUT_RESTART', 2),
                doc_visibility  = footprints.doc.visibility.ADVANCED,
                doc_zorder      = -90,
            ),
            sublauncher = dict(
                info            = 'How to actualy launch the MPI program',
                values          = ['srun', 'libspecific'],
                optional        = True,
                doc_visibility  = footprints.doc.visibility.ADVANCED,
                doc_zorder      = -90,
            ),
            mpiwrapstd = dict(
                values          = [False, ],
            ),
            bindingmethod = dict(
                info            = 'How to bind the MPI processes',
                values          = ['arch', 'launcherspecific', 'vortex'],
                optional        = True,
                doc_visibility  = footprints.doc.visibility.ADVANCED,
                doc_zorder      = -90,
            ),
        )
    )

    _envelope_wrapper_tpl = '@mpitools/envelope_wrapper_mpiauto.tpl'
    _envelope_rank_var = 'MPIAUTORANK'
    _needs_mpilib_specific_mpienv = False

    def _reshaped_mpiopts(self):
        """Raw list of mpi tool command line options."""
        options = super(MpiAuto, self)._reshaped_mpiopts()
        options['init-timeout-restart'] = self.timeoutrestart
        if self.sublauncher == 'srun':
            options['use-slurm-mpi'] = None
        elif self.sublauncher == 'libspecific':
            options['no-use-slurm-mpi'] = None
            options['no-fix-slurm-env'] = None
        if self.bindingmethod:
            for k in ['{:s}use-{:s}-bind'.format(p, t) for p in ('', 'no-')
                      for t in ('arch', 'slurm', 'intelmpi', 'openmpi')]:
                options.pop(k, None)
            if self.bindingmethod == 'arch':
                options['use-arch-bind'] = None
            elif self.bindingmethod == 'launcherspecific' and self.sublauncher == 'srun':
                options['no-use-arch-bind'] = None
                options['use-slurm-bind'] = None
            elif self.bindingmethod == 'launcherspecific':
                options['no-use-arch-bind'] = None
                for k in ['use-{:s}-bind'.format(t)
                          for t in ('slurm', 'intelmpi', 'openmpi')]:
                    options[k] = None
            elif self.bindingmethod == 'vortex':
                options['no-use-arch-bind'] = None
        return options

    def _envelope_fix_envelope_bit(self, e_bit, e_desc):
        """Set the envelope fake binary options."""
        e_bit.options = {k: v for k, v in e_desc.items()
                         if k not in ('openmp')}
        e_bit.options['prefixcommand'] = self._envelope_wrapper_name
        if self.binaries:
            e_bit.master = self.binaries[0].master

    def _set_binaries_hack(self, binaries):
        """Set the list of :class:`MpiBinaryDescription` objects associated with this instance."""
        if len(binaries) > 1 and self.bindingmethod not in (None, 'arch', 'vortex'):
            logger.info("The '{:s}' binding method is not working properly with multiple binaries."
                        .format(self.bindingmethod))
            logger.warning("Resetting the binding method to 'vortex'.")
            self.bindingmethod = 'vortex'

    def _set_binaries_envelope_hack(self, binaries):
        """Tweak the envelope after binaries were setup."""
        super(MpiAuto, self)._set_binaries_envelope_hack(binaries)
        for e_bit in self.envelope:
            e_bit.master = binaries[0].master

    def _set_envelope(self, value):
        """Set the envelope description."""
        super(MpiAuto, self)._set_envelope(value)
        if len(self._envelope) > 1 and self.bindingmethod not in (None, 'arch', 'vortex'):
            logger.info("The '{:s}' binding method is not working properly with complex envelopes."
                        .format(self.bindingmethod))
            logger.warning("Resetting the binding method to 'vortex'.")
            self.bindingmethod = 'vortex'

    envelope = property(mpitools.MpiTool._get_envelope, _set_envelope)

    def _hook_binary_mpiopts(self, options):
        tuned = options.copy()
        # Regular MPI tasks count (the usual...)
        if 'nnp' in options and 'nn' in options:
            if options['nn'] * options['nnp'] == options['np']:
                # Remove harmlful options
                del tuned['np']
                tuned.pop('allowodddist', None)
                # that's the strange MPI distribution...
            else:
                tuned['allowodddist'] = None  # With this, let mpiauto determine its own partitioning
        else:
            msg = ("The provided mpiopts are insufficient to build the command line: {!s}"
                   .format(options))
            raise mpitools.MpiException(msg)
        return tuned

    def _envelope_mkwrapper_todostack(self):
        ranksidx = 0
        todostack, ranks_bsize = super(MpiAuto, self)._envelope_mkwrapper_todostack()
        for bin_obj in self.binaries:
            if bin_obj.options:
                for mpirank in range(ranksidx, ranksidx + bin_obj.nprocs):
                    prefix_c = bin_obj.options.get('prefixcommand', None)
                    if prefix_c:
                        todostack[mpirank] = (prefix_c,
                                              [todostack[mpirank][0], ] + todostack[mpirank][1],
                                              todostack[mpirank][2])
                ranksidx += bin_obj.nprocs
        return todostack, ranks_bsize

    def _envelope_mkcmdline_extra(self, cmdl):
        """If possible, add an openmp option when the arch binding method is used."""

        if self.bindingmethod != 'vortex':
            openmps = set([b.options.get('openmp', None) for b in self.binaries])
            if len(openmps) > 1:
                if self.bindingmethod is not None:
                    logger.warning("Non-uniform OpenMP threads number... Not specifying anything.")
            else:
                openmp = openmps.pop() or 1
                cmdl.append(self.optprefix + self.optmap['openmp'])
                cmdl.append(six.text_type(openmp))

    def setup_environment(self, opts, conflabel):
        """Last minute fixups."""
        super(MpiAuto, self).setup_environment(opts, conflabel)
        if self.bindingmethod in ('arch', 'vortex'):
            # Make sure srun does nothing !
            self._logged_env_set('SLURM_CPU_BIND', 'none')

    def setup(self, opts=None, conflabel=None):
        """Ensure that the prefixcommand has the execution rights."""
        for bin_obj in self.binaries:
            prefix_c = bin_obj.options.get('prefixcommand', None)
            if prefix_c is not None:
                if self.system.path.exists(prefix_c):
                    self.system.xperm(prefix_c, force=True)
                else:
                    raise IOError('The prefixcommand do not exists.')
        super(MpiAuto, self).setup(opts, conflabel)


class MpiAutoDDT(MpiAuto):

    _footprint = dict(
        attr = dict(
            mpiname = dict(
                values = ['mpiauto-ddt', ],
            ),
        )
    )

    _conf_suffix = '-ddt'
    _ddt_session_file_name = 'armforge-vortex-session-file.ddt'

    def _dump_ddt_session(self):
        bin_directory = self.system.path.dirname(self.binaries[0].master)
        tpl = config.load_template(self.ticket, '@armforge-session-conf.tpl', encoding='utf-8')
        sconf = tpl.substitute(sourcedirs='\n'.join(['        <directory>{:s}</directory>'.format(d)
                                                     for d in self.sources]))
        sfile = self.system.path.join(bin_directory, 'armforge-vortex-session-file.ddt')
        with io.open(sfile, 'w') as fhs:
            fhs.write(sconf)
        return sfile

    def _reshaped_mpiopts(self):
        options = super(MpiAutoDDT, self)._reshaped_mpiopts()
        if 'prefix-mpirun' in options:
            raise mpitools.MpiException('It is not allowed to start DDT with another ' +
                                        'prefix_mpirun command defined: "{:s}"'
                                        .format(options))
        ddtpath = self.env.get('VORTEX_ARM_DDT_PATH', None)
        if ddtpath is None:
            forgepath = self.env.get('VORTEX_ARM_FORGE_DIR', None)
            if forgepath is None and self.target.config.has_option('armtools', 'forgedir'):
                forgepath = self.target.config.get('armtools', 'forgedir')
            else:
                raise mpitools.MpiException('DDT requested but the DDT path is not configured.')
            ddtpath = self.system.path.join(forgepath, 'bin', 'ddt')
        if self.sources:
            options['prefix-mpirun'] = '{:s} --session={:s} --connect'.format(ddtpath,
                                                                              self._dump_ddt_session())
        else:
            options['prefix-mpirun'] = '{:s} --connect'.format(ddtpath)
        return options


def arpifs_commons_binarydeco(cls):
    """Handle usual IFS/Arpege namelist tweaking.

    Note: This is a class decorator for class somehow based on MpiBinaryDescription
    """
    orig_setup_namelist_delta = getattr(cls, 'setup_namelist_delta')

    def setup_namelist_delta(self, namcontents, namlocal):
        namw = orig_setup_namelist_delta(self, namcontents, namlocal)
        if 'NBPROC' in namcontents.macros() or 'NPROC' in namcontents.macros():
            namcontents.setmacro('NCPROC', int(self.env.VORTEX_NPRGPNS or self.nprocs))
            namcontents.setmacro('NDPROC', int(self.env.VORTEX_NPRGPEW or 1))
            namw = True
        if 'NAMPAR1' in namcontents:
            np1 = namcontents['NAMPAR1']
            for nstr in [x for x in ('NSTRIN', 'NSTROUT') if x in np1]:
                if isinstance(np1[nstr], (int, float)) and np1[nstr] > self.nprocs:
                    logger.info('Setup %s=%s in NAMPAR1 %s', nstr, self.nprocs, namlocal)
                    np1[nstr] = self.nprocs
                    namw = True
        return namw

    if hasattr(orig_setup_namelist_delta, '__doc__'):
        setup_namelist_delta.__doc__ = orig_setup_namelist_delta.__doc__

    setattr(cls, 'setup_namelist_delta', setup_namelist_delta)
    return cls


# Some IFS/Arpege specific things :

def arpifs_obsort_nprocab_binarydeco(cls):
    """Handle usual IFS/Arpege environement tweaking for OBSORT (nproca & nprocb).

    Note: This is a class decorator for class somehow based on MpiBinaryDescription
    """
    orig_setup_env = getattr(cls, 'setup_environment')

    def setup_environment(self, opts):
        orig_setup_env(self, opts)
        self.env.NPROCA = int(self.env.NPROCA or
                              self.nprocs)
        self.env.NPROCB = int(self.env.NPROCB or
                              self.nprocs // self.env.NPROCA)
        logger.info("MPI Setup NPROCA=%d and NPROCB=%d", self.env.NPROCA, self.env.NPROCB)

    if hasattr(orig_setup_env, '__doc__'):
        setup_environment.__doc__ = orig_setup_env.__doc__

    setattr(cls, 'setup_environment', setup_environment)
    return cls


@arpifs_commons_binarydeco
class MpiNWP(mpitools.MpiBinaryBasic):
    """The kind of binaries used in IFS/Arpege."""

    _footprint = dict(
        attr = dict(
            kind = dict(values = ['basicnwp', ]),
        ),
    )


@arpifs_obsort_nprocab_binarydeco
@arpifs_commons_binarydeco
class MpiNWPObsort(mpitools.MpiBinaryBasic):
    """The kind of binaries used in IFS/Arpege when the ODB OBSSORT code needs to be run."""

    _footprint = dict(
        attr = dict(
            kind = dict(values = ['basicnwpobsort', ]),
        ),
    )


@arpifs_obsort_nprocab_binarydeco
class MpiObsort(mpitools.MpiBinaryBasic):
    """The kind of binaries used when the ODB OBSSORT code needs to be run."""

    _footprint = dict(
        attr = dict(
            kind = dict(values = ['basicobsort', ]),
        ),
    )


class MpiNWPIO(mpitools.MpiBinaryIOServer):
    """Standard IFS/Arpege NWP IO server."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['nwpioserv', ],
            ),
            pattern = dict(
                optional = True,
                default  = 'io_serv.*.d',
            ),
            polling = dict(
                type     = bool,
                optional = True,
                default  = False,
                access   = 'rwx',
            )
        )
    )

    def setup_namelist_delta(self, namcontents, namlocal):
        """Applying IO Serveur profile on local namelist ``namlocal`` with contents namcontents."""
        if 'NAMIO_SERV' in namcontents:
            namio = namcontents['NAMIO_SERV']
        else:
            namio = namcontents.newblock('NAMIO_SERV')

        namio.nproc_io = self.nprocs

        if 'VORTEX_IOSERVER_METHOD' in self.env:
            namio.nio_serv_method = self.env.VORTEX_IOSERVER_METHOD

        if 'VORTEX_IOSERVER_BUFMAX' in self.env:
            namio.nio_serv_buf_maxsize = self.env.VORTEX_IOSERVER_BUFMAX

        if 'VORTEX_IOSERVER_MLSERVER' in self.env:
            namio.nmsg_level_server = self.env.VORTEX_IOSERVER_MLSERVER

        if 'VORTEX_IOSERVER_MLCLIENT' in self.env:
            namio.nmsg_level_client = self.env.VORTEX_IOSERVER_MLCLIENT

        if 'VORTEX_IOSERVER_PROCESS' in self.env:
            namio.nprocess_level = self.env.VORTEX_IOSERVER_PROCESS

        if 'VORTEX_IOSERVER_PIOMODEL' in self.env:
            namio.pioprocr_MDL = self.env.VORTEX_IOSERVER_PIOMODEL

        self.system.subtitle('Parallel io namelist')
        print(namio.dumps())

        return True

    def iodirs(self):
        """Return an ordered list of directories matching the ``pattern`` attribute."""
        return sorted(self.system.glob(self.pattern))

    def clean(self, opts=None):
        """Post-execution cleaning for io server."""
        self.polling = True

        # Old fashion way to make clear that some polling is needed.
        self.system.touch('io_poll.todo')

        # Get a look inside io server output directories according to its own pattern
        ioserv_filelist = set()
        ioserv_prefixes = set()
        logfmt = '%24s: %32s %s'
        iofile_re = re.compile(r'((ICMSH|PF|GRIBPF).*\+\d+(?:\:\d+)?(?:\.sfx)?)(?:\..+)?$')
        for iodir in self.iodirs():
            self.system.subtitle('Parallel io directory {0:s}'.format(iodir))
            for iofile in self.system.listdir(iodir):
                zf = iofile_re.match(iofile)
                if zf:
                    logger.info(logfmt, iodir, iofile, ':-)')
                    ioserv_filelist.add(zf.group(1))
                    ioserv_prefixes.add(zf.group(2))
                else:
                    logger.info(logfmt, iodir, iofile, 'UFO')

        # Touch the output files
        for tgfile in ioserv_filelist:
            self.system.touch(tgfile)

        # Touch the io_poll.todo.PREFIX
        for prefix in ioserv_prefixes:
            self.system.touch('io_poll.todo.{:s}'.format(prefix))
