# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex import toolbox
from vortex.layout.nodes import Task


class BasicStdpost(Task):
    """
    Leverage the :package:`sandbox` package's GribInfosSequential
    AlgoComponents class.

    It also implements:

    * Promises on md5 output files;
    * Automatic diff on outputs in order to check that the results are
      reprodicible with a reference.
    """

    def process(self):

        if 'early-fetch' in self.steps or 'fetch' in self.steps:

            self.sh.subtitle('Fetching the GRIB input files')
            tb1 = toolbox.input(
                role='Gridpoint',
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
            print('tb = {!r}\n'.format(tb1))

        if 'fetch' in self.steps:
            pass

        if 'compute' in self.steps:

            self.sh.subtitle('Creating the AlgoComponent')
            tbalgo = toolbox.algo(
                kind='gribinfos',
                jsonoutput='super.json'
            )
            self.sh.highlight('Running the AlgoComponent')
            self.component_runner(tbalgo)

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

            self.sh.subtitle('Summary file storage')
            tbo2 = toolbox.output(
                kind='gribinfos',
                # The provider part...
                namespace=self.conf.fullspace,
                block='forecast',
                experiment=self.conf.xpid,
                # The container part
                filename='super.json'
            )


class BasicPlusStdpost(Task):
    """
    Leverage the :package:`sandbox` package's GribInfosArbitraryOrder
    AlgoComponents class.

    It also implements:

    * Promises on md5 output files;
    * Automatic diff on outputs in order to check that the results are
      reprodicible with a reference.
    """

    def process(self):

        if 'early-fetch' in self.steps or 'fetch' in self.steps:

            self.sh.subtitle('Fetching the GRIB input files')
            tb1 = toolbox.input(
                role='Gridpoint',
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

        if 'fetch' in self.steps:
            pass

        if 'compute' in self.steps:

            self.sh.subtitle('Creating the AlgoComponent')
            tbalgo = toolbox.algo(
                kind='gribinfos_ao',
                jsonoutput='super.json'
            )
            self.sh.highlight('Running the AlgoComponent')
            self.component_runner(tbalgo)

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
