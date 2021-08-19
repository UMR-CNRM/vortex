# -*- coding: utf-8 -*-
"""
DAVAI sources build (branch export, compilation&link) AlgoComponents.
"""
from __future__ import print_function, absolute_import, unicode_literals, division

import tempfile
from contextlib import contextmanager

import footprints
from footprints import FPDict
from bronx.fancies import loggers

from vortex.algo.components import (AlgoComponent, AlgoComponentDecoMixin,
                                    algo_component_deco_mixin_autodoc)

from .mixins import _CrashWitnessDecoMixin


#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


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
        gmk_installdir = self.target.config.get('gmkpack', 'gmkpack_installdir')
        self.env.setbinpath(self.system.path.join(gmk_installdir, 'util'), 0)
        self.env['GMKROOT'] = gmk_installdir
        prefix = self.system.glove.user + '.gmktmp.'
        self.env['GMKTMP'] = tempfile.mkdtemp(prefix=prefix, dir='/tmp')  # would be much slower on Lustre
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
        git_installdir = self.target.config.get('git', 'git_installdir')
        if git_installdir not in ('', None):
            self.env.setbinpath(self.system.path.join(git_installdir, 'bin'), 0)
            self.env['GIT_EXEC_PATH'] = self.system.path.join(git_installdir,
                                                              'libexec',
                                                              'git-core')

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


class IA4H_gitref_to_IncrementalPack(AlgoComponent, GmkpackDecoMixin, GitDecoMixin,
                                     _CrashWitnessDecoMixin):
    """Make an incremental pack (gmkpack) with sources from a IA4H Git ref."""

    _footprint = [
        dict(
            info = "Make an incremental pack (gmkpack) with sources from a IA4H Git ref.",
            attr = dict(
                kind = dict(
                    values   = ['ia4h_gitref2incrpack'],
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
        from ia4h_scm.algos import IA4H_gitref_to_incrpack  # @UnresolvedImport
        with self._with_potential_ssh_tunnel():
            IA4H_gitref_to_incrpack(self.repository,
                                    self.git_ref,
                                    self.compiler_label,
                                    start_ref=self.start_ref,
                                    packname=self.packname,
                                    compiler_flag=self.compiler_flag,
                                    preexisting_pack=self.preexisting_pack,
                                    clean_if_preexisting=self.cleanpack,
                                    rootpack=self.rootpack,
                                    homepack=self.homepack)


class IA4H_gitref_to_MainPack(AlgoComponent, GmkpackDecoMixin, GitDecoMixin,
                              _CrashWitnessDecoMixin):
    """Make a main pack (gmkpack) with sources from a IA4H Git ref."""

    _footprint = [
        dict(
            info = "Make a main pack (gmkpack) with sources from a IA4H Git ref.",
            attr = dict(
                kind = dict(
                    values   = ['ia4h_gitref2mainpack'],
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
                            "'__inconfig__' will read according file in config of ia4h_scm package; " +
                            "'__inview__' will read according file in Git view."),
                    optional = True,
                    default = '__inconfig__'
                ),
                link_filter_file = dict(
                    info = ("File of symbols to be filtered at link time. " +
                            "Special values: " +
                            "'__inconfig__' will read according file in config of ia4h_scm package; " +
                            "'__inview__' will read according file in Git view."),
                    optional = True,
                    default = '__inconfig__'
                ),
            )
        )
    ]

    def execute(self, rh, kw):  # @UnusedVariable
        from ia4h_scm.algos import IA4H_gitref_to_main_pack  # @UnresolvedImport
        with self._with_potential_ssh_tunnel():
            IA4H_gitref_to_main_pack(self.repository,
                                     self.git_ref,
                                     self.compiler_label,
                                     compiler_flag=self.compiler_flag,
                                     homepack=self.homepack,
                                     populate_filter_file=self.populate_filter_file,
                                     link_filter_file=self.link_filter_file)


class Bundle_to_MainPack(AlgoComponent, GmkpackDecoMixin,
                         _CrashWitnessDecoMixin):
    """Make a main pack (gmkpack) with sources from a bundle."""

    _footprint = [
        dict(
            info = "Make a main pack (gmkpack) with sources from a bundle.",
            attr = dict(
                kind = dict(
                    values   = ['bundle2mainpack'],
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
                            "'__inconfig__' will read according file in config of ia4h_scm package; " +
                            "'__inview__' will read according file in Git view."),
                    optional = True,
                    default = '__inconfig__'
                ),
                link_filter_file = dict(
                    info = ("File of symbols to be filtered at link time. " +
                            "Special values: " +
                            "'__inconfig__' will read according file in config of ia4h_scm package; "
                            "'__inview__' will read according file in Git view."),
                    optional = True,
                    default = '__inconfig__'
                ),
                bundle_cache_dir = dict(
                    info = ("Cache directory in which to download/update repositories. " +
                            "Defaults to the temporary directory of execution, which may not be optimal."),
                    optional = True,
                    default = None,
                ),
                update_git_repositories = dict(
                    info = ("If False, take git repositories as they are, " +
                            "without trying to update (fetch/checkout/pull)"),
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
        from ia4h_scm.algos import bundle_to_main_pack  # @UnresolvedImport
        bundle = [s for s in self.context.sequence.effective_inputs(role=('Bundle',))]
        bundle_path = bundle[0].rh.container.localpath()
        bundle_to_main_pack(bundle_path,
                            self.compiler_label,
                            compiler_flag=self.compiler_flag,
                            bundle_cache_dir=self.bundle_cache_dir,
                            homepack=self.homepack,
                            populate_filter_file=self.populate_filter_file,
                            link_filter_file=self.link_filter_file,
                            update_git_repositories=self.update_git_repositories,
                            bundle_download_threads=self.bundle_download_threads)


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
        from ia4h_scm.algos import pack_build_executables  # @UnresolvedImport
        pack_build_executables(self.packname,
                               programs=self.programs,
                               silent=True,  # so that output goes in a file
                               regenerate_ics=self.regenerate_ics,
                               cleanpack=self.cleanpack,
                               other_options=self.other_options,
                               homepack=self.homepack,
                               fatal_build_failure=self.fatal_build_failure,
                               dump_build_report=True)
