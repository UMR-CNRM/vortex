#!/opt/softs/python/2.7.5/bin/python -u
# -*- coding: utf-8 -*-
#SBATCH --exclusive
#SBATCH --verbose
#SBATCH --cpus-per-task=6
#SBATCH --job-name=fc_test_vtx
#SBATCH --mem=30000
#SBATCH --nodes=21
#SBATCH --ntasks-per-node=4
#SBATCH --partition=normal32
#SBATCH --time=00:43:20
##SBATCH --signal=USR2@2500
#SBATCH --mail-user=dsiop_igasc@meteo.fr --mail-type=ALL

"""
AVERTISSEMENT

Cette tâche est un script `standalone` destiné à tourner tel quel, sans aucun prérequis
ni fichier de paramétrisations, ne s'appuyant donc que sur les valeurs par défaut
de la boîte à outils Vortex sur le supercalculateur prolix de Météo France.

Il a une portée essentiellement pédagogique.
"""

# Afin de bénéficier des packages footprints et vortex, il convient de spécifier
# à l'interpréteur python de nouveaux points de départ pour la recherche de modules ;
# c'est traditionnelement le module sys qui permet cette spécification.
import sys
sys.path.append('/home/gmap/mrpm/esevault/public/vortex/site')
sys.path.append('/home/gmap/mrpm/esevault/public/vortex/src')

# Il est souvent commode de disposer d'un raccourci vers le package footprints...
# mais cela n'a rien d'obligatoire
import footprints as fp

# L'importation du package vortex... qui nous ouvre le saint des saints... ou presque !
import vortex

# Les commandes procédurales les plus importantes sont pilotées par un module dédié: toolbox.
from vortex import toolbox

toolbox.justdoit  = True    # En activant ce drapeau, toutes les sections qui seront définies
                            # par la suite essaieront de réaliser immédiatement leur action de base.

toolbox.getinsitu = True    # Lors de la récupération d'une ressource (Input/get), l'activation de ce drapeau
                            # ne lancera la récupération effective de la ressource que si le fichier
                            # conteneur n'existe pas déjà dans le répertoire courant.

# Le package common permettra d'accéder aux ressources ou composants algorithmiques
# dont la définition est commune aux opérations et au mode recherche.
import common

# Ces importations de haut niveau terminées, le travail proprement dit commence.
# Il est là aussi commode de se définir quelques raccourcis vers des objets stars.

t = vortex.ticket()         # Le ticket de session regroupe tous les éléments disparates
                            # que nous pourrions vouloir manipuler: l'environnement courant,
                            # l'interface avec le système, le contexte d'exécution,etc.

e = t.env                   # L'environnement courant sous forme d'un pseudo-dictionnaire
                            # aux fonctionalités étendues.

sh = t.sh                   # Interface étendue avec le shell... même objet que vortex.sh() !

sh.title('Start')

# On active le mode verbose du shell qui va tracer tous les appels.
sh.trace = True
e.verbose(True, sh)

# On s'affranchit des limites de taille de la pile sur ce système.
sh.setulimit('stack')

# Répertoire d'exécution dédié... c'est une sécurité pour sortir de HOME.
rundir = e.get('RUNDIR', e.WORKDIR + '/rundir')
sh.cd(rundir, create=True)
sh.subtitle('Rundir is ' + rundir)

# Date de base récupérée comme date pivot dans l'environnement
# ou comme la dernière heure synoptique d'il y a au moins 12 heures.
# On utilisera pour cela le module tools.date
from vortex import tools

strdate = e.get('DMT_DATE_PIVOT', tools.date.synop(delta='-PT12H').compact())
rundate = tools.date.Date(strdate)

sh.subtitle('Rundate is ' + rundate.isoformat())

#--------------------------------------------------------------------------------------------------

sh.title('Experiment Setup')

# Définition de la configuration en cours.
# On positionne le vapp et le vconf via le Global Versatile ENVironment (aka glove).
t.glove.setenv(app='arpege', conf='france')

# On définit le term final du forecast et les échéances de post-traitement a priori
fc_term  = 3
fc_terms = range(0, fc_term+1)
fp_terms = fc_terms

print 'FC term =', fc_term, '/ FP terms =', fp_terms

# On fixe la géométrie par défaut du model, usuellement une information de configuration,
# comme celle des domaines BDAP, mais ici, on fixe tout "à la main".
geomodel = vortex.data.geometries.getbyname(e.get('GEOMETRY', 'globalsp'))
bdap_domains = ['euroc25','eurat01','glob05','glob15','glob25']

print 'GEOMETRY OBJ =', geomodel
print 'BDAP DOMAINS =', bdap_domains

# Attributs par défaut pour toutes les résolutions d'empreintes à suivre.
toolbox.defaults(
    model     = t.glove.vapp,           # Comment souvent, le model est l'application
    date      = rundate,                # C'est un véritable "objet" de type Date
    cutoff    = 'production',           # En général positionné par l'environnement
    geometry  = geomodel,               # C'est un objet de type Geometry
    namespace = 'vortex.cache.fr',      # Nous ne ferons des sorties que sur l'espace disque
)

#--------------------------------------------------------------------------------------------------

sh.title('Predefined Providers')

# Provider de ressources internes au flux de l'expérience en cours
p_flux = vortex.proxy.provider(
    experiment  = 'TEST',
    block       = 'forecast',
)

print 'Provider interne :', p_flux

# Provider de ressources extérieures au flux de l'expérience en cours (ici, l'archive oper)
import iga.data

p_extern = vortex.proxy.provider(
    suite       = 'oper',
    igakey      = '[glove:vconf]',
    namespace   = '[suite].inline.fr',
)

print 'Provider externe :', p_extern

# Provider de ressources constantes (hors du flux), en général GEnv

# On récupère donc le module genv qui fournit une interface simple sur l'outil du même nom.
from gco.tools import genv

# En attendant un outil intégré (qui devrait se trouver dans un module op dédié),
# on utilise un petit outil très simplifié nommé genvop en spécifiant nom de commande et path.
genv.genvcmd  = 'genvop'
genv.genvpath = '/home/gmap/mrpm/esevault/public/op-tools'

# On définit le répertoire de recherche de cycles prédéfis comme étant le répertoire de l'outil genv
sh.env.OPGENVROOT = genv.genvpath

# Ainsi outillés, nous pouvons maintenant définir un cycle, par son nom gco,
# et demander au module genv de "remplir" la définition de cycle avec tous les composants associés.
cycle = 'cy38t1_op2.15'
genv.autofill(cycle)

p_const = vortex.proxy.provider(
    # implicit: vapp, vconf
    # optional: gnamespace, gspool
    genv = cycle,
)

print 'Provider const :', p_const

#--------------------------------------------------------------------------------------------------

# Tentative de détermination plus ou moins hasardeuse de l'étape en cours
# Ce genre de chose est évident superflue dans un système intégré
if sys.argv[-1] in ('3', 'backup'):
    npass = 3
elif sys.argv[-1] in ('2', 'compute', 'run') or int(e.get('SLURM_NPROCS', 1)) > 1:
    npass = 2
else:
    npass = 1

#--------------------------------------------------------------------------------------------------

if npass < 3:

    sh.title('Inputs')

    i_analysis = toolbox.input(
        # section
        role        = 'Analysis',
        # provider
        provider    = p_extern,
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
        provider    = p_const,
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
        provider    = p_const,
        # container
        local       = 'const.clim.[geometry::area]',
        # resource
            # implicit: model
            # optional: clscontents, gdomain, gvar, nativefmt
        kind        = 'clim_bdap',
        month       = '[date:ymd]',
        geometry    = bdap_domains,
    )

    i_matrix = toolbox.input(
        # section
        role        = 'LocalClim',
        # provider
        provider    = p_const,
        # container
        local       = 'matrix.fil.[scope::area]',
        # resource
            # implicit: geometry, model
            # optional: clscontents, gvar, nativefmt
        kind        = 'matfilter',
        scope       = bdap_domains,
    )

    i_rrtm = toolbox.input(
        # section
        role        = 'RrtmConst',
        # provider
        provider    = p_const,
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
        provider    = p_const,
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
        provider    = p_const,
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
        provider    = p_const,
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
        provider    = p_const,
        # container
        local       = '[helper::xxtnam]',
        # resource
            # implicit: model
            # optional: binary, clscontents, gvar, nativefmt
        kind        = 'namselect',
        source      = '[helper::xxtsrc]',
        term        = fp_terms
    )

    i_bin = toolbox.input(
        # section
        role        = 'Binary',
        # provider
        provider    = p_const,
        # container
        local       = 'MASTER',
        # resource
            # implicit: model
            # optional: clscontents, compiler, gvar, jacket, nativefmt, static
        kind='ifsmodel',
    )

#--------------------------------------------------------------------------------------------------

    sh.title('Effective Inputs')
    toolbox.show_inputs()

#--------------------------------------------------------------------------------------------------

if npass == 2:

    sh.title('Algo Component')

    fcalgo = toolbox.algo(
        # optional: conf, fcunit, inline, ioserver, mpiname, mpitool, timescheme, xpname
        engine      = 'parallel',
        kind        = 'forecast',
        fcterm      = fc_term,
        timestep=514.286
    )

    # L'exécution se fait en passant en premier argument le premier binaire récupéré auparavant.
    # Nous pourrions tout aussi bien boucler sur tous les binaires, mais on suppose en général
    # qu'il n'y en a qu'un !

    fcalgo.run(
        i_bin[0],                           # Le binaire arpege donc !
        mpiopts = dict(nn=21, nnp=4)        # Les options à passer au lanceur mpi
    )

#--------------------------------------------------------------------------------------------------

if npass == 3:

    sh.title('Outputs')

    o_historic = toolbox.output(
        # section
        role        = 'ModelState',
        fatal       = True,
        # provider
        provider    = p_flux,
        # container
        local       = 'ICMSHFCST+[term::fmth]',
        # resource
            # implicit: cutoff, date, geometry, model
            # optional: clscontents, nativefmt
        kind        = 'historic',
        term        = fc_terms
    )

    o_fullpos = toolbox.output(
        # section
        role        = 'Gridpoint',
        # provider
        provider    = p_flux,
        # container
        local       = 'PFFCST[geometry::area]+[term::fmth]',
        actualfmt   = 'fa',
        # resource
            # implicit: cutoff, date, model
            # optional: clscontents
        kind        = 'gridpoint',
        origin      = 'historic',
        nativefmt   = '[actualfmt]',
        geometry    = bdap_domains,
        term        = fp_terms,
    )

    o_isp = toolbox.output(
        # section
        role        = 'Isp',
        # provider
        provider    = p_flux,
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
        provider    = p_flux,
        # container
        local       = 'DHFDLFCST+{glob:h:\d+}',
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
        provider    = p_flux,
        # container
        local       = 'DHFGLFCST+{glob:h:\d+}',
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
        provider    = p_flux,
        # container
        local       = 'DHFZOFCST+{glob:h:\d+}',
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
        provider    = p_flux,
        # container
        local       = 'NODE.{glob:a:\d+}_{glob:b:\d+}',
        actualfmt   = 'ascii',
        seta        = '[glob:a]',
        setb        = '[glob:b]',
        # resource
            # implicit: cutoff, date, geometry, model
            # optional: clscontents, mpi, openmp, nativefmt
        kind        = 'plisting',
        task        = e.get('SMSNAME', 'std-forecst'),
    )

#--------------------------------------------------------------------------------------------------

    sh.title('Effective Outputs')
    toolbox.show_outputs()

#--------------------------------------------------------------------------------------------------

sh.title('End of execution')

