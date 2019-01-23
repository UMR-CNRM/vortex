#!/opt/softs/python/2.7.5/bin/python -u
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

__all__ = []

import vortex
from vortex import toolbox

from iga.tools import app


def setup(t, **kw):
    return [ Forecast(t, **kw) ]


class Forecast(app.Application):

    def setup(self, **kw):
        """Fix some default experiment settings."""

        t = self.ticket

        self.subtitle('Experiment Setup')
        self.conf.update(kw)

        print('FC term  =', self.conf.fc_term)
        print('FC terms =', self.conf.fc_terms)
        print('FP terms =', self.conf.fp_terms)

        geomodel = vortex.data.geometries.get(tag=self.conf.fc_geometry)

        print('FC MODEL GEOMETRY =', geomodel)
        print('FC BDAP DOMAINS   =', self.conf.fp_domains)

        # Attributs par défaut pour toutes les résolutions d'empreintes à suivre.
        toolbox.defaults(
            model     = t.glove.vapp,           # Comment souvent, le model est l'application
            date      = self.conf.rundate,      # C'est un véritable "objet" de type Date
            cutoff    = 'production',           # En général positionné par l'environnement
            geometry  = geomodel,               # C'est un objet de type Geometry
            namespace = 'vortex.cache.fr',      # Nous ne ferons des sorties que sur l'espace disque
        )

        # --------------------------------------------------------------------------------------------------

        self.subtitle('Predefined Providers')

        # Provider de ressources internes au flux de l'expérience en cours
        self.conf.p_flow = vortex.proxy.provider(
            experiment  = 'TEST',
            block       = 'forecast',
        )

        print('Provider interne :', self.conf.p_flow)

        # Provider de ressources extérieures au flux de l'expérience en cours (ici, l'archive oper)
        import iga.data

        self.conf.p_extern = vortex.proxy.provider(
            suite       = 'oper',
            igakey      = '[glove:vconf]',
            namespace   = '[suite].inline.fr',
        )

        print('Provider externe :', self.conf.p_extern)

        # Provider de ressources constantes (hors du flux), en général GEnv

        # On récupère donc le module genv qui fournit une interface simple sur l'outil du même nom.
        from gco.tools import genv

        # En attendant un outil intégré (qui devrait se trouver dans un module op dédié),
        # on utilise un petit outil très simplifié nommé genvop en spécifiant nom de commande et path.
        genv.genvcmd  = 'genvop'
        genv.genvpath = '/home/gmap/mrpm/esevault/public/op-tools'

        # On définit le répertoire de recherche de cycles prédéfis comme étant le répertoire de l'outil genv
        self.env.OPGENVROOT = genv.genvpath

        # Ainsi outillés, nous pouvons maintenant définir un cycle, par son nom gco,
        # et demander au module genv de "remplir" la définition de cycle avec tous les composants associés.
        self.conf.cycle = self.env.get('op_cycle', 'cy38t1_op2.15')
        genv.autofill(self.conf.cycle)

        self.conf.p_const = vortex.proxy.provider(
            # implicit: vapp, vconf
            # optional: gnamespace, gspool
            genv = self.conf.cycle,
        )

        print('Provider const :', self.conf.p_const)

    def process(self):
        """Core processing of a forecast experiment."""

        t = self.ticket

        if self.fetch in self.steps:

            self.subtitle('Inputs')

            i_analysis = toolbox.input(
                # section
                role        = 'Analysis',
                # provider
                provider    = self.conf.p_extern,
                # container
                local       = 'ICMSHFCSTINIT',
                # resource
                    # implicit: cutoff, date, geometry, model
                    # optional: clscontents, filling, filtering, nativefmt
                kind        = 'analysis',
            )

            i_climmodel = toolbox.input(
                # section
                role        = 'GlobalClim',
                # provider
                provider    = self.conf.p_const,
                # container
                local       = 'Const.Clim',
                # resource
                    # implicit: geometry, model
                    # optional: clscontents, gvar, nativefmt
                kind        = 'clim_model',
                month       = '[date:ymd]',
            )

            i_climbdap = toolbox.input(
                # section
                role        = 'LocalClim',
                # provider
                provider    = self.conf.p_const,
                # container
                local       = 'const.clim.[geometry::area]',
                # resource
                    # implicit: model
                    # optional: clscontents, gdomain, gvar, nativefmt
                kind        = 'clim_bdap',
                month       = '[date:ymd]',
                geometry    = self.conf.fp_domains,
            )

            i_matrix = toolbox.input(
                # section
                role        = 'LocalClim',
                # provider
                provider    = self.conf.p_const,
                # container
                local       = 'matrix.fil.[scope::area]',
                # resource
                    # implicit: geometry, model
                    # optional: clscontents, gvar, nativefmt
                kind        = 'matfilter',
                scope       = self.conf.fp_domains,
            )

            i_rrtm = toolbox.input(
                # section
                role        = 'RrtmConst',
                # provider
                provider    = self.conf.p_const,
                # container
                local       = '[kind].tgz',
                # resource
                    # implicit: model
                    # optional: clscontents, gvar, nativefmt
                kind='rrtm',
            )

            i_rtcoef = toolbox.input(
                # section
                role        = 'RtCoef',
                # provider
                provider    = self.conf.p_const,
                # container
                local       = '[kind].tgz',
                # resource
                    # implicit: model
                    # optional: clscontents, gvar, nativefmt
                kind='rtcoef',
            )

            i_namelistfc = toolbox.input(
                # section
                role        = 'Namelist',
                # provider
                provider    = self.conf.p_const,
                # container
                local       = 'fort.4',
                # resource
                    # implicit: model
                    # optional: binary, clscontents, gvar, nativefmt
                kind        = 'namelist',
                source      = 'namelistfcp'
            )

            i_namxxt = toolbox.input(
                # section
                role        = 'FullPosMap',
                # provider
                provider    = self.conf.p_const,
                # container
                local       = 'xxt.def',
                # resource
                    # optional: clscontents, gvar, nativefmt
                kind        = 'xxtdef',
                binary      = '[model]'
            )

            i_namselect = toolbox.input(
                # section
                role        = 'FullPosSelect',
                # collaborative helper
                helper      = i_namxxt[0].contents,
                # provider
                provider    = self.conf.p_const,
                # container
                local       = '[helper::xxtnam]',
                # resource
                    # implicit: model
                    # optional: binary, clscontents, gvar, nativefmt
                kind        = 'namselect',
                source      = '[helper::xxtsrc]',
                term        = self.conf.fp_terms
            )

            i_bin = toolbox.input(
                # section
                role        = 'Binary',
                # provider
                provider    = self.conf.p_const,
                # container
                local       = 'MASTER',
                # resource
                    # implicit: model
                    # optional: clscontents, compiler, gvar, jacket, nativefmt, static
                kind        = 'ifsmodel',
            )

        # --------------------------------------------------------------------------------------------------

            self.subtitle('Effective Inputs')
            toolbox.show_inputs()

        # --------------------------------------------------------------------------------------------------

        if self.compute in self.steps:

            self.subtitle('Algo Component')

            fcalgo = toolbox.algo(
                # optional: conf, fcunit, inline, ioserver, mpiname, mpitool, timescheme, xpname
                engine      = 'parallel',
                kind        = 'forecast',
                fcterm      = self.conf.fc_term,
                timestep    = 514.286
            )

            # L'exécution se fait en passant en premier argument le premier binaire récupéré auparavant.
            # Nous pourrions tout aussi bien boucler sur tous les binaires, mais on suppose en général
            # qu'il n'y en a qu'un !

            fcalgo.run(
                i_bin[0],
                mpiopts = dict(nn=t.env.SLURM_NNODES, nnp=4)
            )

        # --------------------------------------------------------------------------------------------------

        if self.backup in self.steps:

            self.subtitle('Outputs')

            o_historic = toolbox.output(
                # section
                role        = 'ModelState',
                fatal       = True,
                # provider
                provider    = self.conf.p_flow,
                # container
                local       = 'ICMSHFCST+[term::fmth]',
                # resource
                    # implicit: cutoff, date, geometry, model
                    # optional: clscontents, nativefmt
                kind        = 'historic',
                term        = self.conf.fc_terms
            )

            o_fullpos = toolbox.output(
                # section
                role        = 'Gridpoint',
                # provider
                provider    = self.conf.p_flow,
                # container
                local       = 'PFFCST[geometry::area]+[term::fmth]',
                actualfmt   = 'fa',
                # resource
                    # implicit: cutoff, date, model
                    # optional: clscontents
                kind        = 'gridpoint',
                origin      = 'historic',
                nativefmt   = '[actualfmt]',
                geometry    = self.conf.fp_domains,
                term        = self.conf.fp_terms,
            )

            o_isp = toolbox.output(
                # section
                role        = 'Isp',
                # provider
                provider    = self.conf.p_flow,
                # container
                local       = 'fort.91',
                # resource
                    # implicit: cutoff, date, geometry, model
                    # optional: clscontents, nativefmt
                kind        = 'isp',
            )

            o_dhfd = toolbox.output(
                # section
                role        = 'Dhfd',
                # provider
                provider    = self.conf.p_flow,
                # container
                local       = r'DHFDLFCST+{glob:h:\d+}',
                actualfmt   = 'lfa',
                # resource
                    # implicit: cutoff, date, geometry, model
                    # optional: clscontents, nativefmt
                kind        = 'ddh',
                scope       = 'dlimited',
                term        = '[glob:h]',
            )

            o_dhfg = toolbox.output(
                # section
                role        = 'Dhfg',
                # provider
                provider    = self.conf.p_flow,
                # container
                local       = r'DHFGLFCST+{glob:h:\d+}',
                actualfmt   = 'lfa',
                # resource
                    # implicit: cutoff, date, geometry, model
                    # optional: clscontents, nativefmt
                kind        = 'ddh',
                scope       = 'global',
                term        = '[glob:h]',
            )

            o_dhfz = toolbox.output(
                # section
                role        = 'Dhfz',
                # provider
                provider    = self.conf.p_flow,
                # container
                local       = r'DHFZOFCST+{glob:h:\d+}',
                actualfmt   = 'lfa',
                # resource
                    # implicit: cutoff, date, geometry, model
                    # optional: clscontents, nativefmt
                kind        = 'ddh',
                scope       = 'zonal',
                term        = '[glob:h]',
            )

            o_listing = toolbox.output(
                # section
                role='Listing',
                # provider
                provider    = self.conf.p_flow,
                # container
                local       = r'NODE.{glob:a:\d+}_{glob:b:\d+}',
                actualfmt   = 'ascii',
                seta        = '[glob:a]',
                setb        = '[glob:b]',
                # resource
                    # implicit: cutoff, date, geometry, model
                    # optional: clscontents, mpi, openmp, nativefmt
                kind        = 'plisting',
                task        = e.get('SMSNAME', 'std-forecst'),
            )

        # --------------------------------------------------------------------------------------------------

            self.subtitle('Effective Outputs')
            toolbox.show_outputs()

        # --------------------------------------------------------------------------------------------------

        self.subtitle('End of execution')

