"""
DAVAI sources build (branch export, compilation&link) AlgoComponents.
"""

import tempfile
from contextlib import contextmanager

import footprints
from footprints import FPDict
from bronx.fancies import loggers

from vortex.algo.components import (AlgoComponent, AlgoComponentDecoMixin,
                                    algo_component_deco_mixin_autodoc)

from .mixins import _CrashWitnessDecoMixin
from davai.util import set_env4git


#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)

binaries_syntax_in_workdir = 'justbuilt.{}.x'


@algo_component_deco_mixin_autodoc
class GmkpackDecoMixin(AlgoComponentDecoMixin):
    """Common attributes to gmkpack-related algos."""

    _MIXIN_EXTRA_FOOTPRINTS = (footprints.Footprint(
        info="Abstract mbdetect footprint",
        attr=dict(
            homepack=dict(
                info="Home directory for pack.",
                optional=True,
                default=None
            ),
            cleanpack=dict(
                info="Whether to cleanpack a pack before modifying it.",
                type=bool,
                optional=True,
                default=True
            )
        )
    ),)

    def _set_gmkpack(self, rh, opts):  # @UnusedVariable
        # util
        gmk_installdir = self.env.get('GMKROOT', self.target.config.get('gmkpack', 'gmkpack_installdir'))
        self.env.setbinpath(self.system.path.join(gmk_installdir, 'util'), 0)
        self.env['GMKROOT'] = gmk_installdir
        # tmpdir
        tmpdir = self.target.config.get('gmkpack', 'tmpdir')
        prefix = '.'.join([self.system.glove.user, 'gmktmp', ''])
        self.env['GMKTMP'] = tempfile.mkdtemp(prefix=prefix, dir=tmpdir)
        # homebin
        if not self.system.path.exists(self.env.get('HOMEBIN', '')):
            del self.env['HOMEBIN']  # may cause broken links

    def _gmkpack_finalise(self, opts):  # @UnusedVariable
        try:
            self.system.rmtree(self.env['GMKTMP'])
        except Exception:
            pass  # in case the directory has already been removed by gmkpack

    _MIXIN_PREPARE_HOOKS = (_set_gmkpack, )
    _MIXIN_EXECUTE_FINALISE_HOOKS = (_gmkpack_finalise, )


@algo_component_deco_mixin_autodoc
class GitDecoMixin(AlgoComponentDecoMixin):
    """Common attributes to git-related algos."""

    _MIXIN_EXTRA_FOOTPRINTS = (footprints.Footprint(
        info="Abstract mbdetect footprint",
        attr=dict(
            git_ref=dict(
                info="The Git ref (branch, tag, commit) to be exported to the pack.",
            ),
            repository=dict(
                info="The git repository to be used (on the target machine).",
            ),
            # Below: tunneling
            ssh_tunnel_relay_machine=dict(
                info="If not None, activate SSH tunnel through this relay machine.",
                optional=True,
                default=None
            ),
            ssh_tunnel_entrance_port=dict(
                info="Entrance port of the tunnel, in case of a tunnel. If None, search for a free one.",
                optional=True,
                type=int,
                default=None
            ),
            ssh_tunnel_target_host=dict(
                info="Target host of the tunnel.",
                optional=True,
                default='mirage7.meteo.fr'
            ),
            ssh_tunnel_output_port=dict(
                info="The output port of the tunnel.",
                optional=True,
                type=int,
                default=9418
            ),
            path_to_repo=dict(
                info="Path to repo on relay machine (git://relay:port/{path_to_repo}).",
                optional=True,
                default='arpifs'
            )
        )
    ),)

    def _set_git(self, rh, opts):  # @UnusedVariable
        set_env4git()

    _MIXIN_PREPARE_HOOKS = (_set_git, )

    @contextmanager
    def _with_potential_ssh_tunnel(self):
        if self.ssh_tunnel_relay_machine:
            # tunneling is required
            sshobj = self.system.ssh(self.ssh_tunnel_relay_machine)
            with sshobj.tunnel(self.ssh_tunnel_target_host, self.ssh_tunnel_output_port,
                               entranceport=self.ssh_tunnel_entrance_port) as tunnel:
                # entering the contextmanager
                # save origin remote URL, and temporarily replace with tunnel entrance
                temp_url = 'git://localhost:{}/{}'.format(tunnel.entranceport, self.path_to_repo)
                logger.info("Temporarily switching remote.origin.url to SSH tunnel entrance: {}".format(temp_url))
                with self.system.cdcontext(self.repository):
                    origin_url = self.system.spawn(['git', 'config', '--get', 'remote.origin.url'],
                                                   output=True)
                    self.system.spawn(['git', 'config', '--replace-all', 'remote.origin.url', temp_url],
                                      output=False)
                # give hand back to inner context
                try:
                    yield
                finally:
                    # getting out of contextmanager : set origin remote URL back to what it was
                    if origin_url:
                        logger.info("Set back remote.origin.url to initial value: {}".format(str(origin_url[0])))
                        with self.system.cdcontext(self.repository):
                            self.system.spawn(['git', 'config', '--replace-all', 'remote.origin.url', origin_url[0]],
                                              output=False)
        else:
            yield


class IAL_gitref_to_IncrementalPack(AlgoComponent, GmkpackDecoMixin, GitDecoMixin,
                                    _CrashWitnessDecoMixin):
    """
    DEPRECATED
    Make an incremental pack (gmkpack) with sources from a IAL Git ref.
    """

    _footprint = [
        dict(
            info = "Make an incremental pack (gmkpack) with sources from a IAL Git ref.",
            attr = dict(
                kind = dict(
                    values   = ['ia4h_gitref2incrpack', 'ial_gitref2incrpack'],
                ),
                compiler_label = dict(
                    info = "Gmkpack compiler label.",
                ),
                compiler_flag = dict(
                    info = "Gmkpack compiler flag.",
                    optional = True,
                    default = None
                ),
                start_ref = dict(
                    info = "Git ref to make diff with, to compute the increment (careful).",
                    optional = True,
                    default = None
                ),
                packname = dict(
                    info = "Name of the pack; defaults to self.git_ref. " +
                           "If '__guess__', name is guessed using davai.util.guess_packname().",
                    optional = True,
                    default = None,
                ),
                preexisting_pack = dict(
                    info = "Set to True if the pack preexists.",
                    type = bool,
                    optional = True,
                    default = False,
                ),
                rootpack = dict(
                    info = "Directory in which to find rootpack(s).",
                    optional = True,
                    default = None,
                ),
            )
        )
    ]

    def prepare(self, rh, opts):  # @UnusedVariable
        if self.rootpack is None:
            rootpack = self.target.config.get('gmkpack', 'ROOTPACK')
            if rootpack not in ('', None):
                self._attributes['rootpack'] = rootpack

    def execute(self, rh, kw):  # @UnusedVariable
        from ial_build.algos import IALgitref2pack  # @UnresolvedImport
        if self.start_ref is not None:
            raise NotImplementedError("Deprecated argument: 'start_ref'")
        if self.packname not in (None, '__guess__'):
            raise NotImplementedError("Deprecated argument: 'packname'")
        IALgitref2pack(self.git_ref,
                       self.repository,
                       pack_type='incr',
                       preexisting_pack=self.preexisting_pack,
                       clean_if_preexisting=self.cleanpack,
                       compiler_label=self.compiler_label,
                       compiler_flag=self.compiler_flag,
                       homepack=self.homepack,
                       rootpack=self.rootpack)


class IAL_gitref_to_MainPack(AlgoComponent, GmkpackDecoMixin, GitDecoMixin,
                             _CrashWitnessDecoMixin):
    """
    DEPRECATED
    Make a main pack (gmkpack) with sources from a IAL Git ref.
    """

    _footprint = [
        dict(
            info = "Make a main pack (gmkpack) with sources from a IAL Git ref.",
            attr = dict(
                kind = dict(
                    values   = ['ia4h_gitref2mainpack', 'ial_gitref2mainpack'],
                ),
                compiler_label = dict(
                    info = "Gmkpack compiler label.",
                ),
                compiler_flag = dict(
                    info = "Gmkpack compiler flag.",
                    optional = True,
                    default = None
                ),
                populate_filter_file = dict(
                    info = ("File of files to be filtered at populate time. " +
                            "Special values: " +
                            "'__inconfig__' will read according file in config of ial_build package; " +
                            "'__inview__' will read according file in Git view."),
                    optional = True,
                    default = '__inconfig__'
                ),
                link_filter_file = dict(
                    info = ("File of symbols to be filtered at link time. " +
                            "Special values: " +
                            "'__inconfig__' will read according file in config of ial_build package; " +
                            "'__inview__' will read according file in Git view."),
                    optional = True,
                    default = '__inconfig__'
                ),
            )
        )
    ]

    def execute(self, rh, kw):  # @UnusedVariable
        from ial_build.algos import IALgitref2pack  # @UnresolvedImport
        if self.populate_filter_file not in (None, '__inconfig__'):
            raise NotImplementedError("Deprecated argument: 'populate_filter_file'")
        if self.link_filter_file not in (None, '__inconfig__'):
            raise NotImplementedError("Deprecated argument: 'link_filter_file'")
        IALgitref2pack(self.git_ref,
                       self.repository,
                       pack_type=self.pack_type,
                       preexisting_pack=self.preexisting_pack,
                       clean_if_preexisting=self.cleanpack,
                       compiler_label=self.compiler_label,
                       compiler_flag=self.compiler_flag,
                       homepack=self.homepack)


class IALgitref2Pack(AlgoComponent, GmkpackDecoMixin, GitDecoMixin,
                     _CrashWitnessDecoMixin):
    """Make a pack (gmkpack) with sources from a IAL Git ref."""

    _footprint = [
        dict(
            info = "Make a pack (gmkpack) with sources from a IAL Git ref.",
            attr = dict(
                kind = dict(
                    values   = ['ialgitref2pack'],
                ),
                pack_type = dict(
                    info = "Pack type, whether main (full) or incremental.",
                    values = ['incr', 'main'],
                    optional = True,
                    default = 'incr',
                ),
                compiler_label = dict(
                    info = "Gmkpack compiler label.",
                    optional = True,
                    default = None
                ),
                compiler_flag = dict(
                    info = "Gmkpack compiler flag.",
                    optional = True,
                    default = None
                ),
                preexisting_pack = dict(
                    info = "Set to True if the pack preexists.",
                    type = bool,
                    optional = True,
                    default = False,
                ),
                rootpack = dict(
                    info = "Directory in which to find rootpack(s).",
                    optional = True,
                    default = None,
                ),
            )
        )
    ]

    def execute(self, rh, kw):  # @UnusedVariable
        from ial_build.algos import IALgitref2pack  # @UnresolvedImport
        IALgitref2pack(self.git_ref,
                       self.repository,
                       pack_type=self.pack_type,
                       preexisting_pack=self.preexisting_pack,
                       clean_if_preexisting=self.cleanpack,
                       compiler_label=self.compiler_label,
                       compiler_flag=self.compiler_flag,
                       homepack=self.homepack,
                       rootpack=self.rootpack)


class Bundle2Pack(AlgoComponent, GmkpackDecoMixin,
                  _CrashWitnessDecoMixin):
    """Make a pack (gmkpack) with sources from a bundle."""

    _footprint = [
        dict(
            info = "Make a pack (gmkpack) with sources from a bundle.",
            attr = dict(
                engine = dict(
                    values = ['algo'],
                    optional = True,
                    default = 'algo',
                ),
                kind = dict(
                    values = ['bundle2pack'],
                ),
                bundle_file = dict(
                    info = "Path to bundle file. If not provided, look up resources.",
                    optional = True,
                    default = None
                ),
                pack_type = dict(
                    info = "Pack type, whether main (full) or incremental.",
                    values = ['incr', 'main'],
                    optional = True,
                    default = 'incr',
                ),
                compiler_label = dict(
                    info = "Gmkpack compiler label.",
                    optional = True,
                    default = None
                ),
                compiler_flag = dict(
                    info = "Gmkpack compiler flag.",
                    optional = True,
                    default = None
                ),
                preexisting_pack = dict(
                    info = "Set to True if the pack preexists.",
                    type = bool,
                    optional = True,
                    default = False,
                ),
                rootpack = dict(
                    info = "Directory in which to find rootpack(s).",
                    optional = True,
                    default = None,
                ),
                bundle_src_dir = dict(
                    info = ("Directory in which to download/update repositories. " +
                            "Defaults to the temporary directory of execution, which may not be optimal."),
                    optional = True,
                    default = None,
                ),
                update_git_repositories = dict(
                    info = ("If False, take git repositories as they are, " +
                            "without trying to update (fetch/checkout/pull). " +
                            "(!) Required to get uncommited code from a repo (with according bundle_cache_dir), " +
                            "but projects versions may not be consistent with versions requested in bundle file."),
                    optional = True,
                    type = bool,
                    default = True
                ),
                bundle_download_threads = dict(
                    info = ("Number of parallel threads to download (clone/fetch) repositories. " +
                            "0 turns into an auto-determined number."),
                    optional = True,
                    type = int,
                    default = 1
                ),
            )
        )
    ]

    def execute(self, rh, kw):  # @UnusedVariable
        from ial_build.algos import bundle_file2pack  # @UnresolvedImport
        if self.bundle_file is None:
            bundle_r = [s for s in self.context.sequence.effective_inputs(role=('Bundle',))]
            if len(bundle_r) > 1:
                raise ValueError("Too many bundle resources found.")
            elif len(bundle_r) == 0:
                raise ValueError("No bundle resources found, nor is bundle file explicitly provided.")
            bundle_file = bundle_r[0].rh.container.localpath()
        else:
            bundle_file = self.bundle_file
        bundle_file2pack(bundle_file,
                         pack_type=self.pack_type,
                         update=self.update_git_repositories,
                         preexisting_pack=self.preexisting_pack,
                         clean_if_preexisting=self.cleanpack,
                         src_dir=self.bundle_src_dir,
                         compiler_label=self.compiler_label,
                         compiler_flag=self.compiler_flag,
                         homepack=self.homepack,
                         rootpack=self.rootpack)


class PackBuildExecutables(AlgoComponent, GmkpackDecoMixin,
                           _CrashWitnessDecoMixin):
    """Compile sources and link executables within a pack (gmkpack)."""

    _footprint = [
        dict(
            info = "Compile sources and link executables within a pack (gmkpack).",
            attr = dict(
                kind = dict(
                    values   = ['pack_build_executables'],
                ),
                packname = dict(
                    info = "The pack to be compiled.",
                ),
                programs = dict(
                    info = "Programs to be built.",
                    optional = True,
                    default = '__usual__'
                ),
                regenerate_ics = dict(
                    info = "Whether to regenerate or not the ics_<program> scripts.",
                    type = bool,
                    optional = True,
                    default = True
                ),
                other_options = dict(
                    info = "Other options (cf. ics_build_for() method).",
                    type = FPDict,
                    optional = True,
                    default = dict(),
                ),
                fatal_build_failure = dict(
                    info = "Whether to make fatal build errors, for any or at the end.",
                    optional = True,
                    default = '__any__',
                    values = ['__any__', '__finally__', '__none__']
                ),
            )
        )
    ]

    def execute(self, rh, kw):  # @UnusedVariable
        from ial_build.algos import pack_build_executables  # @UnresolvedImport
        pack_build_executables(self.packname,
                               programs=self.programs,
                               silent=True,  # so that output goes in a file
                               regenerate_ics=self.regenerate_ics,
                               cleanpack=self.cleanpack,
                               other_options=self.other_options,
                               homepack=self.homepack,
                               fatal_build_failure=self.fatal_build_failure,
                               dump_build_report=True)

    def postfix(self, rh, kw):  # @UnusedVariable
        from ial_build.pygmkpack import GmkpackTool  # @UnresolvedImport
        bindir = self.system.path.join(GmkpackTool.get_homepack(self.homepack), self.packname, 'bin')
        b2kind = {'MASTERODB': 'ifsmodel', 'PGD': 'buildpgd',
                  'OOTESTVAR': 'oopsbinary-ootestcomponent',
                  'OOVAR': 'oopsbinary-oovar'}
        # copy binaries on workdir
        print("Copy binaries on workdir:")
        for p in self.system.listdir(bindir):
            outname = binaries_syntax_in_workdir.format(b2kind.get(p, p.lower()))
            print(' + {} -> {}'.format(self.system.path.join(bindir, p), outname))
            self.system.copyfile(self.system.path.join(bindir, p),
                                 outname)
