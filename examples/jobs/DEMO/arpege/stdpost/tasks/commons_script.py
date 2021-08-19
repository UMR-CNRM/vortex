# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex import toolbox
from vortex.layout.nodes import Task


class ScriptStdpost(Task):
    """
    Leverage the :package:`sandbox` package's GribInfosScript or
    GribInfosParaScript AlgoComponents classes.

    It also implements:

    * Promises on md5 output files;
    * Automatic diff on outputs in order to check that the results
      reproduce a reference.
    """

    def process(self):
        """The execution sequence."""

        if 'early-fetch' in self.steps or 'fetch' in self.steps:

            self.sh.subtitle('Fetching the GRIB input files')
            tb1 = toolbox.input(
                role='Gridpoint',
                expected=True,
                # The Resource part...
                kind='gridpoint',
                geometry=self.conf.pp_geometries,
                nativefmt='grib',
                origin='historic',
                term=self.conf.pp_terms,
                # The provider part...
                namespace='vortex.multi.fr',
                block='forecast',
                member=self.conf.pp_members,
                experiment='demo',
                vconf='pearp',
                # The container part
                filename='grib_glob05_m[member]_[term:fmth]'
            )

            self.sh.subtitle('Promising the indiviual md5 files storage')
            tbp1 = toolbox.promise(
                role='Gridpoint Checksum',
                # The Resource part...
                kind='gridpoint',
                geometry=self.conf.pp_geometries,
                nativefmt='ascii',
                hash_method='md5',
                origin='historic',
                term=self.conf.pp_terms,
                # The provider part...
                namespace='vortex.cache.fr',
                block='forecast',
                member=self.conf.pp_members,
                experiment='demo',
                # The container part
                filename='grib_glob05_m[member]_[term:fmth].md5'
            )

            self.sh.subtitle('Fetching the post-processign script')
            tbx = toolbox.executable(
                role='Script',
                # The Resource part...
                kind='demo_ppscript',
                # The provider part...
                genv=self.conf.cycle,
                # The container part
                filename='ppscript'
            )

        if 'fetch' in self.steps:
            pass

        if 'compute' in self.steps:

            self.sh.subtitle('Creating the AlgoComponent')
            tbalgo = toolbox.algo(
                kind=self.conf.gribscript_algo,
                jsonoutput='super.json',
                interpreter='bash',
                ntasks=self.conf.ntasks,
            )
            self.sh.highlight('Running the AlgoComponent')
            self.component_runner(tbalgo, tbx)

        if 'backup' in self.steps or 'late-backup' in self.steps:

            pass

        if 'late-backup' in self.steps:

            self.sh.subtitle('Indiviual md5 files storage')
            tbo1 = toolbox.output(
                role='Gridpoint Checksum',
                promised=True,
                # The Resource part...
                kind='gridpoint',
                geometry=self.conf.pp_geometries,
                nativefmt='ascii',
                hash_method=self.conf.hash_method,
                origin='historic',
                term=self.conf.pp_terms,
                # The provider part...
                namespace=self.conf.fullspace,
                block='forecast',
                member=self.conf.pp_members,
                experiment=self.conf.xpid,
                # The container part
                filename='grib_glob05_m[member]_[term:fmth].md5'
            )

            self.sh.subtitle('Starting automatic diff on indiviual md5 files')
            tbo1d = toolbox.diff(
                # The Resource part...
                kind='gridpoint',
                geometry=self.conf.pp_geometries,
                nativefmt='ascii',
                hash_method=self.conf.hash_method,
                origin='historic',
                term=self.conf.pp_terms,
                # The provider part...
                namespace='vortex.multi.fr',
                block='forecast',
                member=self.conf.pp_members,
                experiment=self.conf.auto_diff_xpid,
                # The container part
                filename='grib_glob05_m[member]_[term:fmth].md5'
            )

            self.sh.subtitle('Summary file storage')
            tbo2 = toolbox.output(
                role='Gridpoints Info',
                # The Resource part...
                kind='gribinfos',
                # The provider part...
                namespace=self.conf.fullspace,
                block='forecast',
                experiment=self.conf.xpid,
                # The container part
                filename='super.json'
            )

            self.sh.subtitle('Starting automatic diff on summary file')
            tbo2d = toolbox.diff(
                # The Resource part...
                kind='gribinfos',
                # The provider part...
                namespace='vortex.multi.fr',
                block='forecast',
                experiment=self.conf.auto_diff_xpid,
                # The container part
                filename='super.json'
            )
